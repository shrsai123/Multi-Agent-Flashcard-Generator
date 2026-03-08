import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document


class VectorStoreManager:
    def __init__(self, persist_dir: str = "./chroma_db", embedding_model: str = "all-MiniLM-L6-v2"):
        self.persist_dir = persist_dir
        self.embedder = SentenceTransformer(embedding_model)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.course_content = self.client.get_or_create_collection(name="course_content")
        self.gold_flashcards = self.client.get_or_create_collection(name="gold_flashcards")
        self.reference_docs = self.client.get_or_create_collection(name="reference_docs")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.encode(texts, show_progress_bar=False).tolist()

    def add_course_chunks(self, chunks: List[Document], source_filename: str):
        if not chunks:
            return
        texts = [c.page_content for c in chunks]
        embeddings = self._embed(texts)
        ids = [f"{source_filename}_chunk_{i}" for i in range(len(chunks))]
        metadatas = []
        for i, chunk in enumerate(chunks):
            meta = chunk.metadata.copy() if chunk.metadata else {}
            meta["source_filename"] = source_filename
            meta["chunk_index"] = i
            metadatas.append(meta)
        self.course_content.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def retrieve_course_chunks(self, query: str, top_k: int = 5, content_type: Optional[str] = None) -> List[Document]:
        query_embedding = self._embed([query])[0]
        where_filter = {"content_type": content_type} if content_type else None
        results = self.course_content.query(
            query_embeddings=[query_embedding], n_results=top_k,
            where=where_filter if where_filter else None,
        )
        documents = []
        if results and results["documents"]:
            for i, doc_text in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                meta["relevance_score"] = 1 - results["distances"][0][i] if results["distances"] else 0.0
                documents.append(Document(page_content=doc_text, metadata=meta))
        return documents

    def add_gold_flashcard(self, card: Dict[str, Any], card_id: Optional[str] = None):
        text = f"Q: {card['question']}\nA: {card['answer']}"
        embedding = self._embed([text])[0]
        if card_id is None:
            card_id = f"gold_{self.gold_flashcards.count()}"
        metadata = {
            "question": card["question"], "answer": card["answer"],
            "difficulty": card.get("difficulty", "medium"),
            "bloom_level": card.get("bloom_level", "understand"),
            "question_type": card.get("question_type", "concept"),
        }
        self.gold_flashcards.upsert(ids=[card_id], embeddings=[embedding], documents=[text], metadatas=[metadata])

    def get_few_shot_examples(self, context: str, n_examples: int = 3) -> List[Dict]:
        if self.gold_flashcards.count() == 0:
            return []
        query_embedding = self._embed([context])[0]
        results = self.gold_flashcards.query(
            query_embeddings=[query_embedding],
            n_results=min(n_examples, self.gold_flashcards.count()),
        )
        examples = []
        if results and results["metadatas"]:
            for meta in results["metadatas"][0]:
                examples.append({
                    "question": meta.get("question", ""), "answer": meta.get("answer", ""),
                    "difficulty": meta.get("difficulty", ""), "bloom_level": meta.get("bloom_level", ""),
                })
        return examples

    def bootstrap_reference_docs(self):
        reference_texts = [
            {"id": "bloom_remember", "text": "Bloom's Remember Level: Retrieve relevant knowledge. Example: Define, list, recall, identify. Example Q: 'What is the definition of polymorphism in OOP?'", "metadata": {"bloom_level": "remember", "doc_type": "bloom_taxonomy"}},
            {"id": "bloom_understand", "text": "Bloom's Understand Level: Construct meaning. Example: Explain, summarize, compare, classify. Example Q: 'Explain how inheritance differs from composition.'", "metadata": {"bloom_level": "understand", "doc_type": "bloom_taxonomy"}},
            {"id": "bloom_apply", "text": "Bloom's Apply Level: Use procedure in situation. Example: Implement, solve, demonstrate. Example Q: 'Write a function using recursion to find the maximum.'", "metadata": {"bloom_level": "apply", "doc_type": "bloom_taxonomy"}},
            {"id": "bloom_analyze", "text": "Bloom's Analyze Level: Break into parts, determine relationships. Example: Compare, contrast, differentiate. Example Q: 'Compare time complexity of quicksort vs mergesort.'", "metadata": {"bloom_level": "analyze", "doc_type": "bloom_taxonomy"}},
            {"id": "flashcard_best_practices", "text": "Flashcard Best Practices: One concept per card. Specific questions. Concise answers. Avoid yes/no. Include context. Test understanding not just recall. Active recall phrasing. Vary difficulty.", "metadata": {"doc_type": "best_practices"}},
        ]
        for ref in reference_texts:
            embedding = self._embed([ref["text"]])[0]
            self.reference_docs.upsert(ids=[ref["id"]], embeddings=[embedding], documents=[ref["text"]], metadatas=[ref["metadata"]])

    def get_bloom_guidance(self, target_level: str) -> str:
        query_embedding = self._embed([f"Bloom's {target_level} level questions"])[0]
        results = self.reference_docs.query(query_embeddings=[query_embedding], n_results=2, where={"doc_type": "bloom_taxonomy"})
        if results and results["documents"]:
            return "\n".join(results["documents"][0])
        return ""