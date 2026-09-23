import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Authorization, AuthorizationStatus, Style, StyleStatus
from app.security.fingerprints import content_fingerprint
from app.security.sessions import require_active_session


def issue_authorization(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    style_id: str,
    purpose: str,
    model_version: str,
    content: str,
) -> Authorization:
    require_active_session(db, user_id, session_id)

    style = db.get(Style, style_id)
    if style is None or style.user_id != user_id or style.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Style is not owned by this user/session",
        )
    if style.status != StyleStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Style is not active",
        )

    now = datetime.utcnow()
    auth = Authorization(
        id=f"auth_{uuid4().hex}",
        user_id=user_id,
        session_id=session_id,
        style_id=style_id,
        purpose=purpose,
        model_version=model_version,
        content_fingerprint=content_fingerprint(content),
        nonce=secrets.token_urlsafe(settings.nonce_bytes),
        status=AuthorizationStatus.ACTIVE.value,
        created_at=now,
        expires_at=now + timedelta(seconds=settings.authorization_ttl_seconds),
    )
    db.add(auth)
    db.commit()
    db.refresh(auth)
    return auth


def consume_authorization(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    authorization_id: str,
    content: str,
    purpose: str,
    model_version: str,
) -> Authorization:
    require_active_session(db, user_id, session_id)

    auth = db.execute(
        select(Authorization).where(Authorization.id == authorization_id)
    ).scalar_one_or_none()

    now = datetime.utcnow()
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization not found",
        )
    if auth.user_id != user_id or auth.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization context mismatch",
        )
    if auth.status != AuthorizationStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization is not active",
        )
    if auth.expires_at <= now:
        auth.status = AuthorizationStatus.EXPIRED.value
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization has expired",
        )

    style = db.get(Style, auth.style_id)
    if style is None or style.user_id != user_id or style.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Style context mismatch",
        )
    if style.status != StyleStatus.ACTIVE.value:
        auth.status = AuthorizationStatus.REVOKED.value
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Style is not active",
        )

    if not secrets.compare_digest(auth.content_fingerprint, content_fingerprint(content)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Content binding mismatch",
        )
    if not secrets.compare_digest(auth.purpose, purpose):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Purpose binding mismatch",
        )
    if not secrets.compare_digest(auth.model_version, model_version):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Model-version binding mismatch",
        )

    # Atomic state transition: only one concurrent request can move ACTIVE -> CONSUMED.
    result = db.execute(
        update(Authorization)
        .where(
            Authorization.id == authorization_id,
            Authorization.status == AuthorizationStatus.ACTIVE.value,
        )
        .values(
            status=AuthorizationStatus.CONSUMED.value,
            consumed_at=now,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization was already consumed or revoked",
        )

    db.commit()
    db.refresh(auth)
    return auth
