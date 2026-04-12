import time
import json
from pathlib import Path
from typing import Dict, List, Any

EVAL_LOG_DIR = Path("eval_logs")
EVAL_LOG_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 1. PIPELINE & TEACHER METRICS
# ═══════════════════════════════════════════════════════════

def compute_pipeline_metrics(scored_cards, approved, human_queue, rejected,
                             raw_cards, gold_at_gen_time, duration_s,
                             session_state: dict) -> dict:
    """Quality scores, routing rates, teacher actions, gold count."""
    scores = [s.composite_score for s in scored_cards]
    total = len(scored_cards) or 1
    mean_score = sum(scores) / total if scores else 0

    review_decisions = session_state.get("review_decisions", {})
    auto_edit_decisions = session_state.get("auto_edit_decisions", {})

    metrics = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session_id": session_state.get("study_session_id", ""),
        "source_file": session_state.get("source_filename", ""),
        "pipeline_duration_sec": round(duration_s, 1),
        # Generation
        "cards_requested": session_state.get("gen_num_cards", 0),
        "cards_valid": len(raw_cards),
        # Quality
        "composite_mean": round(mean_score, 4),
        "composite_min": round(min(scores), 4) if scores else 0,
        "composite_max": round(max(scores), 4) if scores else 0,
        "groundedness_mean": round(sum(s.groundedness for s in scored_cards) / total, 4),
        "clarity_mean": round(sum(s.clarity for s in scored_cards) / total, 4),
        # Routing
        "auto_approved": len(approved),
        "human_review": len(human_queue),
        "auto_rejected": len(rejected),
        # Teacher actions
        "teacher_edits": sum(1 for d in review_decisions.values() if d == "edit")
                       + sum(1 for d in auto_edit_decisions.values() if d == "edit"),
        "teacher_overrides": sum(1 for d in auto_edit_decisions.values() if d in ("edit", "reject")),
        # Gold
        "gold_at_generation": gold_at_gen_time,
        "gold_added": len(session_state.get("gold_cards_session", [])),
    }

    log_file = EVAL_LOG_DIR / "pipeline_metrics.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(metrics, ensure_ascii=False) + "\n")

    return metrics


# ═══════════════════════════════════════════════════════════
# 2. LEARNING METRICS (SM2)
# ═══════════════════════════════════════════════════════════

def compute_learning_metrics(session_state: dict, total_cards: int) -> dict:
    """First-attempt recall, fail rates, session stats."""
    sm2_cards = session_state.get("sm2_cards", {})
    flip_times = session_state.get("flip_times", {})

    if not sm2_cards:
        return {"status": "no_study_data"}

    # First-attempt recall
    first_pass = sum(1 for c in sm2_cards.values() if c.review_history and c.review_history[0][1] >= 3)
    first_total = sum(1 for c in sm2_cards.values() if c.review_history)

    # Ratings
    all_ratings = [q for c in sm2_cards.values() for _, q in c.review_history]
    total_r = len(all_ratings) or 1

    # Session duration
    all_ts = sorted(t for ts in flip_times.values() for t in (ts if isinstance(ts, list) else [ts]))
    duration = round(all_ts[-1] - all_ts[0], 1) if len(all_ts) >= 2 else 0

    return {
        "first_attempt_recall": round(first_pass / max(first_total, 1), 3),
        "cards_studied": len(sm2_cards),
        "completion_rate": round(len(sm2_cards) / max(total_cards, 1), 3),
        "total_reviews": len(all_ratings),
        "rating_distribution": {
            "again": round(sum(1 for q in all_ratings if q <= 2) / total_r, 3),
            "hard": round(sum(1 for q in all_ratings if q == 3) / total_r, 3),
            "good": round(sum(1 for q in all_ratings if q == 4) / total_r, 3),
            "easy": round(sum(1 for q in all_ratings if q == 5) / total_r, 3),
        },
        "session_duration_sec": duration,
    }


# ═══════════════════════════════════════════════════════════
# 3. QUALITY-LEARNING CORRELATIONS (key finding)
# ═══════════════════════════════════════════════════════════

def compute_correlations(session_state: dict, scored_cards: list, final_deck: list) -> dict:
    """Do higher-quality cards get recalled better? This proves the pipeline matters."""
    sm2_cards = session_state.get("sm2_cards", {})
    if not sm2_cards:
        return {"status": "insufficient_data"}

    # Build score lookup — scored_cards (teacher session) or published_quality (student session)
    score_lookup = {}
    if scored_cards:
        for sc in scored_cards:
            score_lookup[sc.card.question] = sc.composite_score
    else:
        pub_q = session_state.get("published_quality", {})
        for q, data in pub_q.items():
            score_lookup[q] = data.get("composite", 0)

    if not score_lookup:
        return {"status": "insufficient_data"}

    high_q_pass, high_q_total = 0, 0
    low_q_pass, low_q_total = 0, 0

    for idx, sm2 in sm2_cards.items():
        idx_int = int(idx)
        if idx_int >= len(final_deck) or not sm2.review_history:
            continue
        card = final_deck[idx_int]
        comp = score_lookup.get(card.question)
        if comp is None:
            continue

        passed = sm2.review_history[0][1] >= 3
        if comp >= 0.8:
            high_q_total += 1
            high_q_pass += int(passed)
        else:
            low_q_total += 1
            low_q_pass += int(passed)

    hq_rate = round(high_q_pass / max(high_q_total, 1), 3)
    lq_rate = round(low_q_pass / max(low_q_total, 1), 3)

    return {
        "high_quality_recall": hq_rate,
        "low_quality_recall": lq_rate,
        "quality_advantage": round(hq_rate - lq_rate, 3),
        "high_quality_cards": high_q_total,
        "low_quality_cards": low_q_total,
    }


# ═══════════════════════════════════════════════════════════
# MASTER EXPORT
# ═══════════════════════════════════════════════════════════

def build_comprehensive_eval_export(session_state: dict, final_deck: list,
                                    scored_cards: list) -> dict:
    """Complete evaluation data — 3 metric sections + per-card detail."""
    # Score lookup: scored_cards (teacher session) or published_quality (student session)
    score_lookup = {}
    if scored_cards:
        for sc in scored_cards:
            score_lookup[sc.card.question] = {
                "composite": round(sc.composite_score, 4),
                "routing": sc.routing_decision,
            }
    else:
        for q, data in session_state.get("published_quality", {}).items():
            score_lookup[q] = {
                "composite": round(data.get("composite", 0), 4),
                "routing": data.get("routing"),
            }

    per_card = []
    for i, c in enumerate(final_deck):
        qs = score_lookup.get(c.question, {})
        sm2 = session_state.get("sm2_cards", {}).get(i)
        per_card.append({
            "index": i,
            "question": c.question, "answer": c.answer,
            "difficulty": c.difficulty, "bloom_level": c.bloom_level,
            "composite_score": qs.get("composite"),
            "routing": qs.get("routing"),
            "sm2_first_rating": sm2.review_history[0][1] if sm2 and sm2.review_history else None,
            "sm2_reviews": len(sm2.review_history) if sm2 else 0,
            "sm2_interval": sm2.interval if sm2 else None,
        })

    # Pre/post test data
    pre = session_state.get("pre_test_scores", {})
    post = session_state.get("post_test_scores", {})
    pre_post = None
    if pre and post:
        pre_post = {
            "test_card_indices": session_state.get("test_indices", []),
            "pre_total": sum(pre.values()),
            "post_total": sum(post.values()),
            "max_score": len(pre) * 2,
            "learning_gain": sum(post.values()) - sum(pre.values()),
            "per_card": {str(ci): {"pre": pre.get(ci, 0), "post": post.get(ci, 0)} for ci in pre},
        }

    return {
        "session_id": session_state.get("study_session_id", "no_id"),
        "role": session_state.get("role", "unknown"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pipeline_metrics": session_state.get("pipeline_metrics", {}),
        "learning_metrics": compute_learning_metrics(session_state, len(final_deck)),
        "quality_correlations": compute_correlations(session_state, scored_cards, final_deck),
        "pre_post_test": pre_post,
        "flashcards": per_card
    }