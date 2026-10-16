"""Pre-download the selectively packaged DiffusionPen generation weights.

Run from the backend directory:
    py download_generation_model.py

The complete public DiffusionPen repository is about 10 GB because it also
contains prepared IAM training data and an optimizer state. This script skips
those unnecessary files and downloads only the generator weights needed for
inference, its five-shot style encoder, the CANINE text encoder, and the SD VAE.
"""
from huggingface_hub import snapshot_download

from app.services.handwriting_generation import (
    DIFFUSIONPEN_REPO,
    TEXT_ENCODER_REPO,
    VAE_REPO,
)


def main() -> None:
    print("Downloading the DiffusionPen EMA generator checkpoint (~680 MB) and style encoder (~11 MB)...")
    diffusionpen_path = snapshot_download(
        repo_id=DIFFUSIONPEN_REPO,
        allow_patterns=[
            "diffusionpen_iam_model_path/models/ema_ckpt.pt",
            "style_models/iam_style_diffusionpen.pth",
        ],
    )
    print(f"DiffusionPen weights cached: {diffusionpen_path}")

    print("Downloading the CANINE text encoder (~528 MB) and tokenizer/config files...")
    canine_path = snapshot_download(
        repo_id=TEXT_ENCODER_REPO,
        allow_patterns=[
            "config.json",
            "model.safetensors",
            "special_tokens_map.json",
            "tokenizer_config.json",
        ],
    )
    print(f"CANINE assets cached: {canine_path}")

    print("Downloading the Stable Diffusion VAE (~335 MB) and config. No full image-generation pipeline is downloaded.")
    vae_path = snapshot_download(
        repo_id=VAE_REPO,
        allow_patterns=[
            "config.json",
            "diffusion_pytorch_model.safetensors",
        ],
    )
    print(f"VAE assets cached: {vae_path}")
    print("Generation assets are ready. Model weights remain in the Hugging Face cache, not in Git.")


if __name__ == "__main__":
    main()
