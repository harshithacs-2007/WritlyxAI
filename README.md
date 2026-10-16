# WritLynxAI

WritLynxAI is a prototype for two handwriting workflows: personalized handwriting generation and handwritten text recognition.

## Applications

- frontend/ — Next.js experience with a live illustrative text preview, generation workspace, English recognition workspace, and persistent Light/Dark themes.
- backend/ — FastAPI + SQLite control layer plus a pretrained English handwriting-recognition endpoint.
- index.html — an older standalone browser demo, separate from the Next.js application.

## Run locally (Windows PowerShell)

Start the backend in the first terminal:

    cd backend
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Copy-Item .env.example .env
    py download_htr_model.py
    uvicorn app.main:app --reload

Start the frontend in a second terminal from the repository root:

    cd frontend
    npm install
    Copy-Item .env.example .env.local
    npm run dev

Open http://localhost:3000. The frontend's local environment example points to http://127.0.0.1:8000.

## Current functionality

- **English recognition:** uploads a PNG/JPEG/WEBP page to the FastAPI endpoint, runs the pretrained TrOCR model, returns an editable transcript, and stores a recognition job/checksum/transcript in the existing SQLite database. The original source image is not retained.
- **Recognition history:** lists recent jobs belonging to the current prototype session so a transcript can be reopened and edited.
- **Generation:** retains the existing session, style record, authorization, one-time-consumption and provenance flow. The current handwriting appearance is still browser-rendered visual simulation, not model-generated handwriting; a pretrained generation model is a separate integration task.
- **Themes and motion:** Light/Dark preference persists across routes; scroll motion is reduced when a user prefers reduced motion.

## Model and storage considerations

The HTR model is microsoft/trocr-base-handwritten, MIT-licensed and fine-tuned on IAM. Its safetensors checkpoint is about 1.33 GB. Run `py download_htr_model.py` to cache it and only the required tokenizer/processor files (weights remain outside Git). First run needs network and disk space; CPU inference may be slow. TrOCR is designed for single text-line input; the prototype performs simple line segmentation and is best with clear, single-column English handwriting. Review every transcript.

The SQLite database already used by the project adds a recognition_jobs table. It stores transcript text, image checksum, filename, model ID, line count and status—not raw uploaded image bytes. Configure WRITLYNX_DATABASE_URL to move the database file.

## Prototype boundaries

- English recognition is a pretrained baseline, not a new model trained by this team.
- Automatic handwriting generation and real writer-style extraction are not integrated yet.
- The generation page's visual output is not AI-generated.
- The FastAPI service and user ID flow are prototype controls, not production authentication infrastructure.
- For a Vercel deployment, set the frontend Root Directory to frontend. The backend must separately run somewhere with enough disk/RAM to load TrOCR; configuring a URL does not deploy the model server.
- The GitHub Pages workflow builds the frontend app on pushes to main.

See backend/README.md for API, model and database details.
