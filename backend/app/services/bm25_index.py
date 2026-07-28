"""
BM25 keyword search, cached per document.

Design choice (the "middle ground"): rank_bm25 has no native incremental
update — you build an index from a full list of documents, or you don't have
one. So instead of true incremental indexing (which would need a different
tool like Elasticsearch), we cache one BM25 index per document_id in memory
and only rebuild it when that document's chunks change (i.e. right after
ingestion). Repeated queries against the same document reuse the cached
index instead of rebuilding it every time.

Known limitations (worth knowing, not fixing here):
- Cache lives in process memory. Restarting the server clears it (it just
  rebuilds lazily on next query, so this is a performance hit, not a
  correctness bug).
- If you ever run multiple backend worker processes, each process has its
  own cache — a query hitting worker A won't benefit from a rebuild that
  happened in worker B. Fine for a single-instance dev/demo setup; a real
  production deployment would move this to a shared store (e.g. Redis) or
  swap BM25 out for a proper search engine entirely.
"""
from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models.models import Chunk


@dataclass
class BM25Entry:
    bm25: BM25Okapi
    chunk_ids: list[str]
    texts: list[str]


_cache: dict[str, BM25Entry] = {}


def _tokenize(text: str) -> list[str]:
    # Simple whitespace + lowercase tokenization. Good enough for BM25 —
    # no need for a heavyweight tokenizer here.
    return text.lower().split()


def invalidate_bm25_cache(document_id: str) -> None:
    """Call this after a document's chunks are created/changed so the next
    query rebuilds a fresh index instead of using stale data."""
    _cache.pop(document_id, None)


def _build_index(db: Session, document_id: str) -> BM25Entry:
    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .all()
    )
    chunk_ids = [c.id for c in chunks]
    texts = [c.text for c in chunks]
    tokenized = [_tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)

    entry = BM25Entry(bm25=bm25, chunk_ids=chunk_ids, texts=texts)
    _cache[document_id] = entry
    return entry


def get_bm25_index(db: Session, document_id: str) -> BM25Entry:
    """Returns the cached index for this document, building it if this is
    the first query since the last cache invalidation."""
    if document_id in _cache:
        return _cache[document_id]
    return _build_index(db, document_id)


def bm25_search(db: Session, document_id: str, query: str, top_k: int = 10) -> list[tuple[str, float]]:
    """Returns [(chunk_id, score), ...] sorted by descending BM25 score."""
    entry = get_bm25_index(db, document_id)
    if not entry.chunk_ids:
        return []

    tokenized_query = _tokenize(query)
    scores = entry.bm25.get_scores(tokenized_query)

    ranked = sorted(zip(entry.chunk_ids, scores), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]
