# WritlynxAI — Person 2 Backend

FastAPI + SQLite prototype for the Review II security/control layer.

## What Person 2 owns

This module implements the backend control path around personalized handwriting generation:

`session -> style ownership -> authorization -> generation -> provenance`

### Implemented controls

- User/session binding
- Style ownership validation
- Purpose binding
- Model-version binding
- Server-side content hashing and content binding
- Fresh nonce issuance
- Short-lived authorization
- One-time authorization consumption
- Style revocation and revocation of active authorizations
- User/session-scoped provenance lookup
- Audit event persistence
- Security-focused automated tests

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | backend health check |
| POST | `/sessions` | create prototype session |
| POST | `/styles` | create a style representation record |
| POST | `/authorize` | issue purpose/model/content-bound authorization |
| POST | `/generate` | consume authorization and create provenance record |
| GET | `/provenance/{generation_id}` | retrieve provenance for the owning session |
| POST | `/revoke/{style_id}` | revoke a style and active authorizations |

Swagger UI is available at `/docs`.

## Run on Windows PowerShell

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Run tests:

```powershell
pytest -q
```

## Review II demo cases

### 1. Valid path — ALLOW

`U001 + Session(U001) + Style(U001) + valid authorization -> generation`

### 2. Cross-user access — BLOCK

`U002 + Session(U002) + Style(U001) -> 403`

### 3. Content substitution — BLOCK

Authorization for content A, then generation with content B -> `403`.

### 4. Replay — BLOCK

Reuse a consumed authorization ID -> `403`.

### 5. Revocation — BLOCK

Authorize, revoke style, then generate -> `403`.

### 6. Purpose/model substitution — BLOCK

Authorization for one purpose/model, then generate with another -> `403`.

## Important prototype boundary

This is an application-level prototype, not production identity/security infrastructure.

The `user_id` supplied by the prototype client is not a trusted production identity. SQLite is prototype storage. The current module does not claim secure storage of learned handwriting embeddings, production tenant isolation, confidential ML execution, distributed replay protection, or production-grade authentication.

The research implementation can later replace these boundaries with real identity, protected representation storage, isolated ML execution, concurrency-safe authorization, and controlled provenance infrastructure.
