"""
retrieval/query_expander.py

Query expansion module for RAG pipeline.

Expands user queries into semantic variations before embedding and retrieval.
This improves recall by catching synonyms, alternative phrasings, and related
terms that users might naturally use but don't appear exactly in manuals.

Examples:
  - "motor hot" expands to ["motor hot", "motor overheating", "motor temperature high"]
  - "E101" expands to ["E101", "error E101", "error code E101", "E 101"]
  - "clicking noise" expands to ["clicking noise", "clicking sound", "click sound"]
"""

import re
from typing import List, Optional
from rag.config import ERROR_CODE_REGEX, normalize_error_code


def _expand_error_code(code: str) -> List[str]:
    """
    Expand an error code into multiple format variations.
    
    E.g., "E101" -> ["E101", "error E101", "error code E101", "E 101", "E-101"]
    
    This helps catch variations in how users or documents might reference the code.
    """
    normalized = normalize_error_code(code)
    # Remove the first letter to get the numeric part
    numeric = normalized[1:] if normalized and normalized[0] in 'EFAL' else normalized
    
    variations = [
        normalized,  # E101
        f"error {normalized}",  # error E101
        f"error code {normalized}",  # error code E101
        f"{normalized[0]} {numeric}",  # E 101
        f"{normalized[0]}-{numeric}",  # E-101
    ]
    
    return list(set(variations))  # Deduplicate


def _expand_freetext(query: str) -> List[str]:
    """
    Expand free-text queries by adding synonyms and related terms.
    
    Uses heuristic patterns to catch common machine troubleshooting phrasings.
    """
    variations = [query]  # Always include the original
    
    lower_query = query.lower()
    
    # Temperature/heating synonyms
    if any(word in lower_query for word in ["hot", "heat", "warm", "temp"]):
        synonyms = ["overheating", "temperature high", "excessive heat", "thermal"]
        for syn in synonyms:
            if syn not in lower_query:
                variations.append(query.replace(
                    next((w for w in ["hot", "heat", "warm", "temp"] if w in lower_query), ""),
                    syn
                ))
    
    # Sound/noise synonyms
    if any(word in lower_query for word in ["noise", "sound", "click", "knock", "grinding", "squeal"]):
        if "click" in lower_query or "clicking" in lower_query:
            variations.extend([
                query.replace("clicking", "click sound"),
                query.replace("clicking", "clicking sound"),
            ])
        if "noise" in lower_query and "sound" not in lower_query:
            variations.append(query.replace("noise", "sound"))
    
    # Pressure/flow synonyms
    if any(word in lower_query for word in ["pressure", "flow", "hydraulic", "pump"]):
        if "low" in lower_query or "pressure" in lower_query:
            variations.extend([
                query.replace("low pressure", "insufficient pressure"),
                query.replace("pressure", "hydraulic pressure"),
            ])
    
    # Vibration/movement synonyms
    if any(word in lower_query for word in ["vibrat", "shake", "shake", "wobble"]):
        variations.extend([
            query.replace("vibrat", "shake"),
            query.replace("wobble", "vibration"),
        ])
    
    # Add more specific variants by looking for machine/model mentions
    # and adding contextual phrasings
    if "machine" in lower_query or "model" in lower_query:
        # If they mention machine/model, also try without it for broader search
        base = re.sub(r"(machine|model)\s+\w+", "", query, flags=re.IGNORECASE).strip()
        if base and base != query:
            variations.append(base)
    
    # Deduplicate (preserve order, remove exact duplicates)
    seen = set()
    deduped = []
    for v in variations:
        if v.lower() not in seen:
            deduped.append(v)
            seen.add(v.lower())
    
    return deduped


def expand_query(
    query: str,
    error_code: Optional[str] = None,
) -> List[str]:
    """
    Expand a query into multiple search variants.
    
    If an error code is detected, generates code format variations.
    For free-text queries, generates semantic/synonym variations.
    
    Args:
        query: The original user query
        error_code: Optional pre-detected error code from query analysis
    
    Returns:
        List of query variations, with the original query first.
        All variations are unique and in a reasonable order for retrieval.
    
    Example:
        >>> expand_query("E101 on machine A", error_code="E101")
        ["E101 on machine A", "error E101 on machine A", "error code E101 on machine A", ...]
    """
    if error_code:
        # Error-code-driven query: expand the code format
        code_variations = _expand_error_code(error_code)
        # Try each code format as a variant of the original query
        results = [query]
        for code_var in code_variations[1:]:  # Skip the first (original code)
            # Replace the detected code with each variation
            expanded = query.replace(error_code, code_var)
            if expanded not in results:
                results.append(expanded)
        return results
    else:
        # Free-text query: expand with synonyms and phrasings
        return _expand_freetext(query)
