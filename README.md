# WritLynxAI

WritLynxAI is a research prototype exploring personalized handwriting generation, handwritten text recognition, and controlled, traceable use of handwriting styles.

## Applications

- \`frontend/\` — the primary Next.js experience. It contains the landing page, generation workspace, and recognition workspace.
- \`backend/\` — FastAPI + SQLite prototype control layer for sessions, style records, authorization, one-time authorization consumption, revocation, and provenance.
- \`index.html\` — an older standalone browser demo. It is separate from the Next.js application.

## Run the Next.js application locally

From PowerShell:

    cd frontend
    npm install
    Copy-Item .env.example .env.local
    npm run dev

Open http://localhost:3000.

To connect the FastAPI control layer, set NEXT_PUBLIC_API_BASE_URL in \`frontend/.env.local\`, normally to \`http://127.0.0.1:8000\`.

## Run the backend locally

From a second terminal:

    cd backend
    py -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    pip install -r requirements.txt
    Copy-Item .env.example .env
    uvicorn app.main:app --reload

The backend API docs are available at http://127.0.0.1:8000/docs.

## Prototype boundaries

- The current generation page uses a deterministic visual simulation. It is not a trained handwriting synthesis model and does not create a real style embedding.
- The recognition page prepares a page image and editable transcript, but an OCR/handwritten-text-recognition model is not connected yet.
- The FastAPI service demonstrates application-level controls. It is not production authentication or production-grade ML execution.
- For a Next.js deployment on Vercel, set the project's Root Directory to \`frontend\`. A deployment configured with the repository root will instead serve the older standalone \`index.html\`.
- The existing GitHub Pages workflow builds the \`frontend/\` application on pushes to \`main\`.
