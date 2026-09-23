from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def setup_user(user_id: str):
    session = client.post("/sessions", json={"user_id": user_id}).json()
    style = client.post(
        "/styles",
        json={
            "user_id": user_id,
            "session_id": session["session_id"],
            "parameters": {
                "slant": 18,
                "spacing": 0.62,
                "stroke": 0.71,
            },
        },
    ).json()
    return session, style


def authorize(user_id: str, session_id: str, style_id: str, content: str):
    return client.post(
        "/authorize",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "style_id": style_id,
            "purpose": "prototype-generation",
            "model_version": "prototype-renderer-v1",
            "content": content,
        },
    )


def generate(
    user_id: str,
    session_id: str,
    authorization_id: str,
    content: str,
    *,
    purpose: str = "prototype-generation",
    model_version: str = "prototype-renderer-v1",
):
    return client.post(
        "/generate",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "authorization_id": authorization_id,
            "content": content,
            "purpose": purpose,
            "model_version": model_version,
        },
    )


def test_valid_authorization_and_one_time_generation():
    session, style = setup_user("U001")
    content = "Hello WritlynxAI"
    auth_response = authorize(
        "U001",
        session["session_id"],
        style["style_id"],
        content,
    )
    assert auth_response.status_code == 200
    auth = auth_response.json()

    response = generate(
        "U001",
        session["session_id"],
        auth["authorization_id"],
        content,
    )
    assert response.status_code == 200

    replay = generate(
        "U001",
        session["session_id"],
        auth["authorization_id"],
        content,
    )
    assert replay.status_code == 403


def test_cross_user_style_access_is_blocked():
    _session_a, style_a = setup_user("U100")
    session_b, _style_b = setup_user("U200")

    response = authorize(
        "U200",
        session_b["session_id"],
        style_a["style_id"],
        "Blocked",
    )
    assert response.status_code == 403


def test_content_binding_is_enforced_server_side():
    session, style = setup_user("U300")
    auth_response = authorize(
        "U300",
        session["session_id"],
        style["style_id"],
        "Original",
    )
    auth = auth_response.json()

    response = generate(
        "U300",
        session["session_id"],
        auth["authorization_id"],
        "Modified",
    )
    assert response.status_code == 403


def test_revoked_style_blocks_existing_authorization():
    session, style = setup_user("U400")
    content = "Revoked"
    auth_response = authorize(
        "U400",
        session["session_id"],
        style["style_id"],
        content,
    )
    auth = auth_response.json()

    revoke = client.post(
        f"/revoke/{style['style_id']}",
        params={"user_id": "U400"},
    )
    assert revoke.status_code == 200

    response = generate(
        "U400",
        session["session_id"],
        auth["authorization_id"],
        content,
    )
    assert response.status_code == 403


def test_purpose_and_model_binding_are_enforced():
    session, style = setup_user("U500")
    content = "Binding"

    auth = authorize(
        "U500",
        session["session_id"],
        style["style_id"],
        content,
    ).json()

    wrong_purpose = generate(
        "U500",
        session["session_id"],
        auth["authorization_id"],
        content,
        purpose="export",
    )
    assert wrong_purpose.status_code == 403

    auth2 = authorize(
        "U500",
        session["session_id"],
        style["style_id"],
        content,
    ).json()

    wrong_model = generate(
        "U500",
        session["session_id"],
        auth2["authorization_id"],
        content,
        model_version="different-renderer",
    )
    assert wrong_model.status_code == 403


def test_provenance_is_user_and_session_scoped():
    session, style = setup_user("U600")
    content = "Provenance"

    auth = authorize(
        "U600",
        session["session_id"],
        style["style_id"],
        content,
    ).json()

    generation = generate(
        "U600",
        session["session_id"],
        auth["authorization_id"],
        content,
    ).json()

    allowed = client.get(
        f"/provenance/{generation['generation_id']}",
        params={
            "user_id": "U600",
            "session_id": session["session_id"],
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["provenance_digest"] == generation["provenance_digest"]

    other_session = client.post(
        "/sessions",
        json={"user_id": "U601"},
    ).json()
    denied = client.get(
        f"/provenance/{generation['generation_id']}",
        params={
            "user_id": "U601",
            "session_id": other_session["session_id"],
        },
    )
    assert denied.status_code == 403
