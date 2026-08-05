import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.models import Document, User
from app.schemas.schemas import DocumentOut
from app.services.ingestion import ingest_document
from app.services.retrieval import hybrid_search
from app.core.storage import upload_pdf_bytes, get_presigned_url

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSION = ".pdf"


@router.get("/", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

def get_document_file(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Serves the raw PDF bytes so the frontend's PDF viewer (react-pdf) can
    render it directly. Scoped to the owner, same as every other document
    endpoint — no public/unauthenticated access to uploaded files.
    """
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    presigned_url = get_presigned_url(document.file_path)
    return RedirectResponse(url=presigned_url)



@router.post("/upload", response_model=DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(ALLOWED_EXTENSION):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Prefix with a UUID so two users uploading "report.pdf" never collide.
    object_key = f"uploads/{uuid.uuid4()}_{file.filename}"
    file_bytes = file.file.read()
    upload_pdf_bytes(object_key, file_bytes)

    document = Document(
        owner_id=current_user.id,
        filename=file.filename,
        file_path=object_key,  # now a Supabase Storage object key, not a local path
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Synchronous for now — fine for development. A later phase can move this
    # to a background task/queue so the upload response returns instantly
    # while ingestion continues server-side.
    ingest_document(db, document)
    db.refresh(document)

    return document


@router.get("/{document_id}/search")
def debug_search(
    document_id: str,
    q: str,
    preview: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    DEBUG ENDPOINT for Phase 3 — lets you inspect hybrid retrieval results
    directly, without an LLM in the loop. Useful for judging whether the
    right chunks are being retrieved before Phase 4 adds generation on top.
    Will likely be removed or auth-locked before final submission.

    By default, chunk text is truncated to a short preview for readable
    terminal output. Pass ?preview=false to get the full chunk text (this is
    exactly what Phase 4 will send to the LLM as context).
    """
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(status_code=400, detail=f"Document status is '{document.status}', not 'ready'")

    results = hybrid_search(db, document_id, q)

    if preview:
        for r in results:
            full_text = r["text"]
            r["word_count"] = len(full_text.split())
            r["text"] = full_text[:150] + ("..." if len(full_text) > 150 else "")

    return {"query": q, "results": results}


# Phase 4 will add /chat/{document_id} which uses hybrid_search() + an LLM
# to produce a grounded answer with citations, instead of raw chunks.
