"""
embeddings/embedder.py

Local, free embedding generation via sentence-transformers. Groq is never
used for embeddings - only for final answer generation.

The model name is configurable (RAG config / EMBEDDING_MODEL env var), and
the SentenceTransformer instance is loaded lazily and cached so repeated
calls (e.g. once per query) don't reload the model from disk each time.
"""

from typing import List
import numpy as np

from rag.config import EMBEDDING_MODEL

_model = None
_model_name = None


def _get_model():
    global _model, _model_name
    if _model is None or _model_name != EMBEDDING_MODEL:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL)
        _model_name = EMBEDDING_MODEL
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of strings, returning an (N, D) float32 array with each
    row L2-normalized so inner-product search behaves like cosine
    similarity."""
    if not texts:
        return np.zeros((0, embedding_dim()), dtype="float32")

    model = _get_model()
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.astype("float32")


def embed_query(text: str) -> np.ndarray:
    """Embed a single query string, returning a (D,) float32 vector."""
    return embed_texts([text])[0]


def embedding_dim() -> int:
    return _get_model().get_sentence_embedding_dimension()
