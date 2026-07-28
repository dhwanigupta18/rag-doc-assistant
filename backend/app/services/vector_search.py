"""
Dense vector search against Qdrant, filtered to one document at a time.
Scoping by document_id is what lets multiple users' (or one user's multiple)
documents share the same Qdrant collection without their searches bleeding
into each other.
"""
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.core.vectorstore import get_qdrant_client
from app.services.embeddings import embed_query


def vector_search(document_id: str, query: str, top_k: int = 10) -> list[tuple[str, float]]:
    """Returns [(chunk_id, score), ...] sorted by descending similarity."""
    client = get_qdrant_client()
    query_vector = embed_query(query)

    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        query_filter=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )

    return [(point.payload["chunk_id"], point.score) for point in results.points]
