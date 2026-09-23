from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    expires_at: datetime


class StyleCreateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str = Field(min_length=1, max_length=64)
    parameters: dict[str, float | int | str] = Field(default_factory=dict)
    representation_version: str = Field(default="prototype-v1", max_length=32)


class StyleResponse(BaseModel):
    style_id: str
    user_id: str
    session_id: str
    status: str
    representation_version: str


class AuthorizationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str = Field(min_length=1, max_length=64)
    style_id: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=1, max_length=64)
    model_version: str = Field(default="prototype-renderer-v1", max_length=64)
    content: str = Field(min_length=1, max_length=5000)


class AuthorizationResponse(BaseModel):
    authorization_id: str
    nonce: str
    expires_at: datetime
    status: str
    content_fingerprint: str


class GenerateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str = Field(min_length=1, max_length=64)
    authorization_id: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=5000)
    purpose: str = Field(min_length=1, max_length=64)
    model_version: str = Field(min_length=1, max_length=64)


class GenerationResponse(BaseModel):
    generation_id: str
    status: str
    provenance_digest: str


class ProvenanceResponse(BaseModel):
    generation_id: str
    user_id: str
    session_id: str
    style_id: str
    authorization_id: str
    purpose: str
    model_version: str
    content_fingerprint: str
    provenance_digest: str
    status: str
    created_at: datetime


class MessageResponse(BaseModel):
    message: str
