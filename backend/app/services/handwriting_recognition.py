"""English handwritten text recognition service backed by the public TrOCR model.

The model and processor are downloaded from Hugging Face on first use and then
cached by huggingface_hub. They are intentionally not downloaded during API
startup so the rest of the prototype remains usable while the cache is cold.
"""
from __future__ import annotations

import io
import os
import threading
from typing import Any

MODEL_ID = os.getenv("WRITLYNX_HTR_MODEL_ID", "microsoft/trocr-base-handwritten")
MAX_IMAGE_PIXELS = 12_000_000
MAX_LINES_PER_PAGE = 40

_model_lock = threading.Lock()
_processor: Any | None = None
_model: Any | None = None
_torch: Any | None = None
_device: Any | None = None


class InvalidHandwritingImage(ValueError):
    """Raised when the uploaded file is not a supported, readable page image."""


class RecognitionModelUnavailable(RuntimeError):
    """Raised when the model weights or inference dependencies are unavailable."""


def _load_model() -> tuple[Any, Any, Any]:
    global _processor, _model, _torch, _device
    if _processor is not None and _model is not None and _torch is not None:
        return _processor, _model, _torch

    with _model_lock:
        if _processor is not None and _model is not None and _torch is not None:
            return _processor, _model, _torch
        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            processor = TrOCRProcessor.from_pretrained(MODEL_ID)
            model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            model.eval()
        except Exception as exc:
            # Do not leak local paths, tokens, or arbitrary dependency errors to clients.
            raise RecognitionModelUnavailable(
                "The English TrOCR model could not be loaded. Check the backend dependencies and network access to Hugging Face, then retry."
            ) from exc

        _processor, _model, _torch, _device = processor, model, torch, device
        return _processor, _model, _torch


def _prepare_lines(image_bytes: bytes) -> list[Any]:
    try:
        import numpy as np
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(image_bytes)) as opened:
            if opened.width < 32 or opened.height < 16:
                raise InvalidHandwritingImage("The image is too small to recognize.")
            if opened.width * opened.height > MAX_IMAGE_PIXELS:
                raise InvalidHandwritingImage(
                    "The page is too large. Upload an image with at most 12 megapixels."
                )
            opened.load()
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except InvalidHandwritingImage:
        raise
    except Exception as exc:
        raise InvalidHandwritingImage(
            "This file is not a readable image. Upload a PNG, JPEG, or WEBP image."
        ) from exc

    gray = np.asarray(image.convert("L"))
    ink = gray < 190
    row_ink = ink.sum(axis=1)
    min_ink = max(2, int(image.width * 0.001))
    active_rows = row_ink > min_ink

    row_indexes = np.flatnonzero(active_rows)
    if len(row_indexes) == 0:
        raise InvalidHandwritingImage(
            "No handwriting was detected. Use a darker, sharper image with clear writing."
        )

    # Merge neighboring ink rows into text-line bands, tolerating small gaps between
    # the ascenders, descenders, and disconnected pen strokes in ordinary handwriting.
    merge_gap = max(3, min(10, image.height // 220))
    groups: list[tuple[int, int]] = []
    start = previous = int(row_indexes[0])
    for row in row_indexes[1:]:
        row = int(row)
        if row - previous > merge_gap + 1:
            groups.append((start, previous + 1))
            start = row
        previous = row
    groups.append((start, previous + 1))

    min_line_height = max(5, int(image.height * 0.002))
    line_images: list[Any] = []
    for top, bottom in groups:
        if bottom - top < min_line_height:
            continue
        # Trim white margins while keeping a small horizontal breathing room.
        line_ink = ink[max(0, top - 4):min(image.height, bottom + 4)]
        columns = np.flatnonzero(line_ink.sum(axis=0) > 0)
        if len(columns) == 0:
            continue
        left = max(0, int(columns[0]) - 12)
        right = min(image.width, int(columns[-1]) + 13)
        upper = max(0, top - 8)
        lower = min(image.height, bottom + 8)
        line_images.append(image.crop((left, upper, right, lower)))

    if not line_images:
        raise InvalidHandwritingImage(
            "Could not separate readable text lines. Try a sharper image with larger writing and clear line spacing."
        )
    if len(line_images) > MAX_LINES_PER_PAGE:
        raise InvalidHandwritingImage(
            f"This prototype can process up to {MAX_LINES_PER_PAGE} lines per image. Crop the page into smaller sections."
        )
    return line_images


def recognize_english_page(image_bytes: bytes) -> dict[str, Any]:
    """Recognize a clear, single-column English handwriting page.

    Returns a transcript and trace metadata; the uploaded image itself is not
    written to disk or stored in the database.
    """
    if not image_bytes:
        raise InvalidHandwritingImage("Choose an image before starting recognition.")

    lines = _prepare_lines(image_bytes)
    processor, model, torch = _load_model()
    output_lines: list[str] = []

    try:
        with torch.inference_mode():
            for line_image in lines:
                pixel_values = processor(images=line_image, return_tensors="pt").pixel_values
                pixel_values = pixel_values.to(_device)
                generated_ids = model.generate(
                    pixel_values,
                    max_new_tokens=128,
                    num_beams=4,
                )
                decoded = processor.batch_decode(
                    generated_ids, skip_special_tokens=True
                )[0].strip()
                output_lines.append(decoded)
    except Exception as exc:
        raise RecognitionModelUnavailable(
            "English handwriting recognition failed during inference. Retry with a clearer image or check the backend model installation."
        ) from exc

    transcript = "\n".join(line for line in output_lines if line).strip()
    if not transcript:
        raise InvalidHandwritingImage(
            "The model returned no readable text. Try a clearer image with higher contrast."
        )

    return {
        "transcript": transcript,
        "lines_recognized": len(output_lines),
        "model_id": MODEL_ID,
    }
