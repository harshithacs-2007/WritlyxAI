# WritLynxAI frontend

A product-oriented Next.js prototype for personalized handwriting generation and English handwritten text recognition, with a persistent Light/Dark theme and reduced-motion-aware scroll interactions.

## Product routes

- `/` — interactive text/paper preview and direct links to the main tools. The preview is illustrative, not produced by a neural generation model.
- `/studio` — handwriting sample intake, text entry, illustrative paper preview, and the existing FastAPI authorization/provenance path.
- `/recognize` — upload a handwritten English image, call the backend TrOCR endpoint, edit/correct the transcript, download text, and reopen recent jobs saved in SQLite.

## Run locally

From the repository root, start the backend in one PowerShell terminal:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py download_htr_model.py
uvicorn app.main:app --reload
```

Then, in a second PowerShell terminal from the repository root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000. The frontend example points to `http://127.0.0.1:8000`. Run the model download once per backend machine/cache. It fetches about 1.33 GB of weights plus tokenizer/processor files and needs network access.

## Prototype boundaries

- The landing-page paper and generation output are illustrative browser-side previews, not model-generated handwriting.
- The Generation route still preserves its existing session/style/authorization/provenance flow. Personal handwriting generation needs a separate trained generation pipeline; TrOCR cannot generate a handwriting style.
- The Recognition route uses a pretrained TrOCR model fine-tuned for English handwriting on IAM. Its lightweight line segmentation is best with clear, single-column pages. Low-quality, slanted, dense, or unusual writing may produce incorrect text; review every output.
- The Recognition API stores transcript, image SHA-256, model ID, filename and run status in the existing SQLite database. It does not store the original source image.
- The demo user/session flow is not production authentication. Do not use sensitive pages or deploy it publicly with this demo identity.
- Landing-page scroll motion uses Framer Motion and is reduced for users who prefer reduced motion.
