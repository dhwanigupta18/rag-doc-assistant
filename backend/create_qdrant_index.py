"""
One-off script to add the payload index Qdrant Cloud requires for filtering
by document_id. Only needs to run once per collection - safe to re-run,
Qdrant just no-ops if the index already exists.

Usage:
    python create_qdrant_index.py
"""
from app.core.vectorstore import get_qdrant_client
from app.core.config import settings

client = get_qdrant_client()

client.create_payload_index(
    collection_name=settings.QDRANT_COLLECTION,
    field_name="document_id",
    field_schema="keyword",
)

print(f"Index created on '{settings.QDRANT_COLLECTION}' for field 'document_id'")