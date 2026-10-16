import hashlib
import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import AuditEvent, Authorization, Generation, GenerationArtifact, RecognitionJob, Style, StyleSample
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
    StyleSampleSummary,
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
from app.services.handwriting_generation import (
    HandwritingGenerationUnavailable,
    InvalidStyleReferences,
    MAX_WORDS_PER_REQUEST,
    generate_handwriting_page,
)

from app.services.style_service import create_style, revoke_style

MAX_RECOGNITION_UPLOAD_BYTES = 8 * 1024 * 1024


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
    allow_methods=["GET", "POST", "DELETE"],
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
        if (file.content_type or "").lower() not in {"image/png", "image/jpeg", "image/webp"}:
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


def _validate_reference_image(
    image_bytes: bytes, content_type: str, filename: str
) -> tuple[str, str]:
    allowed = {
        "image/png": "PNG",
        "image/jpeg": "JPEG",
        "image/webp": "WEBP",
    }
    if content_type.lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Use a PNG, JPEG, or WEBP handwriting sample.",
        )
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image_format = (image.format or "").upper()
            if image_format != allowed[content_type.lower()]:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="The file contents do not match the declared image type.",
                )
            if image.width < 32 or image.height < 16:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The handwriting image is too small.",
                )
            if image.width * image.height > 12_000_000:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Image is too large. The limit is 12 megapixels.",
                )
            image.verify()
    except HTTPException:
        raise
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file is not a readable PNG, JPEG, or WEBP image.",
        ) from exc

    safe_name = Path((filename or "handwriting-sample").replace("\\", "/")).name
    return safe_name[:255] or "handwriting-sample", content_type.lower()


@app.post("/styles/{style_id}/samples", response_model=list[StyleSampleSummary])
def add_style_samples_endpoint(
    style_id: str,
    files: list[UploadFile] = File(...),
    user_id: str = Form(min_length=1, max_length=64),
    session_id: str = Form(min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> list[StyleSampleSummary]:
    """Persist up to five reference images for one active, session-owned style."""
    require_active_session(db, user_id, session_id)
    style = db.get(Style, style_id)
    if style is None or style.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found.")
    if style.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Style does not belong to this session.")
    if style.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Style is not active.")
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose at least one handwriting sample.")
    existing_count = db.query(StyleSample).filter(StyleSample.style_id == style_id).count()
    if existing_count + len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"This prototype stores up to five reference images per style. {existing_count} are already saved.",
        )

    prepared: list[tuple[str, str, str, bytes]] = []
    try:
        for upload in files:
            image_bytes = upload.file.read(MAX_RECOGNITION_UPLOAD_BYTES + 1)
            if not image_bytes:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A selected image is empty.")
            if len(image_bytes) > MAX_RECOGNITION_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Each reference image must be 8 MB or smaller.",
                )
            safe_name, content_type = _validate_reference_image(
                image_bytes, upload.content_type or "", upload.filename or "handwriting-sample"
            )
            prepared.append((safe_name, content_type, hashlib.sha256(image_bytes).hexdigest(), image_bytes))
    finally:
        for upload in files:
            upload.file.close()

    saved: list[StyleSample] = []
    for original_filename, content_type, image_digest, image_bytes in prepared:
        sample = StyleSample(
            id=f"sample_{uuid4().hex}",
            style_id=style_id,
            user_id=user_id,
            session_id=session_id,
            original_filename=original_filename,
            content_type=content_type,
            image_sha256=image_digest,
            image_bytes=image_bytes,
        )
        db.add(sample)
        saved.append(sample)

    audit(
        db, "STYLE_SAMPLES_SAVED", user_id=user_id, session_id=session_id,
        style_id=style_id,
        metadata={"count": len(saved), "image_sha256": [sample.image_sha256 for sample in saved]},
    )
    db.commit()
    for sample in saved:
        db.refresh(sample)

    return [
        StyleSampleSummary(
            sample_id=sample.id,
            style_id=sample.style_id,
            original_filename=sample.original_filename,
            content_type=sample.content_type,
            image_sha256=sample.image_sha256,
            size_bytes=len(sample.image_bytes),
            created_at=sample.created_at,
        )
        for sample in saved
    ]


@app.get("/styles/{style_id}/samples", response_model=list[StyleSampleSummary])
def list_style_samples_endpoint(
    style_id: str,
    user_id: str = Query(min_length=1, max_length=64),
    session_id: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> list[StyleSampleSummary]:
    require_active_session(db, user_id, session_id)
    style = db.get(Style, style_id)
    if style is None or style.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found.")
    if style.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Style does not belong to this session.")
    records = (
        db.query(StyleSample)
        .filter(
            StyleSample.style_id == style_id,
            StyleSample.user_id == user_id,
            StyleSample.session_id == session_id,
        )
        .order_by(StyleSample.created_at.asc())
        .all()
    )
    return [
        StyleSampleSummary(
            sample_id=record.id,
            style_id=record.style_id,
            original_filename=record.original_filename,
            content_type=record.content_type,
            image_sha256=record.image_sha256,
            size_bytes=len(record.image_bytes),
            created_at=record.created_at,
        )
        for record in records
    ]


@app.delete("/styles/{style_id}/samples/{sample_id}", response_model=MessageResponse)
def delete_style_sample_endpoint(
    style_id: str,
    sample_id: str,
    user_id: str = Query(min_length=1, max_length=64),
    session_id: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> MessageResponse:
    require_active_session(db, user_id, session_id)
    style = db.get(Style, style_id)
    if style is None or style.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found.")
    if style.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Style does not belong to this session.")
    sample = db.get(StyleSample, sample_id)
    if sample is None or sample.style_id != style_id or sample.user_id != user_id or sample.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style sample not found.")
    digest = sample.image_sha256
    db.delete(sample)
    audit(
        db, "STYLE_SAMPLE_DELETED", user_id=user_id, session_id=session_id, style_id=style_id,
        metadata={"sample_id": sample_id, "image_sha256": digest},
    )
    db.commit()
    return MessageResponse(message="Handwriting sample deleted.")


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
) -> GenerationResponse:
    if len(payload.content.split()) > MAX_WORDS_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"This prototype can generate up to {MAX_WORDS_PER_REQUEST} words per request.",
        )

    auth = consume_authorization(
        db,
        user_id=payload.user_id,
        session_id=payload.session_id,
        authorization_id=payload.authorization_id,
        content=payload.content,
        purpose=payload.purpose,
        model_version=payload.model_version,
    )
    reference_rows = (
        db.query(StyleSample)
        .filter(
            StyleSample.style_id == auth.style_id,
            StyleSample.user_id == auth.user_id,
            StyleSample.session_id == auth.session_id,
        )
        .order_by(StyleSample.created_at.asc())
        .all()
    )
    if not reference_rows:
        audit(
            db, "GENERATION_FAILED", user_id=auth.user_id, session_id=auth.session_id,
            style_id=auth.style_id,
            metadata={"reason": "NO_STYLE_REFERENCES", "authorization_id": auth.id},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No saved handwriting references are attached to this style. Upload one or more reference images and try again.",
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
        status="PROCESSING",
    )
    db.add(generation)
    audit(
        db, "GENERATION_STARTED", user_id=auth.user_id, session_id=auth.session_id,
        style_id=auth.style_id, generation_id=generation_id,
        metadata={"authorization_id": auth.id, "model_version": auth.model_version},
    )
    db.commit()

    try:
        result = generate_handwriting_page(
            payload.content,
            [row.image_bytes for row in reference_rows[:5]],
        )
    except InvalidStyleReferences as exc:
        generation.status = "FAILED"
        audit(
            db, "GENERATION_FAILED", user_id=auth.user_id, session_id=auth.session_id,
            style_id=auth.style_id, generation_id=generation_id,
            metadata={"reason": "INVALID_STYLE_REFERENCES"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except HandwritingGenerationUnavailable as exc:
        generation.status = "FAILED"
        audit(
            db, "GENERATION_FAILED", user_id=auth.user_id, session_id=auth.session_id,
            style_id=auth.style_id, generation_id=generation_id,
            metadata={"reason": "MODEL_UNAVAILABLE"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        generation.status = "FAILED"
        audit(
            db, "GENERATION_FAILED", user_id=auth.user_id, session_id=auth.session_id,
            style_id=auth.style_id, generation_id=generation_id,
            metadata={"reason": "INVALID_GENERATION_REQUEST"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        generation.status = "FAILED"
        audit(
            db, "GENERATION_FAILED", user_id=auth.user_id, session_id=auth.session_id,
            style_id=auth.style_id, generation_id=generation_id,
            metadata={"reason": "GENERATION_ERROR"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Handwriting generation failed. Check backend logs and retry with a shorter text and clearer reference images.",
        ) from exc

    artifact = GenerationArtifact(
        generation_id=generation_id,
        model_id=result["model_id"],
        original_text=payload.content,
        image_bytes=result["image_bytes"],
        words_generated=int(result["words_generated"]),
        reference_words_used=int(result["reference_words_used"]),
    )
    db.add(artifact)
    generation.status = "COMPLETED"
    audit(
        db, "GENERATION_COMPLETED", user_id=auth.user_id, session_id=auth.session_id,
        style_id=auth.style_id, generation_id=generation_id,
        metadata={
            "authorization_id": auth.id,
            "provenance_digest": digest,
            "model_id": result["model_id"],
            "words_generated": result["words_generated"],
            "reference_words_used": result["reference_words_used"],
        },
    )
    db.commit()
    db.refresh(generation)

    return GenerationResponse(
        generation_id=generation_id,
        status=generation.status,
        provenance_digest=digest,
        model_id=result["model_id"],
        image_url=f"/generations/{generation_id}/image",
        words_generated=int(result["words_generated"]),
        reference_words_used=int(result["reference_words_used"]),
    )


@app.get("/generations/{generation_id}/image")
def generation_image_endpoint(
    generation_id: str,
    user_id: str = Query(min_length=1, max_length=64),
    session_id: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> Response:
    require_active_session(db, user_id, session_id)
    generation = db.get(Generation, generation_id)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found.")
    if generation.user_id != user_id or generation.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Generation context mismatch.")
    artifact = db.get(GenerationArtifact, generation_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated image is not available.")
    return Response(
        content=artifact.image_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="writlynxai-{generation_id}.png"'},
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
