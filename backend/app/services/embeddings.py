"""
Loads the sentence-transformers embedding model once at import time and
reuses it across requests. Loading a transformer model is expensive (a few
seconds), so we never want to do this per-request.
"""
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input text."""
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single query string (used later in Phase 3 for retrieval)."""
    return embed_texts([text])[0]
