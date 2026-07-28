from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.models import Document, ChatMessage, User
from app.schemas.schemas import ChatRequest, ChatResponse, ChatMessageOut
from app.services.retrieval import hybrid_search
from app.services.generation import generate_answer

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_owned_document(db: Session, document_id: str, current_user: User) -> Document:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Document status is '{document.status}', not 'ready'",
        )
    return document


@router.post("/{document_id}", response_model=ChatResponse)
def chat_with_document(
    document_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = _get_owned_document(db, document_id, current_user)

    # 1. Retrieve relevant chunks (Phase 3 pipeline)
    chunks = hybrid_search(db, document_id, request.question)

    # 2. Generate a grounded, cited answer (Phase 4)
    result = generate_answer(request.question, chunks)

    # 3. Persist both sides of the exchange
    user_message = ChatMessage(
        document_id=document.id,
        role="user",
        content=request.question,
    )
    assistant_message = ChatMessage(
        document_id=document.id,
        role="assistant",
        content=result["answer"],
        citations=result["citations"],
    )
    db.add_all([user_message, assistant_message])
    db.commit()

    return ChatResponse(answer=result["answer"], citations=result["citations"])


@router.get("/{document_id}/history", response_model=list[ChatMessageOut])
def get_chat_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = _get_owned_document(db, document_id, current_user)

    return (
        db.query(ChatMessage)
        .filter(ChatMessage.document_id == document.id)
        .order_by(ChatMessage.created_at)
        .all()
    )