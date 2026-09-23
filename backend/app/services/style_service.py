import json
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Authorization, AuthorizationStatus, Style, StyleStatus
from app.security.sessions import require_active_session


def create_style(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    parameters: dict,
    representation_version: str,
) -> Style:
    require_active_session(db, user_id, session_id)

    style = Style(
        id=f"style_{uuid4().hex}",
        user_id=user_id,
        session_id=session_id,
        status=StyleStatus.ACTIVE.value,
        representation_version=representation_version,
        parameters_json=json.dumps(parameters, sort_keys=True),
    )
    db.add(style)
    db.commit()
    db.refresh(style)
    return style


def revoke_style(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    style_id: str,
) -> Style:
    require_active_session(db, user_id, session_id)

    style = db.get(Style, style_id)
    if style is None or style.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style not found",
        )
    if style.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Style does not belong to this session",
        )

    style.status = StyleStatus.REVOKED.value
    style.revoked_at = datetime.utcnow()

    db.execute(
        update(Authorization)
        .where(
            Authorization.style_id == style.id,
            Authorization.status == AuthorizationStatus.ACTIVE.value,
        )
        .values(status=AuthorizationStatus.REVOKED.value)
    )

    db.commit()
    db.refresh(style)
    return style
