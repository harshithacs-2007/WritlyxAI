"""Pre-download the configured pretrained English handwriting model into HF cache.

Run once from the backend directory:
    py download_htr_model.py

Download the safetensors checkpoint and processor/tokenizer metadata only; do not
download the duplicate PyTorch .bin checkpoint or add large weights to Git.
"""
from huggingface_hub import snapshot_download

from app.config import settings


def main() -> None:
    print(f"Downloading model assets for: {settings.htr_model_id}")
    print("The safetensors checkpoint is about 1.33 GB. Ensure disk space and network access.")
    print("Only the safe-tensors weights and required JSON/text processor files will be cached.")
    snapshot_path = snapshot_download(
        repo_id=settings.htr_model_id,
        allow_patterns=[
            "config.json",
            "generation_config.json",
            "model.safetensors",
            "preprocessor_config.json",
            "special_tokens_map.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "vocab.json",
            "merges.txt",
        ],
    )
    print(f"Model cache ready: {snapshot_path}")
    print("You can now start the API; recognition will reuse the cached files.")


if __name__ == "__main__":
    main()
