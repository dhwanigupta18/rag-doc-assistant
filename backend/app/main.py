from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import Base, engine
from app.models import models  # noqa: F401 (ensures models are registered with Base)
from app.routers import health, documents, chat

app = FastAPI(
    title="RAG Document Assistant API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup():
    # For Phase 1, create tables directly. From Phase 2 onward, switch to Alembic migrations.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "RAG Document Assistant API is running"}
