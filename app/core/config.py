import os

class Settings:
    PROJECT_NAME: str = "RMBG-2.0 Service"
    API_V1_STR: str = "/api/v1"
    MODEL_ID: str = "briaai/RMBG-2.0"
    DEVICE: str = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"

settings = Settings()
