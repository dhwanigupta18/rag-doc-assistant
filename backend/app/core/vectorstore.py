"""
Qdrant is our vector database. Each point stored here represents one chunk,
with the embedding vector plus payload metadata (document_id, page_number,
bbox, text) needed to resolve a search hit back to a highlightable location
in the original PDF.
"""
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings

# bge-small-en-v1.5 outputs 384-dimensional vectors.
# If you change EMBEDDING_MODEL later, update this to match its output dimension.
EMBEDDING_DIM = 1024  # jina-embeddings-v3's native output size

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
    return _client


def ensure_collection_exists() -> None:
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        # Qdrant Cloud (unlike local Docker Qdrant) requires an explicit
        # index on any payload field used in a filter — without this,
        # filtering by document_id in vector_search() fails with a 400.
        client.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION,
            field_name="document_id",
            field_schema="keyword",
        )
