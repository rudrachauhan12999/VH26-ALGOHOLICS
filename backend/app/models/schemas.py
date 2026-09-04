"""
Pydantic models for the troubleshooting API.

The request schema is a strict contract with the frontend — field names
must not change. Response shapes vary by status (success / ambiguous /
insufficient / error), so the response models here are used for internal
typing and documentation; the routes return plain dicts matching the
RAG service contract exactly.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class TroubleshootRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Error code or symptom description")
    machine: Optional[str] = Field(None, description="Machine name, e.g. 'Machine A'")
    model: Optional[str] = Field(None, description="Model number, e.g. 'X200'")
    conversation_id: Optional[str] = Field(None, description="Session/conversation identifier")


class Source(BaseModel):
    manual: str
    machine: str
    model: str
    section: str
    page: int


class Answer(BaseModel):
    error_code: str
    meaning: str
    causes: List[str]
    corrective_actions: List[str]
    warnings: List[str] = []
    sources: List[Source]


class TroubleshootOption(BaseModel):
    machine: str
    model: str


class MachineInfo(BaseModel):
    machine: str
    model: str


class ManualInfo(BaseModel):
    manual: str
    machine: str
    model: str


class UploadResponse(BaseModel):
    status: str
    message: str
    filename: str
    size_bytes: int
