"""
config.py

Central, single source of truth for every configurable value in the RAG
module. Nothing else in `rag/` should read `os.environ` directly - always
go through this module so the whole system stays configurable via .env.
"""

import os
import re
from pathlib import Path

try:
    # python-dotenv is optional at import time but expected to be installed
    # (see requirements.txt). If it's missing we just fall back to whatever
    # is already in the process environment.
    from dotenv import load_dotenv

    _ENV_PATH = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=_ENV_PATH, override=False)
except ImportError:  # pragma: no cover - defensive only
    pass


def _get_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# --------------------------------------------------------------------------
# Groq (LLM generation)
# --------------------------------------------------------------------------
GROQ_API_KEY: str = _get_str("GROQ_API_KEY", "")
# Model name is NEVER hardcoded elsewhere in the app - always read from here.
GROQ_MODEL: str = _get_str("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_TEMPERATURE: float = _get_float("GROQ_TEMPERATURE", 0.0)
GROQ_MAX_TOKENS: int = _get_int("GROQ_MAX_TOKENS", 800)
# How many times to retry generation if the model returns malformed JSON.
GROQ_JSON_RETRIES: int = _get_int("GROQ_JSON_RETRIES", 1)

# --------------------------------------------------------------------------
# Embeddings (local, free - never Groq)
# --------------------------------------------------------------------------
EMBEDDING_MODEL: str = _get_str("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --------------------------------------------------------------------------
# Paths / persistence
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(_get_str("RAG_DATA_DIR", str(BASE_DIR / "data")))
INDEX_PATH = DATA_DIR / "faiss.index"
METADATA_PATH = DATA_DIR / "metadata.pkl"
ERROR_CODE_MAP_PATH = DATA_DIR / "error_code_map.json"
MANUALS_MANIFEST = Path(
    _get_str("RAG_MANUALS_MANIFEST", str(BASE_DIR / "demo" / "manuals_manifest.json"))
)

# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------
CHUNK_TARGET_CHARS: int = _get_int("CHUNK_TARGET_CHARS", 900)
CHUNK_OVERLAP_CHARS: int = _get_int("CHUNK_OVERLAP_CHARS", 150)

# --------------------------------------------------------------------------
# Retrieval / sufficiency thresholds (all configurable, none are "magic")
# --------------------------------------------------------------------------
TOP_K = _get_int("RAG_TOP_K", 8)
CONTEXT_TOP_N = _get_int("RAG_CONTEXT_TOP_N", 5)

# Minimum cosine similarity (0-1, since embeddings are normalized and we use
# inner product search) for a chunk to be considered relevant at all.
MIN_RELEVANCE_SCORE: float = _get_float("RAG_MIN_RELEVANCE_SCORE", 0.35)

# Minimum *top* relevance score required before we trust semantic-only
# retrieval (i.e. no exact error code match) enough to call Groq.
MIN_TOP_SCORE_SEMANTIC: float = _get_float("RAG_MIN_TOP_SCORE_SEMANTIC", 0.45)

# Minimum number of relevant chunks required for sufficiency when there is
# no exact error-code hit to lean on.
MIN_RELEVANT_CHUNKS: int = _get_int("RAG_MIN_RELEVANT_CHUNKS", 1)

# Regex used for explicit error-code detection in free text.
# Deliberately narrower than a generic "letters+digits" pattern (which would
# also match model numbers like "X200" or "H500") - troubleshooting error
# codes in this project's manuals always use an E / ERR / FLT / ALM style
# prefix. Adjust via RAG_ERROR_CODE_REGEX in .env if a manual set uses a
# different convention.
ERROR_CODE_REGEX = re.compile(
    _get_str("RAG_ERROR_CODE_REGEX", r"\b(?:E|ERR|FLT|ALM)-?\d{2,4}\b"),
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# Query Expansion (NEW)
# --------------------------------------------------------------------------
# Enable/disable query expansion for improved semantic recall.
# When enabled, queries are expanded into semantic variations before
# embedding and retrieval. This improves recall by catching synonyms,
# alternative phrasings, and related terms.
ENABLE_QUERY_EXPANSION: bool = _get_bool("RAG_ENABLE_QUERY_EXPANSION", True)

# Maximum number of expanded query variants to search.
# Higher values improve recall but increase latency and cost.
# Recommended: 3-5 for good balance.
MAX_QUERY_VARIANTS: int = _get_int("RAG_MAX_QUERY_VARIANTS", 4)

# Follow-up conversation memory
CONVERSATION_HISTORY_LIMIT: int = _get_int("RAG_CONVERSATION_HISTORY_LIMIT", 6)


def normalize_error_code(raw: str) -> str:
    """Normalize an error code string for consistent comparisons, e.g.
    'e-101' / 'E 101' / 'e101' -> 'E101'."""
    return re.sub(r"[\s\-]", "", raw).upper()
