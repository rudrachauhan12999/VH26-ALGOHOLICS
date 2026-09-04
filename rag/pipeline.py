"""
pipeline.py

The ONLY module the backend developer needs to import:

    from rag.pipeline import troubleshoot

    result = troubleshoot(query, machine=None, model=None, conversation_id=None)

`result` is always a plain JSON-serializable dict with a "status" of
exactly one of: "success" | "ambiguous" | "insufficient" | "error".

Internal flow:

    USER QUERY
        v
    QUERY ANALYSIS (error code / machine / model detection + conversation
                     context merge)
        v
    AMBIGUITY CHECK (error code with no resolvable machine/model)
        v
    RETRIEVAL (hybrid: exact code + semantic + machine/model filter)
        v
    RELEVANCE / SUFFICIENCY CHECK
        v
    ONLY IF SUFFICIENT -> GROQ -> STRUCTURED ANSWER
"""

from typing import Optional, List

from rag.config import (
    CONTEXT_TOP_N,
    MIN_RELEVANT_CHUNKS,
    MIN_TOP_SCORE_SEMANTIC,
)
from rag.conversation.memory import GLOBAL_MEMORY
from rag.generation.groq_service import generate_answer, GroqGenerationError
from rag.retrieval.retriever import analyze_query, retrieve, relevant_chunks
from rag.schemas import RetrievedChunk, SourceCitation
from rag.vectorstore.vector_store import VectorStore

_vector_store: Optional[VectorStore] = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        store = VectorStore()
        store.load()
        _vector_store = store
    return _vector_store


def _sources_from_chunks(chunks: List[RetrievedChunk]) -> List[dict]:
    seen = set()
    sources = []
    for chunk in chunks:
        meta = chunk.metadata
        key = (meta.manual, meta.machine, meta.model, meta.section, meta.page)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            SourceCitation(
                manual=meta.manual,
                machine=meta.machine,
                model=meta.model,
                section=meta.section,
                page=meta.page,
            ).model_dump()
        )
    return sources


def _is_sufficient(chunks: List[RetrievedChunk], has_error_code: bool) -> bool:
    good_chunks = relevant_chunks(chunks)
    if not good_chunks:
        return False

    if has_error_code:
        # An exact error-code match is strong, self-verifying evidence.
        return any(c.exact_code_match for c in good_chunks)

    # No exact code to lean on - require a reasonably confident top semantic
    # score AND a minimum number of supporting chunks.
    top_score = max(c.semantic_score for c in good_chunks)
    return top_score >= MIN_TOP_SCORE_SEMANTIC and len(good_chunks) >= MIN_RELEVANT_CHUNKS


def troubleshoot(
    query: str,
    machine: Optional[str] = None,
    model: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> dict:
    try:
        query = (query or "").strip()
        if not query:
            return {"status": "error", "message": "Unable to process the troubleshooting request."}

        store = _get_vector_store()

        # ------------------------------------------------------------
        # 1. QUERY ANALYSIS
        # ------------------------------------------------------------
        analysis = analyze_query(query, store)
        error_code = analysis.error_code
        resolved_machine = machine or analysis.detected_machine
        resolved_model = model or analysis.detected_model

        conversation_state = None
        if conversation_id:
            conversation_state = GLOBAL_MEMORY.get(conversation_id)
            # Fall back to conversation memory ONLY for whatever the current
            # turn didn't already establish - this is what makes follow-up
            # questions like "What if that doesn't fix it?" work.
            if error_code is None:
                error_code = conversation_state.last_error_code
            if resolved_machine is None:
                resolved_machine = conversation_state.last_machine
            if resolved_model is None:
                resolved_model = conversation_state.last_model

        # ------------------------------------------------------------
        # 2. AMBIGUITY CHECK
        # ------------------------------------------------------------
        if error_code and not resolved_machine:
            candidates = store.machines_for_error_code(error_code)
            if len(candidates) > 1:
                if conversation_id:
                    GLOBAL_MEMORY.update(
                        conversation_id, query, error_code, None, None, status="ambiguous"
                    )
                options = [{"machine": m, "model": mo} for m, mo in candidates]
                return {
                    "status": "ambiguous",
                    "message": "This error code exists for multiple machines.",
                    "options": options,
                }
            if len(candidates) == 1:
                resolved_machine, resolved_model = candidates[0]
            # If len(candidates) == 0, the code isn't known at all - retrieval
            # below will naturally come back insufficient.

        # ------------------------------------------------------------
        # 3. RETRIEVAL
        # ------------------------------------------------------------
        retrieved = retrieve(
            query=query,
            vector_store=store,
            machine=resolved_machine,
            model=resolved_model,
            error_code=error_code,
        )

        # ------------------------------------------------------------
        # 4. SUFFICIENCY CHECK
        # ------------------------------------------------------------
        if not _is_sufficient(retrieved, has_error_code=bool(error_code)):
            if conversation_id:
                GLOBAL_MEMORY.update(
                    conversation_id, query, error_code, resolved_machine, resolved_model,
                    status="insufficient",
                )
            return {
                "status": "insufficient",
                "message": "No sufficient information was found in the available manuals.",
                "sources": [],
            }

        good_chunks = relevant_chunks(retrieved)[:CONTEXT_TOP_N]

        # ------------------------------------------------------------
        # 5. GENERATION (Groq) - only reached when evidence is sufficient
        # ------------------------------------------------------------
        try:
            answer = generate_answer(query, good_chunks, error_code=error_code)
        except GroqGenerationError:
            return {"status": "error", "message": "Unable to process the troubleshooting request."}

        if answer is None:
            # The model itself judged the context insufficient - trust that.
            if conversation_id:
                GLOBAL_MEMORY.update(
                    conversation_id, query, error_code, resolved_machine, resolved_model,
                    status="insufficient",
                )
            return {
                "status": "insufficient",
                "message": "No sufficient information was found in the available manuals.",
                "sources": [],
            }

        # Sources always come from retrieval metadata, never from the LLM.
        answer_dict = answer.model_dump()
        answer_dict["sources"] = _sources_from_chunks(good_chunks)
        if not answer_dict.get("error_code"):
            answer_dict["error_code"] = error_code

        if conversation_id:
            GLOBAL_MEMORY.update(
                conversation_id, query, error_code, resolved_machine, resolved_model,
                status="success",
            )

        return {"status": "success", "answer": answer_dict}

    except Exception:
        return {"status": "error", "message": "Unable to process the troubleshooting request."}
