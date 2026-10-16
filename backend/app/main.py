import hashlib
import json
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import AuditEvent, Generation, RecognitionJob
from app.schemas import (
    AuthorizationRequest,
    AuthorizationResponse,
    GenerateRequest,
    GenerationResponse,
    MessageResponse,
    ProvenanceResponse,
    RecognitionJobSummary,
    RecognitionResponse,
    SessionCreateRequest,
    SessionResponse,
    StyleCreateRequest,
    StyleResponse,
)
from app.security.authorization import consume_authorization, issue_authorization
from app.security.sessions import create_session, require_active_session
from app.services.provenance import build_provenance_digest
from app.services.handwriting_recognition import (
    MODEL_ID,
    InvalidHandwritingImage,
    RecognitionModelUnavailable,
    recognize_english_page,
)

MAX_RECOGNITION_UPLOAD_BYTES = 8 * 1024 * 1024
from app.services.style_service import create_style, revoke_style


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WritlynxAI Prototype Backend",
    version="0.2.2",
    description=(
        "Review II prototype control layer: session binding, style ownership, "
        "purpose/model/content binding, one-time authorization, revocation and provenance."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def audit(
    db: Session,
    event_type: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    style_id: str | None = None,
    generation_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            style_id=style_id,
            generation_id=generation_id,
            metadata_json=json.dumps(metadata or {}, sort_keys=True),
        )
    )


@app.get("/health", response_model=MessageResponse)
def health() -> MessageResponse:
    return MessageResponse(message="WritlynxAI backend is running")


@app.post("/recognize", response_model=RecognitionResponse)
def recognize_endpoint(
    file: UploadFile = File(...),
    user_id: str = Form(min_length=1, max_length=64),
    session_id: str = Form(min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> RecognitionResponse:
    """Run English TrOCR on a handwriting page and store transcript metadata only."""
    try:
        require_active_session(db, user_id, session_id)
        if not file.content_type or not file.content_type.lower().startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Upload a PNG, JPEG, or WEBP image.",
            )
        image_bytes = file.file.read(MAX_RECOGNITION_UPLOAD_BYTES + 1)
    finally:
        file.file.close()

    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded image is empty.")
    if len(image_bytes) > MAX_RECOGNITION_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large. The limit is 8 MB per upload.",
        )

    image_digest = hashlib.sha256(image_bytes).hexdigest()
    safe_name = Path((file.filename or "handwriting-image").replace("\\", "/")).name
    safe_name = safe_name[:255] or "handwriting-image"
    job = RecognitionJob(
        id=f"rec_{uuid4().hex}",
        user_id=user_id,
        session_id=session_id,
        original_filename=safe_name,
        image_sha256=image_digest,
        model_id=MODEL_ID,
        status="PROCESSING",
        transcript="",
        lines_recognized=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        prediction = recognize_english_page(image_bytes)
    except InvalidHandwritingImage as exc:
        job.status = "FAILED"
        job.error_code = "INVALID_IMAGE"
        audit(
            db, "RECOGNITION_FAILED", user_id=user_id, session_id=session_id,
            metadata={"job_id": job.id, "reason": job.error_code},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RecognitionModelUnavailable as exc:
        job.status = "FAILED"
        job.error_code = "MODEL_UNAVAILABLE"
        audit(
            db, "RECOGNITION_FAILED", user_id=user_id, session_id=session_id,
            metadata={"job_id": job.id, "reason": job.error_code, "model_id": MODEL_ID},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        job.status = "FAILED"
        job.error_code = "INFERENCE_ERROR"
        audit(
            db, "RECOGNITION_FAILED", user_id=user_id, session_id=session_id,
            metadata={"job_id": job.id, "reason": job.error_code},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recognition failed unexpectedly. Check backend logs and retry with a smaller image.",
        ) from exc

    job.status = "COMPLETED"
    job.transcript = prediction["transcript"]
    job.lines_recognized = int(prediction["lines_recognized"])
    audit(
        db, "RECOGNITION_COMPLETED", user_id=user_id, session_id=session_id,
        metadata={
            "job_id": job.id,
            "model_id": job.model_id,
            "image_sha256": job.image_sha256,
            "lines_recognized": job.lines_recognized,
        },
    )
    db.commit()
    db.refresh(job)

    return RecognitionResponse(
        job_id=job.id,
        status=job.status,
        original_filename=job.original_filename,
        image_sha256=job.image_sha256,
        model_id=job.model_id,
        lines_recognized=job.lines_recognized,
        transcript=job.transcript,
        created_at=job.created_at,
    )


@app.get("/recognitions", response_model=list[RecognitionJobSummary])
def list_recognitions_endpoint(
    user_id: str = Query(min_length=1, max_length=64),
    session_id: str = Query(min_length=1, max_length=64),
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[RecognitionJobSummary]:
    """Return recent recognition transcripts belonging to the active user session."""
    require_active_session(db, user_id, session_id)
    records = (
        db.query(RecognitionJob)
        .filter(RecognitionJob.user_id == user_id, RecognitionJob.session_id == session_id)
        .order_by(RecognitionJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        RecognitionJobSummary(
            job_id=record.id,
            status=record.status,
            original_filename=record.original_filename,
            image_sha256=record.image_sha256,
            model_id=record.model_id,
            lines_recognized=record.lines_recognized,
            transcript=record.transcript,
            created_at=record.created_at,
        )
        for record in records
    ]


@app.post("/sessions", response_model=SessionResponse)
def create_session_endpoint(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
):
    record = create_session(db, payload.user_id)
    audit(db, "SESSION_CREATED", user_id=record.user_id, session_id=record.id)
    db.commit()
    return SessionResponse(
        session_id=record.id,
        user_id=record.user_id,
        expires_at=record.expires_at,
    )


@app.post("/styles", response_model=StyleResponse)
def create_style_endpoint(
    payload: StyleCreateRequest,
    db: Session = Depends(get_db),
):
    style = create_style(
        db,
        user_id=payload.user_id,
        session_id=payload.session_id,
        parameters=payload.parameters,
        representation_version=payload.representation_version,
    )
    audit(
        db,
        "STYLE_CAPTURED",
        user_id=style.user_id,
        session_id=style.session_id,
        style_id=style.id,
    )
    db.commit()
    return StyleResponse(
        style_id=style.id,
        user_id=style.user_id,
        session_id=style.session_id,
        status=style.status,
        representation_version=style.representation_version,
    )


@app.post("/authorize", response_model=AuthorizationResponse)
def authorize_endpoint(
    payload: AuthorizationRequest,
    db: Session = Depends(get_db),
):
    auth = issue_authorization(
        db,
        user_id=payload.user_id,
        session_id=payload.session_id,
        style_id=payload.style_id,
        purpose=payload.purpose,
        model_version=payload.model_version,
        content=payload.content,
    )
    audit(
        db,
        "AUTHORIZATION_GRANTED",
        user_id=auth.user_id,
        session_id=auth.session_id,
        style_id=auth.style_id,
        metadata={
            "authorization_id": auth.id,
            "purpose": auth.purpose,
            "model_version": auth.model_version,
        },
    )
    db.commit()
    return AuthorizationResponse(
        authorization_id=auth.id,
        nonce=auth.nonce,
        expires_at=auth.expires_at,
        status=auth.status,
        content_fingerprint=auth.content_fingerprint,
    )


@app.post("/generate", response_model=GenerationResponse)
def generate_endpoint(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
):
    auth = consume_authorization(
        db,
        user_id=payload.user_id,
        session_id=payload.session_id,
        authorization_id=payload.authorization_id,
        content=payload.content,
        purpose=payload.purpose,
        model_version=payload.model_version,
    )

    generation_id = f"gen_{uuid4().hex}"
    provenance_payload = {
        "generation_id": generation_id,
        "user_id": auth.user_id,
        "session_id": auth.session_id,
        "style_id": auth.style_id,
        "authorization_id": auth.id,
        "purpose": auth.purpose,
        "model_version": auth.model_version,
        "content_fingerprint": auth.content_fingerprint,
    }
    digest = build_provenance_digest(provenance_payload)

    generation = Generation(
        id=generation_id,
        user_id=auth.user_id,
        session_id=auth.session_id,
        style_id=auth.style_id,
        authorization_id=auth.id,
        purpose=auth.purpose,
        model_version=auth.model_version,
        content_fingerprint=auth.content_fingerprint,
        provenance_digest=digest,
        status="PROTOTYPE_AUTHORIZED",
    )
    db.add(generation)

    audit(
        db,
        "GENERATION_COMPLETED",
        user_id=auth.user_id,
        session_id=auth.session_id,
        style_id=auth.style_id,
        generation_id=generation_id,
        metadata={
            "authorization_id": auth.id,
            "provenance_digest": digest,
        },
    )
    db.commit()

    return GenerationResponse(
        generation_id=generation_id,
        status=generation.status,
        provenance_digest=digest,
    )


@app.get("/provenance/{generation_id}", response_model=ProvenanceResponse)
def provenance_endpoint(
    generation_id: str,
    user_id: str = Query(min_length=1, max_length=64),
    session_id: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    require_active_session(db, user_id, session_id)

    generation = db.get(Generation, generation_id)
    if generation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )
    if generation.user_id != user_id or generation.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Generation context mismatch",
        )

    return ProvenanceResponse(
        generation_id=generation.id,
        user_id=generation.user_id,
        session_id=generation.session_id,
        style_id=generation.style_id,
        authorization_id=generation.authorization_id,
        purpose=generation.purpose,
        model_version=generation.model_version,
        content_fingerprint=generation.content_fingerprint,
        provenance_digest=generation.provenance_digest,
        status=generation.status,
        created_at=generation.created_at,
    )


@app.post("/revoke/{style_id}", response_model=StyleResponse)
def revoke_style_endpoint(
    style_id: str,
    user_id: str = Query(min_length=1, max_length=64),
    session_id: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    style = revoke_style(
        db,
        user_id=user_id,
        session_id=session_id,
        style_id=style_id,
    )
    audit(
        db,
        "STYLE_REVOKED",
        user_id=style.user_id,
        session_id=style.session_id,
        style_id=style.id,
    )
    db.commit()

    return StyleResponse(
        style_id=style.id,
        user_id=style.user_id,
        session_id=style.session_id,
        status=style.status,
        representation_version=style.representation_version,
    )
