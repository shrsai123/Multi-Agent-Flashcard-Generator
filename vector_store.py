from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
import faiss
import json
import os
import numpy as np


class VectorStoreManager:
    """FAISS-backed vector store with persistent gold flashcards."""

    def __init__(self, persist_dir: str = "./faiss_db", embedding_model: str = "all-MiniLM-L6-v2"):
        self.persist_dir = persist_dir
        self.embedder = SentenceTransformer(embedding_model, device="cpu")
        self.dim = self.embedder.get_sentence_embedding_dimension()

        os.makedirs(persist_dir, exist_ok=True)

        # ── Session-only: course chunks (per PDF) ──
        self.course_chunks: List[Document] = []
        self.course_index: Optional[faiss.IndexFlatIP] = None

        # ── Persistent: gold flashcards ──
        self.gold_cards: List[Dict[str, Any]] = []
        self.gold_index = faiss.IndexFlatIP(self.dim)
        self._load_gold()

        # ── Persistent: reference docs (Bloom's guidance) ──
        self.ref_docs: List[Dict[str, Any]] = []
        self.ref_index = faiss.IndexFlatIP(self.dim)
        self._load_or_bootstrap_refs()


    def _embed(self, texts: List[str]) -> np.ndarray:
        vecs = self.embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return np.array(vecs, dtype=np.float32)

    def _embed_single(self, text: str) -> np.ndarray:
        return self._embed([text])[0]

    # ══════════════════════════════════════════
    # Course Chunks (session-only, rebuilt per PDF)
    # ══════════════════════════════════════════

    def add_course_chunks(self, chunks: List[Document], source_filename: str):
        for i, chunk in enumerate(chunks):
            chunk.metadata["source_filename"] = source_filename
            chunk.metadata["chunk_id"] = f"chunk_{i}"
        self.course_chunks.extend(chunks)

        # Build FAISS index for course content
        texts = [c.page_content for c in self.course_chunks]
        if texts:
            vecs = self._embed(texts)
            self.course_index = faiss.IndexFlatIP(self.dim)
            self.course_index.add(vecs)

    def retrieve_course_chunks(self, query: str, top_k: int = 5, content_type: Optional[str] = None) -> List[Document]:
        if not self.course_chunks or self.course_index is None:
            return []

        query_vec = self._embed_single(query).reshape(1, -1)
        k = min(top_k * 2, len(self.course_chunks))  # fetch extra to filter
        scores, indices = self.course_index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            chunk = self.course_chunks[idx]
            if content_type and chunk.metadata.get("content_type") != content_type:
                continue
            chunk.metadata["relevance_score"] = float(score)
            results.append(chunk)
            if len(results) >= top_k:
                break
        return results

    # ══════════════════════════════════════════
    # Gold Flashcards (persistent across runs)
    # ══════════════════════════════════════════

    def _gold_path(self) -> str:
        return os.path.join(self.persist_dir, "gold_flashcards.json")

    def _gold_index_path(self) -> str:
        return os.path.join(self.persist_dir, "gold_flashcards.faiss")

    def _load_gold(self):
        json_path = self._gold_path()
        index_path = self._gold_index_path()

        if os.path.exists(json_path) and os.path.exists(index_path):
            with open(json_path, "r", encoding="utf-8") as f:
                self.gold_cards = json.load(f)
            self.gold_index = faiss.read_index(index_path)
        else:
            self.gold_cards = []
            self.gold_index = faiss.IndexFlatIP(self.dim)

    def _save_gold(self):
        with open(self._gold_path(), "w", encoding="utf-8") as f:
            json.dump(self.gold_cards, f, indent=2, ensure_ascii=False)
        faiss.write_index(self.gold_index, self._gold_index_path())

    def add_gold_flashcard(self, card: Dict[str, Any], card_id: Optional[str] = None):
        text = f"Q: {card['question']}\nA: {card['answer']}"
        vec = self._embed_single(text).reshape(1, -1)

        self.gold_cards.append({
            "question": card["question"],
            "answer": card["answer"],
            "difficulty": card.get("difficulty", "medium"),
            "bloom_level": card.get("bloom_level", "understand"),
            "question_type": card.get("question_type", "concept"),
        })
        self.gold_index.add(vec)
        self._save_gold()

    def get_few_shot_examples(self, context: str, n_examples: int = 3) -> List[Dict]:
        if self.gold_index.ntotal == 0:
            return []

        query_vec = self._embed_single(context).reshape(1, -1)
        k = min(n_examples, self.gold_index.ntotal)
        scores, indices = self.gold_index.search(query_vec, k)

        examples = []
        for idx in indices[0]:
            if 0 <= idx < len(self.gold_cards):
                examples.append(self.gold_cards[idx])
        return examples

  

    def _ref_path(self) -> str:
        return os.path.join(self.persist_dir, "reference_docs.json")

    def _ref_index_path(self) -> str:
        return os.path.join(self.persist_dir, "reference_docs.faiss")

    def _load_or_bootstrap_refs(self):
        json_path = self._ref_path()
        index_path = self._ref_index_path()

        if os.path.exists(json_path) and os.path.exists(index_path):
            with open(json_path, "r", encoding="utf-8") as f:
                self.ref_docs = json.load(f)
            self.ref_index = faiss.read_index(index_path)
        else:
            self.bootstrap_reference_docs()

    def bootstrap_reference_docs(self):
        self.ref_docs = [
            {"id": "bloom_remember", "text": "Bloom's Remember: Retrieve knowledge. Use: define, list, recall, identify. Example: 'What is the definition of polymorphism?'", "doc_type": "bloom_taxonomy", "bloom_level": "remember"},
            {"id": "bloom_understand", "text": "Bloom's Understand: Construct meaning. Use: explain, summarize, compare, classify. Example: 'Explain how inheritance differs from composition.'", "doc_type": "bloom_taxonomy", "bloom_level": "understand"},
            {"id": "bloom_apply", "text": "Bloom's Apply: Use in new situations. Use: implement, solve, demonstrate. Example: 'Write a function using recursion to find the maximum.'", "doc_type": "bloom_taxonomy", "bloom_level": "apply"},
            {"id": "bloom_analyze", "text": "Bloom's Analyze: Break into parts. Use: compare, contrast, differentiate. Example: 'Compare time complexity of quicksort vs mergesort.'", "doc_type": "bloom_taxonomy", "bloom_level": "analyze"},
            {"id": "best_practices", "text": "Flashcard Best Practices: One concept per card. Specific questions. Concise answers. Avoid yes/no. Include context. Vary difficulty.", "doc_type": "best_practices", "bloom_level": None},
        ]

        texts = [doc["text"] for doc in self.ref_docs]
        vecs = self._embed(texts)
        self.ref_index = faiss.IndexFlatIP(self.dim)
        self.ref_index.add(vecs)

        # Persist
        with open(self._ref_path(), "w", encoding="utf-8") as f:
            json.dump(self.ref_docs, f, indent=2, ensure_ascii=False)
        faiss.write_index(self.ref_index, self._ref_index_path())

    def get_bloom_guidance(self, target_level: str) -> str:
        if self.ref_index.ntotal == 0:
            return ""

        query_vec = self._embed_single(f"Bloom's {target_level} level questions").reshape(1, -1)
        k = min(2, self.ref_index.ntotal)
        scores, indices = self.ref_index.search(query_vec, k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.ref_docs) and self.ref_docs[idx].get("doc_type") == "bloom_taxonomy":
                results.append(self.ref_docs[idx]["text"])
        return "\n".join(results)


    def get_gold_count(self) -> int:
        return len(self.gold_cards)

    def close(self):
        pass 