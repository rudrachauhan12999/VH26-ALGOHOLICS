"""
conversation/memory.py

Deliberately simple in-process conversation memory - no database, just a
dict keyed by conversation_id. This is enough to support follow-up
questions like:

    User: "E101"
    Assistant: <answer about motor overheating>
    User: "What if that doesn't fix it?"

The second query has no error code and no machine/model, so the pipeline
pulls the last known error_code/machine/model from memory and merges them
in before retrieval.

Note: this memory is process-local and resets on restart. That's an
explicit, intentional simplicity trade-off for a hackathon project - the
backend team can swap this module out for something persistent later
without touching the rest of `rag/`.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rag.config import CONVERSATION_HISTORY_LIMIT


@dataclass
class Turn:
    query: str
    error_code: Optional[str]
    machine: Optional[str]
    model: Optional[str]
    status: str


@dataclass
class ConversationState:
    last_error_code: Optional[str] = None
    last_machine: Optional[str] = None
    last_model: Optional[str] = None
    history: List[Turn] = field(default_factory=list)


class ConversationMemory:
    def __init__(self):
        self._conversations: Dict[str, ConversationState] = {}

    def get(self, conversation_id: str) -> ConversationState:
        return self._conversations.setdefault(conversation_id, ConversationState())

    def update(
        self,
        conversation_id: str,
        query: str,
        error_code: Optional[str],
        machine: Optional[str],
        model: Optional[str],
        status: str,
    ) -> None:
        state = self.get(conversation_id)

        # Only overwrite the "last known" context with real values - a
        # follow-up question with no new error code/machine/model shouldn't
        # erase what we already knew.
        if error_code:
            state.last_error_code = error_code
        if machine:
            state.last_machine = machine
        if model:
            state.last_model = model

        state.history.append(
            Turn(query=query, error_code=error_code, machine=machine, model=model, status=status)
        )
        state.history[:] = state.history[-CONVERSATION_HISTORY_LIMIT:]

    def reset(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)


# A single process-wide instance is enough for a hackathon deployment. The
# backend developer imports `troubleshoot()` from rag.pipeline and never
# needs to touch this directly.
GLOBAL_MEMORY = ConversationMemory()
