"""
Supabase Storage (S3-compatible) client for storing uploaded PDFs.

Why this exists: hosting platforms like Render use ephemeral containers -
anything written to local disk (e.g. the old UPLOAD_DIR approach) is wiped
on every restart or redeploy. Postgres and Qdrant already solved this by
being separate managed services; uploaded files need the same treatment, so
they're stored in Supabase Storage instead of the container's filesystem.
"""
from functools import lru_cache
import boto3

from app.core.config import settings


@lru_cache(maxsize=1)
def get_storage_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.SUPABASE_PROJECT_REF}.supabase.co/storage/v1/s3",
        aws_access_key_id=settings.SUPABASE_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SUPABASE_S3_SECRET_ACCESS_KEY,
        region_name="us-east-1",
    )


def upload_pdf_bytes(key: str, file_bytes: bytes) -> None:
    client = get_storage_client()
    client.put_object(
        Bucket=settings.SUPABASE_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType="application/pdf",
    )


def download_pdf_bytes(key: str) -> bytes:
    client = get_storage_client()
    response = client.get_object(Bucket=settings.SUPABASE_BUCKET_NAME, Key=key)
    return response["Body"].read()


def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """
    Returns a temporary, directly-accessible URL for the file in storage.
    Used so the frontend's PDF viewer can fetch the file straight from
    Supabase (which handles HTTP range requests well - important for
    react-pdf) instead of proxying the full file through our own backend.
    """
    client = get_storage_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.SUPABASE_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )