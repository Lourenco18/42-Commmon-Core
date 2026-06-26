"""Pydantic data models for the RAG pipeline.

This module defines all the data structures used throughout the system,
following the specification in the project subject.
"""

import uuid
from typing import List, Union

from pydantic import BaseModel, Field


class MinimalSource(BaseModel):
    """Represents a minimal source of information from the knowledge base."""

    file_path: str
    first_character_index: int
    last_character_index: int


class UnansweredQuestion(BaseModel):
    """Represents a question without an answer."""

    question_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """Represents a question with its answer and source references."""

    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """Represents a dataset of RAG questions (answered or unanswered)."""

    rag_questions: List[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    """Represents search results for a single question."""

    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Represents search results with a generated answer."""

    answer: str


class StudentSearchResults(BaseModel):
    """Represents the full search results for a dataset."""

    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(StudentSearchResults):
    """Represents search results with generated answers for a dataset."""

    search_results: List[MinimalAnswer]  # type: ignore[assignment]
