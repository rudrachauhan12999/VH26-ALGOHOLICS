"""
retrieval/retriever.py

Implements the retrieval half of the pipeline:

  QUERY ANALYSIS -> QUERY EXPANSION -> RETRIEVAL -> RELEVANCE CHECK -> MACHINE/MODEL
  CONSISTENCY CHECK -> SUFFICIENCY CHECK

Retrieval never relies on embeddings alone. For every query we:
  1. Detect an explicit error code via regex, if present.
  2. Detect a machine/model mention in free text, if present.
  3. Expand the query into semantic variations (NEW).
  4. Run semantic vector search on multiple expanded queries.
  5. Boost/keep chunks that contain an exact error-code match.
  6. Filter/prefer chunks matching the given (or detected) machine/model.

The pipeline module (`rag/pipeline.py`) is responsible for turning the
output of this module into ambiguous/insufficient/success decisions - this
module's job is purely "find and score the right evidence".
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from rag.config import (
    ERROR_CODE_REGEX,
    MIN_RELEVANCE_SCORE,
    TOP_K,
    normalize_error_code,
)
from rag.embeddings.embedder import embed_query
from rag.retrieval.query_expander import expand_query
from rag.schemas import RetrievedChunk, ChunkMetadata
from rag.vectorstore.vector_store import VectorStore


@dataclass
class QueryAnalysis:
    error_code: Optional[str]
    detected_machine: Optional[str]
    detected_model: Optional[str]


def detect_error_code(query: str) -> Optional[str]:
    matches = ERROR_CODE_REGEX.findall(query)
    if not matches:
        return None
    # If multiple candidate codes appear, take the first - good enough for a
    # hackathon-scale system, and callers can always pass an explicit code.
    return normalize_error_code(matches[0])


def detect_machine_model(
    query: str, known_machines: List[Tuple[str, str]]
) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort detection of a machine/model mention inside free text,
    e.g. 'Why is Machine A overheating?' -> ('Machine A', None)."""
    lowered = query.lower()

    detected_machine = None
    detected_model = None

    # Prefer the most specific match: machine + model mentioned together.
    for machine, model in known_machines:
        if machine.lower() in lowered and model.lower() in lowered:
            return machine, model

    for machine, model in known_machines:
        if machine.lower() in lowered:
            detected_machine = machine
            # Only attach the model if it's unambiguous for that machine.
            break

    for machine, model in known_machines:
        if model.lower() in lowered:
            detected_model = model
            if detected_machine is None:
                detected_machine = machine
            break

    return detected_machine, detected_model


def analyze_query(query: str, vector_store: VectorStore) -> QueryAnalysis:
    error_code = detect_error_code(query)
    machine, model = detect_machine_model(query, vector_store.known_machines())
    return QueryAnalysis(error_code=error_code, detected_machine=machine, detected_model=model)


def retrieve(
    query: str,
    vector_store: VectorStore,
    machine: Optional[str] = None,
    model: Optional[str] = None,
    error_code: Optional[str] = None,
    top_k: int = TOP_K,
) -> List[RetrievedChunk]:
    """Hybrid retrieval combining query expansion, exact error-code matching
    with semantic search, then applying machine/model preference.
    
    Query expansion generates semantic variations of the user query, which are
    then embedded and searched independently. Results are merged, deduplicated,
    and ranked by relevance.
    """

    # Expand the query into semantic variations
    query_variations = expand_query(query, error_code=error_code)
    
    # Collect all candidates from all query variations
    all_candidates: List[RetrievedChunk] = []
    seen_keys = set()
    
    normalized_code = normalize_error_code(error_code) if error_code else None
    
    for variant in query_variations:
        query_vector = embed_query(variant)
        raw_results = vector_store.search(query_vector, top_k=max(top_k, 20))
        
        for text, meta, score in raw_results:
            exact_match = False
            if normalized_code:
                page_codes = {normalize_error_code(c) for c in ERROR_CODE_REGEX.findall(text)}
                exact_match = normalized_code in page_codes

            key = (meta.manual, meta.page, text)
            if key in seen_keys:
                # Keep the highest score if we've seen this before
                for existing in all_candidates:
                    if (existing.metadata.manual, existing.metadata.page, existing.text) == key:
                        existing.semantic_score = max(existing.semantic_score, score)
                        break
                continue
            
            seen_keys.add(key)
            all_candidates.append(
                RetrievedChunk(
                    text=text,
                    metadata=meta,
                    semantic_score=score,
                    exact_code_match=exact_match,
                )
            )
    
    candidates = all_candidates
    
    # If an error code was given/detected but didn't turn up in the top
    # semantic results, pull in chunks that contain it explicitly - exact
    # error-code matching must never be at the mercy of embedding recall.
    if normalized_code:
        already_have = {(c.metadata.manual, c.metadata.page, c.text) for c in candidates}
        # Use the original query for the exhaustive exact-code sweep
        query_vector = embed_query(query)
        for text, meta, score in vector_store.search(query_vector, top_k=vector_store.index.ntotal or 1):
            key = (meta.manual, meta.page, text)
            if key in already_have:
                continue
            page_codes = {normalize_error_code(c) for c in ERROR_CODE_REGEX.findall(text)}
            if normalized_code in page_codes:
                candidates.append(
                    RetrievedChunk(
                        text=text,
                        metadata=meta,
                        semantic_score=score,
                        exact_code_match=True,
                    )
                )
                already_have.add(key)

    # Apply machine/model preference: filter first (strict), and only fall
    # back to "prefer but don't discard" if filtering would remove
    # everything relevant (e.g. detection was slightly wrong).
    if machine:
        filtered = [c for c in candidates if c.metadata.machine.lower() == machine.lower()]
        if filtered:
            candidates = filtered
    if model:
        filtered = [c for c in candidates if c.metadata.model.lower() == model.lower()]
        if filtered:
            candidates = filtered

    def sort_key(c: RetrievedChunk):
        return (c.exact_code_match, c.semantic_score)

    candidates.sort(key=sort_key, reverse=True)

    # Deduplicate identical (manual, page, text) entries that may have been
    # added twice (once from query expansion search, once from the exact-code sweep).
    seen = set()
    deduped: List[RetrievedChunk] = []
    for c in candidates:
        key = (c.metadata.manual, c.metadata.page, c.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    return deduped[:top_k]


def relevant_chunks(chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
    """Chunks that clear the minimum relevance bar - either an exact error
    code match, or a semantic score above the configured threshold."""
    return [
        c for c in chunks if c.exact_code_match or c.semantic_score >= MIN_RELEVANCE_SCORE
    ]
