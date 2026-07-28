"""
TEMPORARY: real JWT-based auth is deferred to a dedicated phase so we can
focus on the ingestion/retrieval pipeline first. Until then, every request
is treated as coming from a single auto-created "dev user" so that
Document.owner_id has something valid to reference.

Replace `get_current_user` with real token verification once auth is built —
every router that depends on this function will automatically pick up real
auth then, with no other changes needed.
"""
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import User
from fastapi import Depends

DEV_USER_EMAIL = "dev@local.test"


def get_or_create_dev_user(db: Session) -> User:
    user = db.query(User).filter(User.email == DEV_USER_EMAIL).first()
    if user is None:
        user = User(email=DEV_USER_EMAIL, hashed_password="not-a-real-password")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(db: Session = Depends(get_db)) -> User:
    # Swap this out for real JWT decoding + DB lookup when auth is built.
    return get_or_create_dev_user(db)
