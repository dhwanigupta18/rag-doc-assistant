"""
Generates embeddings via Jina AI's hosted Embeddings API instead of running
a model locally. This removes local ML inference from the server entirely —
important on memory-constrained free hosting, where even a "small" local
embedding model plus its runtime was enough to exceed 512MB alongside the
rest of the FastAPI stack.

Jina's API distinguishes "passage" embeddings (for indexed document chunks)
from "query" embeddings (for search queries) — asymmetric embedding, which
is the correct way to use this model and can noticeably improve retrieval
quality over treating both the same way.
"""
import requests

from app.core.config import settings

JINA_API_URL = "https://api.jina.ai/v1/embeddings"


def _embed(texts: list[str], task: str) -> list[list[float]]:
    response = requests.post(
        JINA_API_URL,
        headers={
            "Authorization": f"Bearer {settings.JINA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.EMBEDDING_MODEL,
            "task": task,
            "input": texts,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()["data"]
    # Jina returns results possibly out of order; each item carries its
    # original index, so sort by that before extracting embeddings.
    data.sort(key=lambda item: item["index"])
    return [item["embedding"] for item in data]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed document chunks (used during ingestion)."""
    return _embed(texts, task="retrieval.passage")


def embed_query(text: str) -> list[float]:
    """Embed a single search query (used during retrieval)."""
    return _embed([text], task="retrieval.query")[0]