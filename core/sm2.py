from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
 
 
@dataclass
class SM2Card:
    """SM-2 scheduling state for one flashcard."""
    card_index: int
    easiness_factor: float = 2.5
    interval: int = 0            # days
    repetitions: int = 0
    next_review: Optional[float] = None   # unix timestamp
    last_reviewed: Optional[float] = None
    review_history: List[Tuple[float, int]] = field(default_factory=list)
 
    @property
    def is_due(self) -> bool:
        if self.next_review is None:
            return True
        return time.time() >= self.next_review
 
    @property
    def status(self) -> str:
        if self.next_review is None:
            return "new"
        if self.is_due:
            return "due"
        remaining = self.next_review - time.time()
        if remaining < 3600:
            return f"due in {int(remaining / 60)}m"
        elif remaining < 86400:
            return f"due in {remaining / 3600:.1f}h"
        else:
            return f"due in {remaining / 86400:.1f}d"
 
    def review(self, quality: int) -> dict:
        """Process a review rating (0-5). Returns update summary."""
        assert 0 <= quality <= 5
        now = time.time()
        old_ef = self.easiness_factor
        old_interval = self.interval
 
        if quality < 3:
            # Failed — reset
            self.repetitions = 0
            self.interval = 0
        else:
            # Passed — advance schedule
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.easiness_factor)
            self.repetitions += 1
 
        # Update easiness factor (always, pass or fail)
        self.easiness_factor = max(
            1.3,
            self.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )
 
        self.last_reviewed = now
        self.next_review = now + (self.interval * 86400)
        self.review_history.append((now, quality))
 
        return {
            "quality": quality,
            "old_ef": round(old_ef, 3),
            "new_ef": round(self.easiness_factor, 3),
            "old_interval": old_interval,
            "new_interval": self.interval,
            "repetitions": self.repetitions,
        }
 
    def to_dict(self) -> dict:
        return {
            "card_index": self.card_index,
            "easiness_factor": round(self.easiness_factor, 4),
            "interval": self.interval,
            "repetitions": self.repetitions,
            "next_review": self.next_review,
            "last_reviewed": self.last_reviewed,
            "review_count": len(self.review_history),
            "review_history": [{"timestamp": ts, "quality": q} for ts, q in self.review_history],
        }
 
 
# ── Simplified 4-button rating (maps to SM2 0-5 scale) ──
 
RATING_BUTTONS = {
    "again": {"quality": 1, "color": "#f43f5e", "label": "Again", "icon": "✗", "desc": "Didn't know it"},
    "hard":  {"quality": 3, "color": "#f59e0b", "label": "Hard",  "icon": "⚡", "desc": "Got it, with effort"},
    "good":  {"quality": 4, "color": "#10b981", "label": "Good",  "icon": "✓", "desc": "Recalled correctly"},
    "easy":  {"quality": 5, "color": "#22d3ee", "label": "Easy",  "icon": "★", "desc": "Instant recall"},
}
 
 
def get_or_create_sm2(session_state: dict, card_index: int) -> SM2Card:
    """Get existing SM2Card from session state, or create a new one."""
    sm2_cards = session_state.setdefault("sm2_cards", {})
    if card_index not in sm2_cards:
        sm2_cards[card_index] = SM2Card(card_index=card_index)
    return sm2_cards[card_index]
 
 
def get_due_cards(session_state: dict, total_cards: int) -> List[int]:
    """Return indices of cards that are due for review, new cards first."""
    sm2_cards = session_state.get("sm2_cards", {})
    due = []
    new = []
    for i in range(total_cards):
        card = sm2_cards.get(i)
        if card is None:
            new.append(i)
        elif card.is_due:
            due.append(i)
    return new + due  # new cards first, then due cards
 
 
def get_sm2_summary(session_state: dict, total_cards: int) -> dict:
    """Compute summary stats for the SM2 state."""
    sm2_cards = session_state.get("sm2_cards", {})
    new_count = 0
    due_count = 0
    learning_count = 0
    mastered_count = 0
    total_reviews = 0
 
    for i in range(total_cards):
        card = sm2_cards.get(i)
        if card is None:
            new_count += 1
        elif card.is_due:
            due_count += 1
        elif card.interval >= 21:
            mastered_count += 1
        else:
            learning_count += 1
        if card:
            total_reviews += len(card.review_history)
 
    return {
        "new": new_count,
        "due": due_count,
        "learning": learning_count,
        "mastered": mastered_count,
        "total_reviews": total_reviews,
    }