# WritLynxAI frontend

Next.js prototype for two handwriting workflows.

- /studio — handwriting sample intake, local visual preview, and the existing FastAPI authorization/provenance flow when NEXT_PUBLIC_API_BASE_URL is configured.
- /recognize — local source-image preview and editable manual transcript workspace, ready for a future handwritten-text-recognition model.

## Run locally

From this directory, install dependencies, copy .env.example to .env.local, then run npm run dev. Open http://localhost:3000.

To connect the FastAPI control layer, set NEXT_PUBLIC_API_BASE_URL in .env.local, normally to http://127.0.0.1:8000.

## Current prototype boundaries

- The generation page uses deterministic browser-side visual simulation. It is not a trained handwriting synthesis model and does not extract a real style embedding.
- When the API URL is configured, generation requests preserve the existing session, style record, authorization, one-time consumption, and provenance endpoint sequence. If the backend request fails, the UI reports the error instead of silently falling back to local mode.
- The recognition page does not perform OCR or HTR yet. Uploaded images remain in the browser; the transcript can be edited manually and downloaded as a text file.
- The security backend remains a prototype control layer, not production authentication infrastructure.
