import os
import sys
import json
import argparse
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()

from core.models import Flashcard, ScoredFlashcard, FlashcardState
from vector_store import VectorStoreManager
from providers.llm_provider import create_llm, PROVIDER_DEFAULTS
from agents.content_extraction import extract_text_from_pdf, content_extraction_node
from agents.flashcard_generation import flashcard_generation_node
from agents.quality_check import quality_check_node


# ═══════════════════════════════════════════════
# Terminal colors
# ═══════════════════════════════════════════════

class C:
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def header(text):
    print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}{C.RESET}\n")


def step(num, total, text):
    print(f"{C.BOLD}{C.MAGENTA}  [{num}/{total}]{C.RESET} {text}")


def ok(text):
    print(f"  {C.GREEN}✓{C.RESET} {text}")


def warn(text):
    print(f"  {C.YELLOW}⚠{C.RESET} {text}")


def fail(text):
    print(f"  {C.RED}✗{C.RESET} {text}")


# ═══════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════

def run_pipeline(
    pdf_path: str,
    provider: str = "gemini",
    model: str = None,
    api_key: str = None,
    num_cards: int = 5,
    skip_review: bool = False,
    output_file: str = None,
    chroma_dir: str = "./chroma_db",
):
    header("Multi-Agent Flashcard Generator")

    # ── Validate ──
    if not os.path.exists(pdf_path):
        fail(f"PDF not found: {pdf_path}")
        sys.exit(1)

    if provider not in ("gemini", "huggingface"):
        fail(f"Provider must be 'gemini' or 'huggingface', got '{provider}'")
        sys.exit(1)

    if model is None:
        model = PROVIDER_DEFAULTS[provider]["model"]

    print(f"  PDF:      {pdf_path}")
    print(f"  Provider: {provider}")
    print(f"  Model:    {model}")
    print(f"  Cards:    {num_cards}")
    print()

    import traceback

    # ── 1. Initialize LLM ──
    step(1, 5, "Initializing LLM...")
    try:
        llm = create_llm(provider=provider, model=model, temperature=0.7, api_key=api_key)
        quality_llm = create_llm(provider=provider, model=model, temperature=0.3, api_key=api_key)
        ok(f"LLM ready: {model}")
    except Exception as e:
        fail(f"LLM init failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── 2. Extract PDF ──
    step(2, 5, "Extracting text from PDF...")
    try:
        pdf_text = extract_text_from_pdf(pdf_path)
        if not pdf_text.strip():
            fail("Could not extract text. Is this a scanned/image PDF?")
            sys.exit(1)
        ok(f"Extracted {len(pdf_text):,} characters")
    except Exception as e:
        fail(f"PDF extraction failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── 3. Content Extraction Agent ──
    step(3, 5, "Running Content Extraction Agent...")
    try:
        vector_store = VectorStoreManager()

        vector_store.bootstrap_reference_docs()
        ok("  Reference docs loaded")

        state: FlashcardState = {
            "pdf_content": pdf_text,
            "source_filename": Path(pdf_path).name,
        }

        extraction_result = content_extraction_node(state, vector_store, llm)
        state.update(extraction_result)

        content_type = state.get("content_type", "unknown")
        num_chunks = len(state.get("chunks", []))
        ok(f"Content type: {content_type} | Chunks: {num_chunks}")

        if num_chunks == 0:
            fail("No chunks produced. PDF might be empty.")
            sys.exit(1)

    except Exception as e:
        fail(f"Content extraction failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── 4. Flashcard Generation Agent ──
    step(4, 5, f"Generating {num_cards} flashcards...")
    try:
        generation_result = flashcard_generation_node(state, vector_store, llm, cards_per_batch=num_cards)
        state.update(generation_result)

        raw_cards = state.get("raw_cards", [])
        if not raw_cards:
            fail(f"Generation failed: {state.get('error', 'Unknown')}")
            sys.exit(1)
        ok(f"Generated {len(raw_cards)} flashcards")
    except Exception as e:
        fail(f"Flashcard generation failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── 5. Quality Check Agent ──
    step(5, 5, "Running Quality Check Agent...")
    try:
        quality_result = quality_check_node(state, quality_llm)
        state.update(quality_result)
    except Exception as e:
        fail(f"Quality check failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    approved: List[Flashcard] = list(state.get("approved_cards", []))
    human_queue: List[ScoredFlashcard] = state.get("human_queue", [])
    rejected: List[ScoredFlashcard] = state.get("rejected_cards", [])
    scored_cards: List[ScoredFlashcard] = state.get("scored_cards", [])

    ok(f"Auto-approved: {len(approved)} | Needs review: {len(human_queue)} | Rejected: {len(rejected)}")

    # ── Print scores ──
    header("Quality Scores")
    for i, sc in enumerate(scored_cards):
        routing = sc.routing_decision
        color = C.GREEN if routing == "auto_approve" else (C.YELLOW if routing == "human_review" else C.RED)
        icon = "✓" if routing == "auto_approve" else ("?" if routing == "human_review" else "✗")

        print(f"  {color}{icon}{C.RESET} Card {i+1}: {C.BOLD}{sc.composite_score:.3f}{C.RESET} "
              f"(G={sc.groundedness:.2f} C={sc.clarity:.2f} U={sc.uniqueness:.2f} D={sc.difficulty_calibration:.2f})")
        print(f"    Q: {sc.card.question[:90]}")
        if sc.justification:
            print(f"    {C.DIM}{sc.justification}{C.RESET}")
        print()

    # ── Interactive Teacher Review ──
    if human_queue and not skip_review:
        header(f"Teacher Review — {len(human_queue)} cards")
        teacher_edits = []

        for i, scored_card in enumerate(human_queue):
            card = scored_card.card
            print(f"  {C.BOLD}─── Card {i+1}/{len(human_queue)} (score: {scored_card.composite_score:.3f}) ───{C.RESET}")
            print(f"  {C.CYAN}Q:{C.RESET} {card.question}")
            print(f"  {C.GREEN}A:{C.RESET} {card.answer}")
            print(f"  {C.DIM}[{card.difficulty}] [{card.bloom_level}] [{card.question_type}]{C.RESET}")
            if scored_card.justification:
                print(f"  {C.DIM}Judge says: {scored_card.justification}{C.RESET}")
            print()

            while True:
                choice = input("  [a]pprove / [e]dit / [r]eject / [s]kip: ").strip().lower()
                if choice in ("a", "approve"):
                    approved.append(card)
                    ok("Approved!")
                    break
                elif choice in ("e", "edit"):
                    new_q = input("  New question (Enter=keep): ").strip()
                    new_a = input("  New answer (Enter=keep): ").strip()
                    edited = Flashcard(
                        question=new_q or card.question,
                        answer=new_a or card.answer,
                        difficulty=card.difficulty,
                        bloom_level=card.bloom_level,
                        source_chunk_id=card.source_chunk_id,
                        question_type=card.question_type,
                    )
                    approved.append(edited)
                    teacher_edits.append(edited)
                    ok("Edited & approved! (stored as gold example)")
                    break
                elif choice in ("r", "reject"):
                    warn("Rejected.")
                    break
                elif choice in ("s", "skip"):
                    warn("Skipped.")
                    break
                else:
                    print("  Use: a / e / r / s")
            print()

        # Feedback loop: store edits as gold examples
        if teacher_edits:
            for ed in teacher_edits:
                vector_store.add_gold_flashcard({
                    "question": ed.question, "answer": ed.answer,
                    "difficulty": ed.difficulty, "bloom_level": ed.bloom_level,
                    "question_type": ed.question_type,
                })
            ok(f"{len(teacher_edits)} edits stored as gold examples for future improvement")

    elif human_queue and skip_review:
        approved.extend([sc.card for sc in human_queue])
        warn(f"--no-review: auto-approved {len(human_queue)} borderline cards")

    # ── Final Deck ──
    final_deck = approved
    header(f"Final Deck — {len(final_deck)} Flashcards")

    for i, card in enumerate(final_deck, 1):
        print(f"  {C.BOLD}Card {i}{C.RESET}")
        print(f"  {C.CYAN}Q:{C.RESET} {card.question}")
        print(f"  {C.GREEN}A:{C.RESET} {card.answer}")
        print(f"  {C.DIM}[{card.difficulty}] [{card.bloom_level}] [{card.question_type}]{C.RESET}")
        print()

    # ── Save JSON ──
    if output_file is None:
        output_file = f"{Path(pdf_path).stem}_flashcards.json"

    output_data = {
        "source_pdf": pdf_path,
        "provider": provider,
        "model": model,
        "content_type": content_type,
        "num_chunks": num_chunks,
        "stats": {
            "total_generated": len(raw_cards),
            "auto_approved": len(state.get("approved_cards", [])),
            "human_reviewed": len(human_queue),
            "rejected": len(rejected),
            "final_deck_size": len(final_deck),
        },
        "quality_scores": [
            {
                "question": sc.card.question,
                "composite": round(sc.composite_score, 3),
                "groundedness": sc.groundedness,
                "clarity": sc.clarity,
                "uniqueness": sc.uniqueness,
                "difficulty_calibration": sc.difficulty_calibration,
                "routing": sc.routing_decision,
            }
            for sc in scored_cards
        ],
        "flashcards": [
            {
                "question": c.question,
                "answer": c.answer,
                "difficulty": c.difficulty,
                "bloom_level": c.bloom_level,
                "question_type": c.question_type,
                "source_chunk_id": c.source_chunk_id,
            }
            for c in final_deck
        ],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    ok(f"Saved to: {output_file}")
    return final_deck


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Flashcard Generator (CLI — no frontend)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Gemini 3 Flash (free key from ai.google.dev)
  export GEMINI_API_KEY=your-key
  python run_pipeline.py --pdf lecture.pdf --provider gemini

  # HuggingFace Llama (free token from huggingface.co)
  export HF_TOKEN=hf_your-token
  python run_pipeline.py --pdf lecture.pdf --provider huggingface

  # 10 cards, skip review, custom output
  python run_pipeline.py --pdf notes.pdf --provider gemini --cards 10 --no-review --output deck.json

  # Specific HuggingFace model
  python run_pipeline.py --pdf ch3.pdf --provider huggingface --model mistralai/Mistral-7B-Instruct-v0.3
        """,
    )

    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "huggingface"],
                        help="LLM provider (default: gemini)")
    parser.add_argument("--model", default=None, help="Model name (default: provider's default)")
    parser.add_argument("--api-key", default=None, help="API key (or use env vars GEMINI_API_KEY / HF_TOKEN)")
    parser.add_argument("--cards", type=int, default=5, help="Number of flashcards (default: 5)")
    parser.add_argument("--no-review", action="store_true", help="Skip interactive teacher review")
    parser.add_argument("--output", default=None, help="Output JSON path (default: <pdf>_flashcards.json)")
    parser.add_argument("--chroma-dir", default="./chroma_db", help="ChromaDB directory")

    args = parser.parse_args()

    run_pipeline(
        pdf_path=args.pdf,
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        num_cards=args.cards,
        skip_review=args.no_review,
        output_file=args.output,
        chroma_dir=args.chroma_dir,
    )


if __name__ == "__main__":
    main()