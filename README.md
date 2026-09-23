# WritlynxAI

Research prototype for personalized handwriting synthesis with controlled style use and provenance.

## Prototype

- `index.html` — standalone interactive demo
- `frontend/` — Next.js prototype application
- `backend/` — FastAPI + SQLite security/control layer

The standalone page is intentionally deterministic and does not claim to be the trained handwriting model.

## Deploying the standalone page

The repository can be imported into Vercel with the repository root as the project root. No build step is required; Vercel serves `index.html` directly.

The expected user flow is:

Capture -> Generate -> Provenance

The backend remains a separate FastAPI service for the Review II security-control demonstration.
