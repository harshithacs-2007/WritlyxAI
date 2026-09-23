from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SessionRecord, User


def create_session(db: Session, user_id: str) -> SessionRecord:
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        db.add(user)
        db.flush()

    now = datetime.utcnow()
    record = SessionRecord(
        id=f"sess_{uuid4().hex}",
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
        revoked=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def require_active_session(db: Session, user_id: str, session_id: str) -> SessionRecord:
    session = db.get(SessionRecord, session_id)
    now = datetime.utcnow()

    if session is None or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to this user",
        )
    if session.revoked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session has been revoked",
        )
    if session.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session has expired",
        )
    return session
