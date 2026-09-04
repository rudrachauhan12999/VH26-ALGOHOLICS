"""
schemas.py

Pydantic models used across the RAG pipeline. Keeping these in one place
means every module (chunker, retriever, groq_service, pipeline) agrees on
exactly what a "chunk", "source" or "answer" looks like.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    manual: str
    machine: str
    model: str
    section: str = "General"
    page: int


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata


class RetrievedChunk(BaseModel):
    """A chunk plus the score(s) it earned during retrieval."""

    text: str
    metadata: ChunkMetadata
    semantic_score: float = 0.0
    exact_code_match: bool = False


class SourceCitation(BaseModel):
    manual: str
    machine: str
    model: str
    section: str
    page: int


class TroubleshootAnswer(BaseModel):
    """The structured payload Groq must produce (validated on the way out)."""

    error_code: Optional[str] = None
    meaning: str
    causes: List[str] = Field(default_factory=list)
    corrective_actions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    # sources are re-derived from retrieval, not trusted from the LLM, but we
    # keep the field here so the shape matches the final API response.
    sources: List[SourceCitation] = Field(default_factory=list)


class AmbiguousOption(BaseModel):
    machine: str
    model: str


StatusType = Literal["success", "ambiguous", "insufficient", "error"]


class SuccessResponse(BaseModel):
    status: Literal["success"] = "success"
    answer: TroubleshootAnswer


class AmbiguousResponse(BaseModel):
    status: Literal["ambiguous"] = "ambiguous"
    message: str
    options: List[AmbiguousOption]


class InsufficientResponse(BaseModel):
    status: Literal["insufficient"] = "insufficient"
    message: str
    sources: List[SourceCitation] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
