# WritLynxAI backend

FastAPI + SQLite prototype for generation authorization/provenance and English handwriting recognition.

## What it does

- Session-bound access for prototype requests.
- Style ownership, purpose/model/content binding, one-time authorization, revocation, and generation provenance.
- English handwriting recognition through Microsoft's pretrained TrOCR base model.
- SQLite records for recognition jobs, transcripts, file checksums, model ID, status, and line count.
- Recognition uploads are processed in memory and **are not stored**. Style-reference images explicitly uploaded through the Generation workspace **are stored as SQLite BLOBs** (up to five images, 8 MB each) so a future style-conditioned generator can use them.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Backend health check |
| POST | /sessions | Create prototype session |
| POST | /styles | Create a style representation record |
| POST | /styles/{style_id}/samples | Store 1–5 writing-reference images for future style generation |
| GET | /styles/{style_id}/samples | List saved reference-image metadata for the active session |
| DELETE | /styles/{style_id}/samples/{sample_id} | Delete a saved reference image |
| POST | /authorize | Issue purpose/model/content-bound authorization |
| POST | /generate | Consume authorization and create generation provenance |
| GET | /provenance/{generation_id} | Retrieve provenance for the owning session |
| POST | /revoke/{style_id} | Revoke a style and active authorizations |
| POST | /recognize | Recognize English handwriting from a PNG/JPEG/WEBP image |
| GET | /recognitions | List recent recognition jobs belonging to an active session |

The style-reference endpoint accepts multipart fields files (1–5), user_id, and session_id. It stores validated PNG/JPEG/WEBP image bytes and a SHA-256 digest; the user can delete saved references from the Generation workspace. The generation model is not connected yet, so persisted style samples are groundwork for the next step.

The recognition endpoint accepts multipart form fields file, user_id, and session_id. It returns an editable transcript, model identifier, SHA-256 of the input image, number of processed lines, and the persisted job ID. Recent results can be listed with user_id and session_id query parameters. Swagger UI is available at /docs.

## Run on Windows PowerShell

    cd backend
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Copy-Item .env.example .env
    py download_htr_model.py
    uvicorn app.main:app --reload

The frontend expects NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 in frontend/.env.local.

## English HTR model

The configured default is microsoft/trocr-base-handwritten, an MIT-licensed model fine-tuned on IAM. TrOCR is intended for **single text-line images**, so this prototype segments a clear single-column page into line crops before inference. The segmentation is intentionally lightweight; columns, skew, tables, very dense pages, and unusual layouts can produce poor transcripts. Always review model output.

- Run `py download_htr_model.py` to download the safetensors checkpoint (about 1.33 GB) plus the tokenizer/processor files into the normal Hugging Face cache. The service can also lazy-download the model on the first `/recognize` request. Model weights are not committed to Git.
- The model checkpoint alone is about 1.33 GB, so allow extra disk space for the PyTorch runtime and cache. The first call requires network access; CPU inference works but can be slow.
- WRITLYNX_HTR_MODEL_ID can select a compatible model via .env. Keep it compatible with the configured TrOCR loader and evaluate it before use.
- Upload limit: 8 MB; decoded image limit: 12 megapixels; at most 40 detected text lines per image.

## Database behaviour

The project already uses SQLAlchemy with SQLite. The recognition_jobs table stores the recognition filename, image SHA-256, transcript, model ID, job status and line count; **recognition source images are not retained**. The style_samples table stores up to five explicitly selected Generation reference images per style, with filename, MIME type, digest, and bytes. The user can delete these image rows. Database path defaults to ./writlynxai.db relative to the backend process working directory.

## Review II security controls

The existing generation path continues to enforce:

- User/session binding and session expiry
- Style ownership validation
- Purpose and model-version binding
- Server-side content hashing and content binding
- Fresh nonce issuance and short-lived authorization
- One-time authorization consumption
- Style revocation and active-authorization revocation
- User/session-scoped provenance records and audit events

## Prototype boundary

This is application-level prototype infrastructure, not production identity/security infrastructure. The user_id supplied by the prototype client is not a trusted production identity. HTR outputs are not guaranteed accurate, and the recognition route currently targets English handwriting using an IAM-fine-tuned baseline. SQLite stores prototype records; it does not provide production-scale tenancy, access control, or retention management.

## Citation

If you use TrOCR, cite: Li et al., *TrOCR: Transformer-based Optical Character Recognition with Pre-trained Models* (2021), https://arxiv.org/abs/2109.10282.
