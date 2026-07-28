from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ---- Auth ----

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Documents ----

class DocumentOut(BaseModel):
    id: str
    filename: str
    page_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Chat ----

class ChatRequest(BaseModel):
    question: str


class Citation(BaseModel):
    chunk_id: str
    page_number: int
    bbox: dict


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[list[dict]] = None
    created_at: datetime

    class Config:
        from_attributes = True
