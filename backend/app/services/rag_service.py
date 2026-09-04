"""
RAG service boundary.

Every call the backend makes into the RAG + AI layer goes through this
file. This now delegates directly to the real pipeline in `rag/pipeline.py`.

`rag/` must be installed/importable alongside `backend/` (i.e. as a
sibling top-level package), with its dependencies installed
(`pip install -r rag/requirements.txt`), its `.env` configured
(`GROQ_API_KEY`, etc.), and its index built:

    python -m rag.demo.build_demo_data
    python -m rag.ingest_manuals

No route, schema, or response contract changes are needed here — the
routes only ever call `rag_service.troubleshoot(...)` and return
whatever it gives back, and `rag.pipeline.troubleshoot()` honors the
exact same contract the mock did.
"""

from typing import Dict, List, Optional

from rag.pipeline import troubleshoot as real_troubleshoot

# Demo data shared by /api/machines and /api/manuals.
# TODO: replace with real data pulled from the RAG layer's manual index
# (e.g. rag.vectorstore.vector_store) once that lookup exists.
DEMO_MACHINES: List[Dict[str, str]] = [
    {"machine": "Machine A", "model": "X200"},
    {"machine": "Machine B", "model": "H500"},
]

DEMO_MANUALS: List[Dict[str, str]] = [
    {"manual": "Machine_A_Manual.pdf", "machine": "Machine A", "model": "X200"},
    {"manual": "Machine_B_Manual.pdf", "machine": "Machine B", "model": "H500"},
]


def troubleshoot(
    query: str,
    machine: Optional[str] = None,
    model: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict:
    """
    Passes straight through to the real RAG pipeline. Response shape is
    whatever `rag.pipeline.troubleshoot()` returns: a dict with a
    "status" of "success" | "ambiguous" | "insufficient" | "error".
    """
    return real_troubleshoot(
        query=query,
        machine=machine,
        model=model,
        conversation_id=conversation_id,
    )