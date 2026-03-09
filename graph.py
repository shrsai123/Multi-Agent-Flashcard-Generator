import os
from typing import Literal, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.models import FlashcardState, Flashcard, ScoredFlashcard, TeacherAction
from vector_store import VectorStoreManager
from providers.llm_provider import create_llm
from agents.content_extraction import content_extraction_node
from agents.flashcard_generation import flashcard_generation_node
from agents.quality_check import quality_check_node



def make_extraction_node(vector_store: VectorStoreManager, llm):
    """Create a content extraction node with injected dependencies."""
    def node(state: FlashcardState) -> dict:
        return content_extraction_node(state, vector_store, llm)
    return node


def make_generation_node(vector_store: VectorStoreManager, llm):
    """Create a flashcard generation node with injected dependencies."""
    def node(state: FlashcardState) -> dict:
        return flashcard_generation_node(state, vector_store, llm)
    return node


def make_quality_node(llm):
    """Create a quality check node with injected dependencies."""
    def node(state: FlashcardState) -> dict:
        return quality_check_node(state, llm)
    return node


def teacher_review_node(state: FlashcardState) -> dict:
    """
    HITL node: This is where the graph pauses (via interrupt) and waits
    for teacher input through the Streamlit UI.
    """
    human_queue = state.get("human_queue", [])
    teacher_actions = state.get("teacher_actions", [])
    approved_cards = list(state.get("approved_cards", []))
    rejected_cards = list(state.get("rejected_cards", []))
    teacher_edits = []
    regeneration_requests = []

    if not teacher_actions:
        return {
            "teacher_edits": [],
            "regeneration_requests": [],
            "rejected_cards": rejected_cards,
            "final_deck": approved_cards,
        }
        

    for action in teacher_actions:
        idx = action.card_index
        if idx < 0 or idx >= len(human_queue):
            continue

        scored_card = human_queue[idx]

        if action.action == "approve":
            approved_cards.append(scored_card.card)

        elif action.action == "edit":
            edited_card = Flashcard(
                question=action.edited_question or scored_card.card.question,
                answer=action.edited_answer or scored_card.card.answer,
                difficulty=scored_card.card.difficulty,
                bloom_level=scored_card.card.bloom_level,
                source_chunk_id=scored_card.card.source_chunk_id,
                question_type=scored_card.card.question_type,
            )
            approved_cards.append(edited_card)
            teacher_edits.append(edited_card)

        elif action.action == "reject":
            rejected_cards.append(scored_card)

        elif action.action == "regenerate":
            regeneration_requests.append(scored_card)
            rejected_cards.append(scored_card)

    return {
        "approved_cards": approved_cards,
        "teacher_edits": teacher_edits,
        "regeneration_requests": regeneration_requests,
        "rejected_cards": rejected_cards,
        "final_deck": approved_cards,
    }


def finalize_deck_node(state: FlashcardState) -> dict:
    """Final node: assemble the complete deck."""
    approved = state.get("approved_cards", [])
    return {"final_deck": list(approved)}


# ─────────────────────────────────────────────
# Routing Logic (Conditional Edges)
# ─────────────────────────────────────────────

def route_after_quality_check(state: FlashcardState) -> str:
    human_queue = state.get("human_queue", [])
    if human_queue:
        return "teacher_review"
    return "finalize"


# ─────────────────────────────────────────────
# Build the Graph
# ─────────────────────────────────────────────

def build_flashcard_graph(
    vector_store: VectorStoreManager,
    llm=None,
    quality_llm=None,
) -> StateGraph:
    """
    Build the LangGraph StateGraph for the flashcard pipeline.

    Args:
        vector_store: ChromaDB manager instance
        llm: Main LLM for content extraction + flashcard generation
        quality_llm: LLM for quality scoring (can be same or different)
    """
    if llm is None:
        llm = create_llm(provider="gemini")
    if quality_llm is None:
        quality_llm = llm  # Reuse the same LLM for quality checks

    graph = StateGraph(FlashcardState)

    # Add nodes
    graph.add_node("content_extraction", make_extraction_node(vector_store, llm))
    graph.add_node("flashcard_generation", make_generation_node(vector_store, llm))
    graph.add_node("quality_check", make_quality_node(quality_llm))
    graph.add_node("teacher_review", teacher_review_node)
    graph.add_node("finalize", finalize_deck_node)

    # Add edges
    graph.set_entry_point("content_extraction")
    graph.add_edge("content_extraction", "flashcard_generation")
    graph.add_edge("flashcard_generation", "quality_check")

    graph.add_conditional_edges(
        "quality_check",
        route_after_quality_check,
        {
            "teacher_review": "teacher_review",
            "finalize": "finalize",
        }
    )

    graph.add_edge("teacher_review", "finalize")
    graph.add_edge("finalize", END)

    return graph


def compile_graph(
    vector_store: VectorStoreManager,
    llm=None,
    quality_llm=None,
    use_checkpointer: bool = True,
):
    """Compile the graph with optional checkpointing for HITL support."""
    graph = build_flashcard_graph(vector_store, llm, quality_llm)

    if use_checkpointer:
        checkpointer = MemorySaver()
        return graph.compile(checkpointer=checkpointer, interrupt_before=["teacher_review"])
    else:
        return graph.compile()


# ─────────────────────────────────────────────
# Store teacher edits as gold examples
# ─────────────────────────────────────────────

def store_teacher_edits(vector_store: VectorStoreManager, teacher_edits: list):
    """Store teacher-edited cards in gold_flashcards for future few-shot retrieval."""
    for card in teacher_edits:
        card_dict = {
            "question": card.question,
            "answer": card.answer,
            "difficulty": card.difficulty,
            "bloom_level": card.bloom_level,
            "question_type": card.question_type,
        }
        vector_store.add_gold_flashcard(card_dict)