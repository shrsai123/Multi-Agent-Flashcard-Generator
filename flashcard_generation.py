import json
import re
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from models import Flashcard, FlashcardState
from vector_store import VectorStoreManager


SYSTEM_PROMPT = """You are an expert educational flashcard creator. Generate high-quality flashcards
from the provided source material. Each flashcard should test a specific concept.

RULES:
1. Questions must be clear, specific, and unambiguous
2. Answers must be concise but complete
3. Each card tests ONE concept only
4. Vary question types: definitions, concepts, applications, comparisons
5. Vary difficulty levels and Bloom's taxonomy levels across cards
6. Avoid yes/no questions
7. Include the source_chunk_id so we can verify grounding

You MUST respond with valid JSON only — an array of flashcard objects. No markdown fences."""


def build_generation_prompt(chunks_text: str, few_shot_examples: List[Dict], bloom_guidance: str = "", num_cards: int = 5) -> str:
    examples_str = ""
    if few_shot_examples:
        examples_str = "Here are examples of high-quality flashcards approved by teachers:\n"
        for i, ex in enumerate(few_shot_examples, 1):
            examples_str += f"\nExample {i}:\n  Q: {ex.get('question', '')}\n  A: {ex.get('answer', '')}\n  Difficulty: {ex.get('difficulty', 'medium')}\n  Bloom Level: {ex.get('bloom_level', 'understand')}\n"
        examples_str += "\n---\n"

    bloom_str = f"\nBloom's Taxonomy Guidance:\n{bloom_guidance}\n---\n" if bloom_guidance else ""

    return f"""{examples_str}{bloom_str}
Source material:
{chunks_text}

Generate exactly {num_cards} flashcards from this material.

For each flashcard, provide:
- question: Clear, specific question
- answer: Concise but complete answer
- difficulty: "easy" | "medium" | "hard"
- bloom_level: "remember" | "understand" | "apply" | "analyze"
- source_chunk_id: Which chunk this came from (use chunk_0, chunk_1, etc.)
- question_type: "definition" | "concept" | "application" | "comparison"

Respond ONLY with a JSON array. No markdown, no explanations.
Example format:
[
  {{
    "question": "What is...",
    "answer": "It is...",
    "difficulty": "medium",
    "bloom_level": "understand",
    "source_chunk_id": "chunk_0",
    "question_type": "concept"
  }}
]"""


def generate_flashcards(chunks_text: str, llm, few_shot_examples: List[Dict], bloom_guidance: str = "", num_cards: int = 5) -> List[Flashcard]:
    user_prompt = build_generation_prompt(chunks_text, few_shot_examples, bloom_guidance, num_cards)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

    response = llm.invoke(messages)
    raw_text = response.content.strip()

    # Clean markdown fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()

    try:
        cards_data = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match:
            cards_data = json.loads(match.group())
        else:
            raise ValueError(f"Failed to parse LLM response as JSON:\n{raw_text[:500]}")

    flashcards = []
    for card_dict in cards_data:
        try:
            card = Flashcard(**card_dict)
            flashcards.append(card)
        except Exception as e:
            print(f"Skipping invalid card: {e}")
    return flashcards


def flashcard_generation_node(state: FlashcardState, vector_store: VectorStoreManager, llm, cards_per_batch: int = 5) -> dict:
    """LangGraph node: Generate flashcards from chunks."""
    chunks = state.get("chunks", [])
    if not chunks:
        return {"raw_cards": [], "error": "No chunks available for generation"}

    chunks_text = ""
    for i, chunk in enumerate(chunks):
        chunks_text += f"\n--- chunk_{i} ---\n{chunk.page_content}\n"

    few_shot_context = chunks[0].page_content[:200] if chunks else ""
    few_shot_examples = vector_store.get_few_shot_examples(few_shot_context, n_examples=3)
    bloom_guidance = vector_store.get_bloom_guidance("understand")

    try:
        raw_cards = generate_flashcards(chunks_text, llm, few_shot_examples, bloom_guidance, cards_per_batch)
        return {"raw_cards": raw_cards}
    except Exception as e:
        return {"raw_cards": [], "error": f"Generation failed: {str(e)}"}