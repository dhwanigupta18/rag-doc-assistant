"""
Loads the embedding model once at import time and reuses it across requests.
Uses fastembed (ONNX Runtime) instead of sentence-transformers/PyTorch — no
GPU or GB-scale PyTorch dependency, which matters on memory-constrained free
hosting tiers (512MB total).

Embeddings are generated in small batches rather than all at once. On a
memory-constrained host, embedding e.g. 20+ chunks in a single batch spikes
peak memory considerably higher than processing them a few at a time — this
trades a small amount of latency for a meaningfully lower memory ceiling.
"""
from functools import lru_cache
from fastembed import TextEmbedding

from app.core.config import settings

BATCH_SIZE = 8


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    return TextEmbedding(model_name=settings.EMBEDDING_MODEL, threads=1)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, processed in small chunks to cap peak memory."""
    model = get_embedding_model()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_vectors = list(model.embed(batch))
        vectors.extend(v.tolist() for v in batch_vectors)
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a single query string (used in Phase 3 for retrieval)."""
    return embed_texts([text])[0]