"""Download the configured pretrained English handwriting model into the HF cache.

Run from the backend directory after installing requirements:
    py download_htr_model.py
This intentionally does not place large model weights in the Git repository.
"""
from huggingface_hub import snapshot_download

from app.config import settings


def main() -> None:
    print(f"Downloading model assets for: {settings.htr_model_id}")
    print("The TrOCR base checkpoint is about 1.33 GB; ensure disk space and network access.")
    snapshot_path = snapshot_download(repo_id=settings.htr_model_id)
    print(f"Model cache ready: {snapshot_path}")
    print("You can now start the API; recognition will reuse the cached files.")


if __name__ == "__main__":
    main()
