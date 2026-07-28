"""
Cross-encoder reranking: unlike embeddings (which score query and chunk
independently, then compare vectors), a cross-encoder looks at the query and
chunk *together* and outputs a single relevance score. This is slower per
pair, so we only run it on the small shortlist coming out of hybrid fusion —
never on the full chunk set.
"""
from functools import lru_cache
from sentence_transformers import CrossEncoder

from app.core.config import settings


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.RERANKER_MODEL)


def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    candidates: list of dicts, each must have a "text" key.
    Returns the same list, sorted by descending reranker score, with a
    "rerank_score" key added to each dict.
    """
    if not candidates:
        return []

    model = get_reranker()
    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)

    for c, score in zip(candidates, scores):
        c["rerank_score"] = float(score)

    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
