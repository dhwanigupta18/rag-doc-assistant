"""
Orchestrates the full ingestion pipeline for a single uploaded document:

  1. Parse PDF into text blocks with bounding boxes (pdf_parser.py)
  2. Merge blocks into retrieval-sized chunks (chunker.py)
  3. Generate embeddings for each chunk (embeddings.py)
  4. Store chunk metadata in Postgres, vectors in Qdrant (vectorstore.py)

Runs synchronously for now (fine for small-to-medium PDFs during development).
In a later phase, consider moving this to a background task queue (e.g.
Celery or FastAPI BackgroundTasks) so uploads don't block the HTTP response.
"""
import uuid

from qdrant_client.http.models import PointStruct
from sqlalchemy.orm import Session

from app.core.vectorstore import get_qdrant_client, ensure_collection_exists
from app.core.config import settings
from app.models.models import Document, Chunk
from app.services.pdf_parser import extract_blocks
from app.services.chunker import build_chunks
from app.services.embeddings import embed_texts
from app.services.bm25_index import invalidate_bm25_cache


def ingest_document(db: Session, document: Document) -> None:
    """
    Runs the full pipeline for a Document row that already exists in Postgres
    (file already saved to disk, status == "processing"). Updates the
    document's status to "ready" or "failed" when done.
    """
    try:
        blocks, page_count = extract_blocks(document.file_path)
        chunks = build_chunks(blocks)

        if not chunks:
            document.status = "failed"
            document.page_count = page_count
            db.commit()
            return

        # 1. Embed all chunk texts in one batch call (much faster than per-chunk)
        texts = [c.text for c in chunks]
        vectors = embed_texts(texts)

        # 2. Persist chunk metadata in Postgres, generating IDs up front so
        #    the same ID can be used as the Qdrant point ID (keeps the two
        #    stores linked by a single shared identifier).
        chunk_rows = []
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            chunk_rows.append(
                Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    bbox=chunk.bbox,
                    chunk_index=chunk.chunk_index,
                )
            )
        db.add_all(chunk_rows)

        # 3. Push vectors + payload into Qdrant
        ensure_collection_exists()
        client = get_qdrant_client()
        points = [
            PointStruct(
                id=chunk_rows[i].id,
                vector=vectors[i],
                payload={
                    "document_id": document.id,
                    "chunk_id": chunk_rows[i].id,
                    "page_number": chunk_rows[i].page_number,
                    "text": chunk_rows[i].text,
                    "bbox": chunk_rows[i].bbox,
                },
            )
            for i in range(len(chunk_rows))
        ]
        client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)

        document.status = "ready"
        document.page_count = page_count
        db.commit()

        # New chunks exist now — drop any stale cached BM25 index for this
        # document so the next search rebuilds against the current chunks.
        invalidate_bm25_cache(document.id)

    except Exception:
        document.status = "failed"
        db.commit()
        raise
