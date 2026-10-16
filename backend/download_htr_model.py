"""Download the configured pretrained English HTR model.

Run from the backend directory:
    py download_htr_model.py

If WRITLYNX_HTR_MODEL_PATH is set in .env, model assets are downloaded there.
Otherwise, they are stored in the normal Hugging Face cache. Model weights are
not added to the Git repository.
"""
from pathlib import Path

from huggingface_hub import snapshot_download

from app.config import settings


def main() -> None:
    print(f"Downloading model assets for: {settings.htr_model_id}")
    print("The safetensors checkpoint is about 1.33 GB. Ensure disk space and network access.")
    print("Only safetensors weights and required tokenizer/processor files will be cached.")
    download_args = {
        "repo_id": settings.htr_model_id,
        "allow_patterns": [
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
    }
    target = settings.htr_model_path.strip()
    if target:
        local_dir = Path(target).expanduser()
        local_dir.mkdir(parents=True, exist_ok=True)
        download_args["local_dir"] = str(local_dir)
        print(f"Saving model files to: {local_dir}")
    else:
        print("Saving model files to the default Hugging Face cache.")

    model_path = snapshot_download(**download_args)
    print(f"Model files ready: {model_path}")
    print("Restart the backend after downloading; the recognizer will load from this location.")


if __name__ == "__main__":
    main()
