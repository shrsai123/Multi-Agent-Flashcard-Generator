from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langchain_core.documents import Document


class Flashcard(BaseModel):
    question:str = Field(..., description="The question or prompt for the flashcard.")
    answer:str = Field(..., description="The answer for the flashcard.")
    difficulty: Literal['easy', 'medium', 'hard'] = Field(..., description="The difficulty level of the flashcard.")
    bloom_level:Literal['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create'] = Field(..., description="The Bloom's taxonomy level of the flashcard.")
    source_chunk_id: str = Field(..., description="The ID of the source chunk from which the flashcard was generated.")
    question_type:Literal['definition','concept','application','comparison'] = Field(..., description="The type of question for the flashcard.")


class ScoredFlashcard(BaseModel):
    card: Flashcard
    groundedness: float= Field(..., ge=0.0,le=1.0)
    clarity: float =Field(..., ge=0.0, le=1.0)
    uniqueness: float = Field(..., ge=0.0, le=1.0)
    difficulty_calibration: float = Field(..., ge=0.0, le=1.0)
    justification: str = Field(default="")
    
    @property
    def composite_score(self) -> float:
        return (
            0.4 * self.groundedness
            + 0.3 * self.clarity
            + 0.2 * self.uniqueness
            + 0.1 * self.difficulty_calibration
        )

    @property
    def routing_decision(self) -> str:
        score = self.composite_score
        if score >= 0.8:
            return "auto_approve"
        elif score >= 0.5:
            return "human_review"
        else:
            return "auto_reject"
        
class TeacherAction(BaseModel):
    card_index: int
    action: Literal['approve', 'edit', 'reject', 'regenerate']
    edited_question: Optional[str]=None
    edited_answer: Optional[str]=None
    feedback_note: Optional[str]=None


class FlashcardState(TypedDict, total=False):
    """Shared state flowing through the LangGraph pipeline."""
    pdf_content: str
    content_type: str
    chunks: List[Document]
    raw_cards: List[Flashcard]
    scored_cards: List[ScoredFlashcard]
    approved_cards: List[Flashcard]
    human_queue: List[ScoredFlashcard]
    rejected_cards: List[ScoredFlashcard]
    teacher_actions: List[TeacherAction]
    teacher_edits: List[Flashcard]
    final_deck: List[Flashcard]
    error: Optional[str]
    source_filename: str
