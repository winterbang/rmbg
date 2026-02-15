import os
import torch

class Settings:
    PROJECT_NAME: str = "RMBG-2.0 Service"
    API_V1_STR: str = "/api/v1"
    MODEL_ID: str = "briaai/RMBG-2.0"
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

settings = Settings()
