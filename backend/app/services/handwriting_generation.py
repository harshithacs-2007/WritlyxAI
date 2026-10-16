"""Few-shot English handwriting generation using pretrained DiffusionPen.

This loader downloads only the generator EMA checkpoint and its style-encoder
weights from the official public checkpoint repo. It deliberately does not
download the paper's preprocessed IAM training dataset or optimizer state.
"""
from __future__ import annotations

import io
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
from PIL import Image, ImageOps

DIFFUSIONPEN_REPO = "konnik/DiffusionPen"
VAE_REPO = "stabilityai/sd-vae-ft-mse"
TEXT_ENCODER_REPO = "google/canine-c"
MAX_REFERENCE_PIXELS = 12_000_000
MAX_REFERENCE_BYTES = 8 * 1024 * 1024
MAX_WORDS_PER_REQUEST = 48
DIFFUSION_STEPS = 50
DIFFUSIONPEN_CHAR_CLASSES = "!\"#&'()*+,-./0123456789:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "

_model_lock = threading.Lock()
_unet: Any | None = None
_style_encoder: Any | None = None
_tokenizer: Any | None = None
_vae: Any | None = None
_scheduler: Any | None = None
_torch: Any | None = None
_device: Any | None = None


class HandwritingGenerationUnavailable(RuntimeError):
    """Raised when one of the pretrained handwriting model components is unavailable."""


class InvalidStyleReferences(ValueError):
    """Raised when the saved reference images do not contain usable handwriting words."""


def _read_tensor_checkpoint(path: Path, torch: Any) -> dict[str, Any]:
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        payload = torch.load(path, map_location="cpu")
    if isinstance(payload, dict) and isinstance(payload.get("state_dict"), dict):
        payload = payload["state_dict"]
    if not isinstance(payload, dict):
        raise HandwritingGenerationUnavailable("A pretrained checkpoint has an unexpected format.")
    return payload


def _normalise_unet_state_dict(state: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in state.items():
        while key.startswith("module."):
            key = key[len("module."):]
        # The reference training code wraps its CANINE model in DataParallel.
        key = key.replace("text_encoder.module.", "text_encoder.")
        cleaned[key] = value
    return cleaned


def _load_models() -> tuple[Any, Any, Any, Any, Any, Any]:
    global _unet, _style_encoder, _tokenizer, _vae, _scheduler, _torch, _device
    if all(item is not None for item in (_unet, _style_encoder, _tokenizer, _vae, _scheduler, _torch, _device)):
        return _unet, _style_encoder, _tokenizer, _vae, _scheduler, _torch

    with _model_lock:
        if all(item is not None for item in (_unet, _style_encoder, _tokenizer, _vae, _scheduler, _torch, _device)):
            return _unet, _style_encoder, _tokenizer, _vae, _scheduler, _torch
        try:
            import torch
            from diffusers import AutoencoderKL, DDIMScheduler
            from huggingface_hub import snapshot_download
            from transformers import CanineModel, CanineTokenizer

            from app.vendor.diffusionpen.feature_extractor import ImageEncoder
            from app.vendor.diffusionpen.unet import UNetModel

            checkpoint_root = Path(snapshot_download(
                repo_id=DIFFUSIONPEN_REPO,
                allow_patterns=[
                    "diffusionpen_iam_model_path/models/ema_ckpt.pt",
                    "style_models/iam_style_diffusionpen.pth",
                ],
            ))
            unet_checkpoint = checkpoint_root / "diffusionpen_iam_model_path/models/ema_ckpt.pt"
            style_checkpoint = checkpoint_root / "style_models/iam_style_diffusionpen.pth"
            if not unet_checkpoint.is_file() or not style_checkpoint.is_file():
                raise FileNotFoundError("Official DiffusionPen checkpoint files were not found.")

            cuda_ready = torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory >= 8 * 1024 ** 3
            device = torch.device("cuda" if cuda_ready else "cpu")
            tokenizer = CanineTokenizer.from_pretrained(TEXT_ENCODER_REPO)
            text_encoder = CanineModel.from_pretrained(TEXT_ENCODER_REPO, use_safetensors=True)
            args = SimpleNamespace(interpolation=False, mix_rate=None)
            unet = UNetModel(
                image_size=(64, 256),
                in_channels=4,
                model_channels=320,
                out_channels=4,
                num_res_blocks=1,
                attention_resolutions=(1, 1),
                channel_mult=(1, 1),
                num_heads=4,
                num_classes=339,
                context_dim=320,
                vocab_size=len(DIFFUSIONPEN_CHAR_CLASSES),
                text_encoder=text_encoder,
                args=args,
            )
            raw_state = _read_tensor_checkpoint(unet_checkpoint, torch)
            state = _normalise_unet_state_dict(raw_state)
            expected = unet.state_dict()
            matched = {key: value for key, value in state.items() if key in expected and getattr(value, "shape", None) == expected[key].shape}
            if len(matched) < int(len(expected) * 0.90):
                raise HandwritingGenerationUnavailable(
                    "DiffusionPen checkpoint does not match the vendored architecture. Check the model repository revision."
                )
            unet.load_state_dict(matched, strict=False)
            del raw_state, state, matched, expected
            unet.to(device)
            unet.eval()
            for parameter in unet.parameters():
                parameter.requires_grad_(False)

            # The official style checkpoint is trained against this MobileNetV2 encoder.
            style_encoder = ImageEncoder(
                model_name="mobilenetv2_100",
                num_classes=0,
                pretrained=True,
                trainable=False,
            )
            style_state = _read_tensor_checkpoint(style_checkpoint, torch)
            style_state = {
                key.removeprefix("module."): value
                for key, value in style_state.items()
            }
            current_style_state = style_encoder.state_dict()
            matched_style = {
                key: value for key, value in style_state.items()
                if key in current_style_state and getattr(value, "shape", None) == current_style_state[key].shape
            }
            if len(matched_style) < int(len(current_style_state) * 0.90):
                raise HandwritingGenerationUnavailable(
                    "The DiffusionPen style checkpoint does not match its encoder architecture."
                )
            current_style_state.update(matched_style)
            style_encoder.load_state_dict(current_style_state)
            style_encoder.to(device)
            style_encoder.eval()
            for parameter in style_encoder.parameters():
                parameter.requires_grad_(False)
            del style_state, current_style_state, matched_style

            # This VAE has the same SD latent scale used by the DiffusionPen release.
            vae = AutoencoderKL.from_pretrained(VAE_REPO, use_safetensors=True)
            vae.to(device)
            vae.eval()
            for parameter in vae.parameters():
                parameter.requires_grad_(False)

            scheduler = DDIMScheduler(
                num_train_timesteps=1000,
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear",
                clip_sample=False,
                set_alpha_to_one=False,
                steps_offset=1,
                prediction_type="epsilon",
            )
        except HandwritingGenerationUnavailable:
            raise
        except Exception as exc:
            raise HandwritingGenerationUnavailable(
                "The handwriting-generation model could not be loaded. Check model download access, available memory, and backend dependencies."
            ) from exc

        _unet, _style_encoder, _tokenizer = unet, style_encoder, tokenizer
        _vae, _scheduler, _torch, _device = vae, scheduler, torch, device
        return _unet, _style_encoder, _tokenizer, _vae, _scheduler, _torch


def _otsu_threshold(gray: np.ndarray) -> int:
    histogram = np.bincount(gray.reshape(-1), minlength=256).astype(np.float64)
    total = histogram.sum()
    if total <= 0:
        return 180
    probability = histogram / total
    cumulative_probability = np.cumsum(probability)
    levels = np.arange(256, dtype=np.float64)
    cumulative_mean = np.cumsum(probability * levels)
    total_mean = cumulative_mean[-1]
    denominator = cumulative_probability * (1.0 - cumulative_probability)
    between = np.zeros(256, dtype=np.float64)
    valid = denominator > 1e-12
    between[valid] = (total_mean * cumulative_probability[valid] - cumulative_mean[valid]) ** 2 / denominator[valid]
    threshold = int(np.argmax(between))
    return min(225, max(80, threshold))


def _contiguous_groups(active: np.ndarray, max_gap: int) -> list[tuple[int, int]]:
    indexes = np.flatnonzero(active)
    if len(indexes) == 0:
        return []
    groups: list[tuple[int, int]] = []
    start = previous = int(indexes[0])
    for value in indexes[1:]:
        value = int(value)
        if value - previous > max_gap + 1:
            groups.append((start, previous + 1))
            start = value
        previous = value
    groups.append((start, previous + 1))
    return groups


def _reference_image_to_words(image_bytes: bytes) -> list[Image.Image]:
    if not image_bytes:
        raise InvalidStyleReferences("One of the reference images is empty.")
    try:
        with Image.open(io.BytesIO(image_bytes)) as opened:
            if (opened.format or "").upper() not in {"PNG", "JPEG", "WEBP"}:
                raise InvalidStyleReferences("Style references must be PNG, JPEG, or WEBP images.")
            if opened.width < 32 or opened.height < 16:
                raise InvalidStyleReferences("A handwriting reference image is too small.")
            if opened.width * opened.height > MAX_REFERENCE_PIXELS:
                raise InvalidStyleReferences("A reference image is larger than 12 megapixels.")
            opened.load()
            page = ImageOps.exif_transpose(opened).convert("RGB")
    except InvalidStyleReferences:
        raise
    except Exception as exc:
        raise InvalidStyleReferences("A saved style reference is not a readable image.") from exc

    gray = np.asarray(page.convert("L"))
    threshold = _otsu_threshold(gray)
    ink = gray < threshold
    height, width = ink.shape
    active_rows = ink.sum(axis=1) > max(2, int(width * 0.001))
    line_groups = _contiguous_groups(active_rows, max(3, min(12, height // 200)))
    words: list[Image.Image] = []

    for top, bottom in line_groups:
        if bottom - top < max(5, int(height * 0.003)):
            continue
        band_top = max(0, top - 5)
        band_bottom = min(height, bottom + 5)
        band = ink[band_top:band_bottom]
        active_columns = band.sum(axis=0) > 0
        # Word spaces are wider than most intra-word pen gaps. This heuristic is
        # deliberately conservative; the model is still only few-shot conditioned.
        word_gap = max(6, min(22, int(width * 0.009)))
        word_groups = _contiguous_groups(active_columns, word_gap)
        for left, right in word_groups:
            if right - left < 5:
                continue
            pad_x = max(3, int((right - left) * 0.035))
            crop_left = max(0, left - pad_x)
            crop_right = min(width, right + pad_x)
            crop_top = max(0, band_top - 2)
            crop_bottom = min(height, band_bottom + 2)
            crop = page.crop((crop_left, crop_top, crop_right, crop_bottom))
            if crop.width >= 5 and crop.height >= 5:
                words.append(crop)

    if not words:
        raise InvalidStyleReferences(
            "No clear handwriting words were found in a style reference. Use a brighter page with darker, separated writing."
        )
    return words


def _make_style_tensor(word_images: list[Image.Image], torch: Any, device: Any) -> Any:
    from PIL import ImageOps

    tensors = []
    for image in word_images:
        image = image.convert("RGB")
        image = ImageOps.pad(image, (256, 64), method=Image.Resampling.BICUBIC, color=(255, 255, 255), centering=(0.5, 0.5))
        array = np.asarray(image, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1)
        tensor = (tensor - 0.5) / 0.5
        tensors.append(tensor)
    return torch.stack(tensors).to(device)


def _prepare_generated_word(image_array: np.ndarray) -> Image.Image:
    image = Image.fromarray(image_array).convert("RGB")
    gray = np.asarray(image.convert("L"))
    ink = gray < 235
    row_ink = np.flatnonzero(ink.sum(axis=1) > 0)
    col_ink = np.flatnonzero(ink.sum(axis=0) > 0)
    if len(row_ink) and len(col_ink):
        image = image.crop((
            max(0, int(col_ink[0]) - 3),
            max(0, int(row_ink[0]) - 2),
            min(image.width, int(col_ink[-1]) + 4),
            min(image.height, int(row_ink[-1]) + 3),
        ))
    target_height = 70
    target_width = max(12, int(image.width * target_height / max(1, image.height)))
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def _generate_word_images(words: list[str], style_tensors: Any) -> list[Image.Image]:
    unet, style_encoder, tokenizer, vae, scheduler, torch = _load_models()
    device = _device
    results: list[Image.Image] = []
    batch_size = 4

    for offset in range(0, len(words), batch_size):
        batch_words = words[offset:offset + batch_size]
        if not batch_words:
            continue
        # The original model averages five 1280-D reference features per word.
        batch_styles = style_tensors.repeat(len(batch_words), 1, 1, 1)
        with torch.inference_mode():
            style_features = style_encoder(batch_styles)
            style_features = style_features.reshape(len(batch_words) * 5, -1)
            text_features = tokenizer(
                batch_words,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
                max_length=40,
            ).to(device)
            latent = torch.randn(
                (len(batch_words), 4, 8, 32),
                device=device,
                dtype=next(unet.parameters()).dtype,
            )
            scheduler.set_timesteps(DIFFUSION_STEPS, device=device)
            labels = torch.zeros(len(batch_words), dtype=torch.long, device=device)
            for timestep in scheduler.timesteps:
                times = torch.full(
                    (len(batch_words),), int(timestep.item()), dtype=torch.long, device=device
                )
                predicted_noise = unet(
                    latent,
                    times,
                    text_features,
                    labels,
                    mix_rate=None,
                    style_extractor=style_features,
                )
                latent = scheduler.step(predicted_noise, timestep, latent).prev_sample

            decoded = vae.decode(latent / 0.18215).sample
            decoded = (decoded / 2 + 0.5).clamp(0, 1)
            pixels = (decoded * 255).to(torch.uint8).cpu().permute(0, 2, 3, 1).numpy()

        results.extend(_prepare_generated_word(pixels[index]) for index in range(len(batch_words)))
    return results


def _compose_page(text: str, word_images: list[Image.Image]) -> bytes:
    page_width = 1200
    margin_x = 72
    margin_y = 78
    gap_x = 16
    line_gap = 28
    max_line_width = page_width - 2 * margin_x

    lines: list[list[Image.Image]] = []
    current: list[Image.Image] = []
    current_width = 0
    image_index = 0
    for paragraph_index, paragraph in enumerate(text.splitlines() or [text]):
        words = paragraph.split()
        if not words:
            if current:
                lines.append(current)
                current, current_width = [], 0
            lines.append([])
            continue
        for _word in words:
            image = word_images[image_index]
            image_index += 1
            needed = image.width if not current else gap_x + image.width
            if current and current_width + needed > max_line_width:
                lines.append(current)
                current, current_width = [], 0
                needed = image.width
            current.append(image)
            current_width += needed
        if current:
            lines.append(current)
            current, current_width = [], 0

    line_height = 70
    paragraph_gap = 22
    line_count = len(lines)
    page_height = max(260, margin_y * 2 + max(1, line_count) * (line_height + line_gap))
    canvas = Image.new("RGB", (page_width, page_height), (246, 241, 229))
    draw_y = margin_y
    for line in lines:
        if not line:
            draw_y += paragraph_gap
            continue
        x = margin_x
        for index, image in enumerate(line):
            canvas.paste(image, (x, draw_y))
            x += image.width + gap_x
        draw_y += line_height + line_gap

    header = Image.new("RGB", (page_width, 38), (246, 241, 229))
    canvas.paste(header, (0, 0))
    from PIL import ImageDraw
    drawing = ImageDraw.Draw(canvas)
    drawing.text((margin_x, 28), "WRTLYNXAI  /  DIFFUSIONPEN PREVIEW", fill=(130, 113, 86))
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def generate_handwriting_page(text: str, reference_images: list[bytes]) -> dict[str, Any]:
    """Generate an English handwritten-style PNG conditioned on saved reference images."""
    if not text.strip():
        raise ValueError("Enter the text to generate.")
    words = [word for word in text.split() if word]
    if len(words) > MAX_WORDS_PER_REQUEST:
        raise ValueError(f"This prototype can generate up to {MAX_WORDS_PER_REQUEST} words per request.")
    if not reference_images:
        raise InvalidStyleReferences("Save at least one handwriting reference image before generating.")
    all_words_by_image: list[list[Image.Image]] = []
    for image_bytes in reference_images[:5]:
        if len(image_bytes) > MAX_REFERENCE_BYTES:
            raise InvalidStyleReferences("A reference image is larger than 8 MB.")
        all_words_by_image.append(_reference_image_to_words(image_bytes))

    # Prefer one crop per submitted image so the five-shot reference set samples
    # different parts of the writer's pages. Fill any remaining slots from other words.
    chosen: list[Image.Image] = []
    for collection in all_words_by_image:
        if collection:
            chosen.append(collection[len(collection) // 2])
    remaining = [word for collection in all_words_by_image for word in collection]
    for candidate in remaining:
        if len(chosen) >= 5:
            break
        if candidate not in chosen:
            chosen.append(candidate)
    while chosen and len(chosen) < 5:
        chosen.append(chosen[-1].copy())
    if len(chosen) < 5:
        raise InvalidStyleReferences(
            "The uploaded pages did not contain enough usable handwriting. Upload a clearer page with several separated words."
        )

    _unet, _style_encoder, _tokenizer, _vae, _scheduler, torch = _load_models()
    style_tensors = _make_style_tensor(chosen[:5], torch, _device)
    generated_words = _generate_word_images(words, style_tensors)
    if not generated_words:
        raise HandwritingGenerationUnavailable("The model returned no generated words.")

    return {
        "image_bytes": _compose_page(text, generated_words),
        "model_id": "konnik/DiffusionPen (IAM pretrained weights)",
        "words_generated": len(generated_words),
        "reference_words_used": len(chosen[:5]),
    }
