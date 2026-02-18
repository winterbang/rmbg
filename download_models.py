#!/usr/bin/env python3
"""
Download RMBG-2.0 model files for offline bundling
"""

import os
from pathlib import Path
from huggingface_hub import hf_hub_download

MODEL_ID = "briaai/RMBG-2.0"
LOCAL_MODEL_DIR = Path(__file__).parent / "models" / "RMBG-2.0"

# Files to download
FILES_TO_DOWNLOAD = [
    "config.json",
    "BiRefNet_config.py", 
    "birefnet.py",
    "model.safetensors"
]

def download_model_files():
    """Download all required model files to local directory"""
    LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading {MODEL_ID} to {LOCAL_MODEL_DIR}")
    print("This may take a few minutes (~176MB)...\n")
    
    for filename in FILES_TO_DOWNLOAD:
        print(f"Downloading {filename}...")
        try:
            downloaded_path = hf_hub_download(
                repo_id=MODEL_ID,
                filename=filename,
                local_dir=LOCAL_MODEL_DIR,
                local_dir_use_symlinks=False
            )
            print(f"✓ {filename} downloaded to {downloaded_path}\n")
        except Exception as e:
            print(f"✗ Failed to download {filename}: {e}\n")
            return False
    
    print(f"\n✅ All model files downloaded successfully!")
    print(f"📁 Location: {LOCAL_MODEL_DIR.absolute()}")
    print(f"📦 Total size: ~176MB")
    return True

if __name__ == "__main__":
    success = download_model_files()
    exit(0 if success else 1)
