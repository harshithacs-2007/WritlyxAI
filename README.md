# WritlynxAI

WritlynxAI is a research prototype for personalized handwriting synthesis with controlled style usage and provenance.

## Repository structure

- frontend/ — Next.js user-facing prototype
- backend/ — FastAPI + SQLite control layer
- .github/workflows/ — GitHub Pages deployment

## Run locally

Frontend:

    cd frontend
    npm install
    npm run dev

Backend:

    cd backend
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Then set frontend/.env.local:

    NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000

The frontend can also run without the backend using its clearly labelled local prototype renderer.

## Review II scope

The current prototype demonstrates:

Capture -> style representation -> authorization -> generation -> provenance

The browser renderer is deterministic prototype behavior. It is not the trained handwriting model. Training/fine-tuning and protected ML execution are part of the research-integration phase.

## GitHub Pages

Every push to main that changes frontend/ triggers the Pages workflow. The expected site path is:

https://harshithacs-2007.github.io/WritlyxAI/

The repository's GitHub Pages feature may need to be enabled under Settings -> Pages with GitHub Actions as the source.
