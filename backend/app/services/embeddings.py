"""
Loads the embedding model once at import time and reuses it across requests.
Uses fastembed (ONNX Runtime) instead of sentence-transformers/PyTorch — the
same BAAI/bge-small-en-v1.5 model, but without pulling in PyTorch, which
alone can exceed memory limits on constrained free-tier hosting.
"""
from functools import lru_cache
from fastembed import TextEmbedding

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    return TextEmbedding(model_name=settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input text."""
    model = get_embedding_model()
    vectors = list(model.embed(texts))
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    """Embed a single query string (used in Phase 3 for retrieval)."""
    return embed_texts([text])[0]