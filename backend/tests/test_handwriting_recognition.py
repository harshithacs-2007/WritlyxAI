from contextlib import nullcontext
from io import BytesIO
from types import SimpleNamespace

from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import RecognitionJob
from app.services import handwriting_recognition as recognition


def test_prepare_lines_splits_a_clear_two_line_image():
    image = Image.new("RGB", (640, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.line((35, 42, 260, 44), fill="black", width=4)
    draw.line((35, 112, 360, 114), fill="black", width=4)
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    lines = recognition._prepare_lines(buffer.getvalue())

    assert len(lines) == 2
    assert lines[0].width > 100
    assert lines[1].width > 100


def test_recognize_page_uses_model_output_without_downloading_weights(monkeypatch):
    class FakeTensor:
        def to(self, _device):
            return self

    class FakeProcessor:
        def __call__(self, *, images, return_tensors):
            assert return_tensors == "pt"
            return SimpleNamespace(pixel_values=FakeTensor())

        def batch_decode(self, generated_ids, skip_special_tokens):
            assert skip_special_tokens is True
            return [f"recognized line {generated_ids[0]}"]

    class FakeModel:
        def __init__(self):
            self.calls = 0

        def generate(self, _pixels, **_kwargs):
            self.calls += 1
            return [self.calls]

    fake_model = FakeModel()
    fake_torch = SimpleNamespace(inference_mode=nullcontext)
    fake_processor = FakeProcessor()
    monkeypatch.setattr(recognition, "_prepare_lines", lambda _data: [object(), object()])
    monkeypatch.setattr(
        recognition,
        "_load_model",
        lambda: (fake_processor, fake_model, fake_torch),
    )
    monkeypatch.setattr(recognition, "_device", "cpu")

    result = recognition.recognize_english_page(b"test image bytes")

    assert result["transcript"] == "recognized line 1\nrecognized line 2"
    assert result["lines_recognized"] == 2
    assert result["model_id"] == "microsoft/trocr-base-handwritten"


def test_recognize_api_persists_transcript_and_hash_in_sqlite(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session_factory = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        main,
        "recognize_english_page",
        lambda _data: {
            "transcript": "The quick brown fox.",
            "lines_recognized": 1,
            "model_id": "microsoft/trocr-base-handwritten",
        },
    )
    page = Image.new("RGB", (120, 60), "white")
    page_buffer = BytesIO()
    page.save(page_buffer, format="PNG")

    try:
        with TestClient(main.app) as client:
            session_response = client.post("/sessions", json={"user_id": "demo-user"})
            assert session_response.status_code == 200
            session_id = session_response.json()["session_id"]

            response = client.post(
                "/recognize",
                data={"user_id": "demo-user", "session_id": session_id},
                files={"file": ("sample.png", page_buffer.getvalue(), "image/png")},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "COMPLETED"
            assert payload["transcript"] == "The quick brown fox."
            assert len(payload["image_sha256"]) == 64
            assert "job_id" in payload

            history = client.get(
                "/recognitions",
                params={"user_id": "demo-user", "session_id": session_id},
            )
            assert history.status_code == 200
            assert history.json()[0]["job_id"] == payload["job_id"]
            assert history.json()[0]["transcript"] == "The quick brown fox."

        with test_session_factory() as db:
            saved = db.get(RecognitionJob, payload["job_id"])
            assert saved is not None
            assert saved.status == "COMPLETED"
            assert saved.transcript == "The quick brown fox."
            assert len(saved.image_sha256) == 64
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        test_engine.dispose()
