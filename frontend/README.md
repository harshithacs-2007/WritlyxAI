# WritlynxAI Frontend

Next.js prototype UI for Review II.

Run in PowerShell:

cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev

Open http://localhost:3000.

For backend integration, set NEXT_PUBLIC_API_BASE_URL to the FastAPI server, normally http://127.0.0.1:8000.

The Studio uses sessions, styles, authorization and generation from the backend when reachable. When the backend is not reachable, it falls back to a clearly labeled local prototype renderer so the website remains demonstrable.

The generated handwriting is a deterministic browser renderer, not the trained handwriting model. Real style encoding and trained/fine-tuned handwriting generation belong to the research-integration phase.
