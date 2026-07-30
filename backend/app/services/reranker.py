"""
Cross-encoder reranking via fastembed (ONNX Runtime) instead of
sentence-transformers/PyTorch, for the same memory reasons as embeddings.py.
Only runs on the small shortlist coming out of hybrid fusion, never the full
chunk set.
"""
from functools import lru_cache
from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.core.config import settings


@lru_cache(maxsize=1)
def get_reranker() -> TextCrossEncoder:
    return TextCrossEncoder(model_name=settings.RERANKER_MODEL, threads=1)


def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    candidates: list of dicts, each must have a "text" key.
    Returns the same list, sorted by descending reranker score, with a
    "rerank_score" key added to each dict.
    """
    if not candidates:
        return []

    model = get_reranker()
    documents = [c["text"] for c in candidates]
    scores = list(model.rerank(query, documents))

    for c, score in zip(candidates, scores):
        c["rerank_score"] = float(score)

    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)