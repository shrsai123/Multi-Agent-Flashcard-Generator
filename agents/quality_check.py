import json
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document

from core.models import Flashcard, ScoredFlashcard, FlashcardState


QUALITY_CHECK_SYSTEM = """You are a strict quality evaluator for educational flashcards.
Score the flashcard on 4 dimensions (each 0.0 to 1.0):

1. **groundedness**: Is the answer supported by the source text? (1.0=perfectly grounded, 0.0=fabricated)
2. **clarity**: Is the question unambiguous and answer concise? (1.0=crystal clear, 0.0=confusing)
3. **uniqueness**: Does this test a distinct concept? (1.0=unique, 0.0=duplicate)
4. **difficulty_calibration**: Does labeled difficulty match actual complexity? (1.0=perfect, 0.0=wrong)

Respond with ONLY valid JSON. No markdown, no explanation outside the JSON."""


def build_scoring_prompt(card: Flashcard, source_chunk: str, existing_questions: List[str]) -> str:
    existing_str = "\n".join(f"  - {q}" for q in existing_questions[-10:]) if existing_questions else "  (none yet)"
    return f"""Source material:
{source_chunk}

Flashcard to evaluate:
  Question: {card.question}
  Answer: {card.answer}
  Difficulty: {card.difficulty}
  Bloom Level: {card.bloom_level}
  Question Type: {card.question_type}

Existing questions in deck (for uniqueness check):
{existing_str}

Score this flashcard. Respond with JSON only:
{{
  "groundedness": <float 0-1>,
  "clarity": <float 0-1>,
  "uniqueness": <float 0-1>,
  "difficulty_calibration": <float 0-1>,
  "justification": "<brief 1-2 sentence justification>"
}}"""


def score_flashcard(card: Flashcard, source_chunk: str, existing_questions: List[str], llm) -> ScoredFlashcard:
    if not source_chunk.strip():
        return ScoredFlashcard(
            card=card,
            groundedness=0.0,
            clarity=0.6,
            uniqueness=0.6,
            difficulty_calibration=0.6,
            justification="Missing or invalid source_chunk_id, so grounding could not be verified.",
        )
    prompt = build_scoring_prompt(card, source_chunk, existing_questions)
    messages = [SystemMessage(content=QUALITY_CHECK_SYSTEM), HumanMessage(content=prompt)]

    response = llm.invoke(messages)
    content = response.content
    if isinstance(content, list):
      raw_text = "".join(block if isinstance(block, str) else block.get("text", "") for block in content).strip()
    else:
      raw_text = content.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()

    try:
        scores = json.loads(raw_text)
    except json.JSONDecodeError:
        scores = {"groundedness": 0.6, "clarity": 0.6, "uniqueness": 0.7, "difficulty_calibration": 0.6, "justification": "Failed to parse LLM scoring response"}

    return ScoredFlashcard(
        card=card,
        groundedness=max(0.0, min(1.0, float(scores.get("groundedness", 0.5)))),
        clarity=max(0.0, min(1.0, float(scores.get("clarity", 0.5)))),
        uniqueness=max(0.0, min(1.0, float(scores.get("uniqueness", 0.5)))),
        difficulty_calibration=max(0.0, min(1.0, float(scores.get("difficulty_calibration", 0.5)))),
        justification=scores.get("justification", ""),
    )


def quality_check_node(state: FlashcardState, llm) -> dict:
    """LangGraph node: Score all raw cards and route them."""
    raw_cards: List[Flashcard] = state.get("raw_cards", [])
    chunks: List[Document] = state.get("chunks", [])

    if not raw_cards:
        return {"scored_cards": [], "approved_cards": [], "human_queue": [], "rejected_cards": []}

    chunk_lookup: Dict[str, str] = {}
    for i, chunk in enumerate(chunks):
        chunk_lookup[f"chunk_{i}"] = chunk.page_content

    scored_cards = []
    existing_questions: List[str] = []
    approved_cards: List[Flashcard] = []
    human_queue: List[ScoredFlashcard] = []
    rejected_cards: List[ScoredFlashcard] = []


    for card in raw_cards:
        source_text = chunk_lookup.get(card.source_chunk_id, "")
        if not source_text and chunks:
            source_text = chunks[0].page_content

        scored = score_flashcard(card, source_text, existing_questions, llm)
        scored_cards.append(scored)

        routing = scored.routing_decision
        if routing == "auto_approve":
            approved_cards.append(card)
        elif routing == "human_review":
            human_queue.append(scored)
        else:
            rejected_cards.append(scored)

        existing_questions.append(card.question)

    return {
        "scored_cards": scored_cards,
        "approved_cards": approved_cards,
        "human_queue": human_queue,
        "rejected_cards": rejected_cards,
    }