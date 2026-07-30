"""
Reranks candidates via Jina AI's hosted Reranker API instead of running a
cross-encoder model locally, for the same memory reasons as embeddings.py.
"""
import requests

from app.core.config import settings

JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"


def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    candidates: list of dicts, each must have a "text" key.
    Returns the same list, sorted by descending reranker score, with a
    "rerank_score" key added to each dict.
    """
    if not candidates:
        return []

    documents = [c["text"] for c in candidates]

    response = requests.post(
        JINA_RERANK_URL,
        headers={
            "Authorization": f"Bearer {settings.JINA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.RERANKER_MODEL,
            "query": query,
            "documents": documents,
            "return_documents": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()["results"]

    for result in results:
        candidates[result["index"]]["rerank_score"] = result["relevance_score"]

    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)