import os
import re
import json
import math
import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


# =========================
# Data models
# =========================

@dataclass
class Chunk:
    chunk_id: str
    text: str


@dataclass
class Flashcard:
    question: str
    answer: str
    difficulty: str
    bloom_level: str
    question_type: str
    source_chunk_id: str


@dataclass
class JudgedCard:
    card: Flashcard
    groundedness: float
    clarity: float
    uniqueness: float
    difficulty_calibration: float
    justification: str

    @property
    def composite_score(self) -> float:
        return (
            0.4 * self.groundedness
            + 0.3 * self.clarity
            + 0.2 * self.uniqueness
            + 0.1 * self.difficulty_calibration
        )

    @property
    def decision(self) -> str:
        s = self.composite_score
        if s >= 0.80:
            return "approve"
        if s >= 0.55:
            return "revise"
        return "reject"


# =========================
# LLM factory
# =========================

def create_llm(provider: str = "gemini", model: Optional[str] = None, api_key: Optional[str] = None, temperature: float = 0.3):
    provider = provider.lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("Missing GEMINI_API_KEY / GOOGLE_API_KEY")

        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.5-flash",
            google_api_key=key,
            temperature=temperature,
            convert_system_message_to_human=True,
        )

    elif provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        token = api_key or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            raise ValueError("Missing HF_TOKEN / HUGGINGFACEHUB_API_TOKEN")

        repo_id = model or "meta-llama/Llama-3.1-8B-Instruct"
        endpoint = HuggingFaceEndpoint(
            repo_id=repo_id,
            huggingfacehub_api_token=token,
            temperature=temperature,
            max_new_tokens=2048,
            task="text-generation",
        )
        return ChatHuggingFace(llm=endpoint, huggingfacehub_api_token=token)

    else:
        raise ValueError("provider must be 'gemini' or 'huggingface'")


# =========================
# Utilities
# =========================

def clean_json_response(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


def extract_text_from_pdf(pdf_path: str) -> str:
    parts = []

    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    except Exception:
        pass

    text = "\n\n".join(parts).strip()
    if len(text) >= 100:
        return text

    parts = []
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
    except Exception:
        pass

    return "\n\n".join(parts).strip()


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 200) -> List[Chunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            # overlap from previous chunk
            tail = current[-overlap:] if current else ""
            current = f"{tail}\n\n{para}".strip()

    if current:
        chunks.append(current)

    return [Chunk(chunk_id=f"chunk_{i}", text=c) for i, c in enumerate(chunks)]


def truncate(text: str, n: int = 1200) -> str:
    return text if len(text) <= n else text[:n] + "\n...[truncated]"


# =========================
# Agent 1: Extractor
# =========================

def extractor_agent(pdf_path: str) -> List[Chunk]:
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        raise ValueError("No text extracted from PDF")
    return chunk_text(text)


# =========================
# Agent 2: Generator
# =========================

def generator_agent(chunks: List[Chunk], llm, num_cards: int = 5) -> List[Flashcard]:
    if not chunks:
        return []

    # Keep it simple: use first few chunks only
    selected_chunks = chunks[: min(5, len(chunks))]
    chunks_payload = [
        {"chunk_id": c.chunk_id, "text": truncate(c.text, 1000)}
        for c in selected_chunks
    ]

    prompt = f"""
You are an expert educational flashcard generator.

Generate exactly {num_cards} flashcards from the chunks below.

Rules:
- Each flashcard must test one concept only.
- Questions must be specific and unambiguous.
- Answers must be concise but complete.
- source_chunk_id must be one of the provided chunk_ids.
- difficulty must be one of: easy, medium, hard
- bloom_level must be one of: remember, understand, apply, analyze
- question_type must be one of: definition, concept, application, comparison

Chunks:
{json.dumps(chunks_payload, ensure_ascii=False, indent=2)}

Return ONLY valid JSON array:
[
  {{
    "question": "...",
    "answer": "...",
    "difficulty": "medium",
    "bloom_level": "understand",
    "question_type": "concept",
    "source_chunk_id": "chunk_0"
  }}
]
""".strip()

    response = llm.invoke(prompt)
    data = clean_json_response(response.content)

    cards = []
    valid_difficulty = {"easy", "medium", "hard"}
    valid_bloom = {"remember", "understand", "apply", "analyze"}
    valid_qtype = {"definition", "concept", "application", "comparison"}
    valid_chunk_ids = {c.chunk_id for c in selected_chunks}

    for item in data:
        try:
            source_chunk_id = item["source_chunk_id"]
            if source_chunk_id not in valid_chunk_ids:
                source_chunk_id = selected_chunks[0].chunk_id

            difficulty = item.get("difficulty", "medium")
            if difficulty not in valid_difficulty:
                difficulty = "medium"

            bloom = item.get("bloom_level", "understand")
            if bloom not in valid_bloom:
                bloom = "understand"

            qtype = item.get("question_type", "concept")
            if qtype not in valid_qtype:
                qtype = "concept"

            cards.append(
                Flashcard(
                    question=item["question"].strip(),
                    answer=item["answer"].strip(),
                    difficulty=difficulty,
                    bloom_level=bloom,
                    question_type=qtype,
                    source_chunk_id=source_chunk_id,
                )
            )
        except Exception:
            continue

    return cards


# =========================
# Agent 3: Judge
# =========================

def judge_one_card(card: Flashcard, chunk_lookup: Dict[str, str], llm, seen_questions: List[str]) -> JudgedCard:
    source_text = chunk_lookup.get(card.source_chunk_id, "")

    if not source_text.strip():
        return JudgedCard(
            card=card,
            groundedness=0.0,
            clarity=0.6,
            uniqueness=0.6,
            difficulty_calibration=0.6,
            justification="Missing source chunk for grounding.",
        )

    prompt = f"""
You are a strict flashcard judge.

Evaluate the flashcard against the source text.

Source text:
{truncate(source_text, 1200)}

Flashcard:
Question: {card.question}
Answer: {card.answer}
Difficulty: {card.difficulty}
Bloom Level: {card.bloom_level}
Question Type: {card.question_type}

Previously seen questions:
{json.dumps(seen_questions[-10:], ensure_ascii=False)}

Return ONLY valid JSON:
{{
  "groundedness": 0.0,
  "clarity": 0.0,
  "uniqueness": 0.0,
  "difficulty_calibration": 0.0,
  "justification": "..."
}}
""".strip()

    response = llm.invoke(prompt)
    try:
        data = clean_json_response(response.content)
    except Exception:
        data = {
            "groundedness": 0.5,
            "clarity": 0.6,
            "uniqueness": 0.6,
            "difficulty_calibration": 0.6,
            "justification": "Judge response parse failed; fallback scores used."
        }

    def clamp(x, default=0.5):
        try:
            return max(0.0, min(1.0, float(x)))
        except Exception:
            return default

    return JudgedCard(
        card=card,
        groundedness=clamp(data.get("groundedness", 0.5)),
        clarity=clamp(data.get("clarity", 0.5)),
        uniqueness=clamp(data.get("uniqueness", 0.5)),
        difficulty_calibration=clamp(data.get("difficulty_calibration", 0.5)),
        justification=str(data.get("justification", "")),
    )


def judge_agent(cards: List[Flashcard], chunks: List[Chunk], llm) -> List[JudgedCard]:
    chunk_lookup = {c.chunk_id: c.text for c in chunks}
    seen_questions = []
    judged = []

    for card in cards:
        jc = judge_one_card(card, chunk_lookup, llm, seen_questions)
        judged.append(jc)
        seen_questions.append(card.question)

    return judged


# =========================
# Agent 4: Revision
# =========================

def revision_agent(judged_cards: List[JudgedCard], chunks: List[Chunk], llm) -> List[Flashcard]:
    chunk_lookup = {c.chunk_id: c.text for c in chunks}
    revised = []

    for jc in judged_cards:
        if jc.decision != "revise":
            continue

        card = jc.card
        source_text = chunk_lookup.get(card.source_chunk_id, "")

        prompt = f"""
Revise this flashcard to improve clarity and grounding.

Source text:
{truncate(source_text, 1200)}

Current card:
{json.dumps(asdict(card), ensure_ascii=False, indent=2)}

Judge feedback:
{jc.justification}

Rules:
- Keep the same source_chunk_id
- Keep one concept per card
- Keep answer concise
- Return only valid JSON object

{{
  "question": "...",
  "answer": "...",
  "difficulty": "medium",
  "bloom_level": "understand",
  "question_type": "concept",
  "source_chunk_id": "{card.source_chunk_id}"
}}
""".strip()

        response = llm.invoke(prompt)
        try:
            data = clean_json_response(response.content)
            revised.append(
                Flashcard(
                    question=data["question"].strip(),
                    answer=data["answer"].strip(),
                    difficulty=data.get("difficulty", card.difficulty),
                    bloom_level=data.get("bloom_level", card.bloom_level),
                    question_type=data.get("question_type", card.question_type),
                    source_chunk_id=card.source_chunk_id,
                )
            )
        except Exception:
            revised.append(card)

    return revised


# =========================
# Supervisor pipeline
# =========================

def run_simple_pipeline(
    pdf_path: str,
    provider: str = "gemini",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    num_cards: int = 5,
    auto_revise: bool = True,
    output_file: Optional[str] = None,
):
    print("\n=== SIMPLE MULTI-AGENT FLASHCARD PIPELINE ===\n")

    llm_gen = create_llm(provider=provider, model=model, api_key=api_key, temperature=0.7)
    llm_judge = create_llm(provider=provider, model=model, api_key=api_key, temperature=0.2)

    print("[1/4] ExtractorAgent")
    chunks = extractor_agent(pdf_path)
    print(f"  extracted chunks: {len(chunks)}")

    print("[2/4] GeneratorAgent")
    cards = generator_agent(chunks, llm_gen, num_cards=num_cards)
    print(f"  generated cards: {len(cards)}")
    if not cards:
        raise RuntimeError("No flashcards generated")

    print("[3/4] JudgeAgent")
    judged = judge_agent(cards, chunks, llm_judge)

    approved = [j.card for j in judged if j.decision == "approve"]
    borderline = [j for j in judged if j.decision == "revise"]
    rejected = [j for j in judged if j.decision == "reject"]

    print(f"  approved: {len(approved)}")
    print(f"  borderline: {len(borderline)}")
    print(f"  rejected: {len(rejected)}")

    if auto_revise and borderline:
        print("[4/4] RevisionAgent")
        revised_cards = revision_agent(borderline, chunks, llm_gen)
        rejudged = judge_agent(revised_cards, chunks, llm_judge)

        approved.extend([j.card for j in rejudged if j.decision in {"approve", "revise"}])
        rejected.extend([j for j in rejudged if j.decision == "reject"])
    else:
        print("[4/4] RevisionAgent skipped")

    final_deck = approved

    if output_file is None:
        output_file = f"{Path(pdf_path).stem}_simple_flashcards.json"

    payload = {
        "source_pdf": pdf_path,
        "provider": provider,
        "model": model or ("gemini-2.5-flash" if provider == "gemini" else "meta-llama/Llama-3.1-8B-Instruct"),
        "num_chunks": len(chunks),
        "num_generated": len(cards),
        "num_final": len(final_deck),
        "flashcards": [asdict(c) for c in final_deck],
        "judged": [
            {
                "card": asdict(j.card),
                "groundedness": j.groundedness,
                "clarity": j.clarity,
                "uniqueness": j.uniqueness,
                "difficulty_calibration": j.difficulty_calibration,
                "composite_score": round(j.composite_score, 3),
                "decision": j.decision,
                "justification": j.justification,
            }
            for j in judged
        ],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\nSaved: {output_file}\n")

    for i, c in enumerate(final_deck, 1):
        print(f"Card {i}")
        print(f"Q: {c.question}")
        print(f"A: {c.answer}")
        print(f"[{c.difficulty}] [{c.bloom_level}] [{c.question_type}] [{c.source_chunk_id}]")
        print()

    return final_deck


def main():
    parser = argparse.ArgumentParser(description="Simplified multi-agent flashcard pipeline")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--provider", default="gemini", choices=["gemini", "huggingface"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--cards", type=int, default=5)
    parser.add_argument("--no-revise", action="store_true")
    parser.add_argument("--output", default=None)

    args = parser.parse_args()

    run_simple_pipeline(
        pdf_path=args.pdf,
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        num_cards=args.cards,
        auto_revise=not args.no_revise,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()