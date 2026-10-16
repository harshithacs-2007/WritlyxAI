# WritLynxAI frontend

A product-oriented Next.js prototype for two handwriting workflows, with a persistent Light/Dark theme and reduced-motion-aware scroll interactions.

## Product routes

- `/` — concise product landing page with a live editable text/paper preview. Continue in the studio to carry the preview text into the generation workspace.
- `/studio` — handwriting sample intake, text entry, an illustrative paper preview, and the existing FastAPI authorization/provenance flow when `NEXT_PUBLIC_API_BASE_URL` is configured.
- `/recognize` — local source-image preview, editable manual transcript, and text-file download.

## Run locally

From this directory, install dependencies, copy `.env.example` to `.env.local`, then run:

```bash
npm install
npm run dev
```

Open http://localhost:3000.

To connect the FastAPI control layer, set `NEXT_PUBLIC_API_BASE_URL` in `.env.local`, normally to `http://127.0.0.1:8000`.

## Prototype boundaries

- The landing-page paper is a live UI preview, not model-generated handwriting.
- The generation workspace uses deterministic browser-side visual styling. It is not a trained handwriting-synthesis model and does not extract a real style embedding.
- When the API URL is configured, generation requests preserve the existing session, style record, authorization, one-time consumption, and provenance endpoint sequence. If the backend request fails, the UI reports the error instead of silently falling back to local mode.
- The recognition page does not perform OCR or HTR yet. Uploaded images remain in the browser; the transcript can be edited manually and downloaded as a text file.
- The security backend remains a prototype control layer, not production authentication infrastructure.
- Landing-page motion uses the existing Framer Motion dependency; scroll-linked movement is disabled or reduced for users who prefer reduced motion.
