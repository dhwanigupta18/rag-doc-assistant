"""
The core retrieval pipeline: run BM25 and vector search in parallel, merge
their ranked lists with Reciprocal Rank Fusion (RRF), then rerank the fused
shortlist with a cross-encoder for the final, precision-focused ordering.

Why RRF specifically: it combines two ranked lists using only rank position
(not raw scores), which sidesteps the problem that BM25 scores and cosine
similarity scores live on completely different scales and aren't directly
comparable. A chunk that ranks highly in *either* list gets a boosted
combined score; a chunk ranking highly in *both* gets boosted the most.
"""
from sqlalchemy.orm import Session

from app.models.models import Chunk
from app.services.bm25_index import bm25_search
from app.services.vector_search import vector_search
from app.services.reranker import rerank

RRF_K = 60  # standard smoothing constant used in most RRF implementations
FUSION_CANDIDATES = 15  # how many chunks to pull from each method before fusing
FINAL_TOP_K = 5  # how many chunks to return after reranking


def _reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]], k: int = RRF_K
) -> dict[str, float]:
    """
    ranked_lists: each is [(chunk_id, score), ...] already sorted best-first.
    Returns {chunk_id: fused_score}, higher is better.
    """
    fused_scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, (chunk_id, _score) in enumerate(ranked_list):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return fused_scores


def hybrid_search(db: Session, document_id: str, query: str) -> list[dict]:
    """
    Full pipeline: BM25 + vector search -> RRF fusion -> cross-encoder rerank.
    Returns the final top chunks as dicts ready to hand to the LLM (Phase 4)
    or to a debug endpoint, each containing chunk_id, page_number, bbox,
    text, and rerank_score.
    """
    bm25_results = bm25_search(db, document_id, query, top_k=FUSION_CANDIDATES)
    vector_results = vector_search(document_id, query, top_k=FUSION_CANDIDATES)

    fused_scores = _reciprocal_rank_fusion([bm25_results, vector_results])
    if not fused_scores:
        return []

    top_fused_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)
    top_fused_ids = top_fused_ids[:FUSION_CANDIDATES]

    chunks = db.query(Chunk).filter(Chunk.id.in_(top_fused_ids)).all()
    chunk_by_id = {c.id: c for c in chunks}

    candidates = [
        {
            "chunk_id": cid,
            "page_number": chunk_by_id[cid].page_number,
            "bbox": chunk_by_id[cid].bbox,
            "text": chunk_by_id[cid].text,
            "fusion_score": fused_scores[cid],
        }
        for cid in top_fused_ids
        if cid in chunk_by_id
    ]

    reranked = rerank(query, candidates)
    return reranked[:FINAL_TOP_K]
