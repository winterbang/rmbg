import logging
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from torchvision import transforms
from huggingface_hub import hf_hub_download
from transformers import AutoConfig, AutoModelForImageSegmentation
from safetensors.torch import load_file
from typing import Tuple, Union, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

import sys
import sys
import os

# Bundled model directory (for offline operation)
if getattr(sys, 'frozen', False):
    # Frozen (PyInstaller)
    base_candidates = []
    
    # Candidate 1: sys._MEIPASS (PyInstaller temp/resource folder)
    if hasattr(sys, '_MEIPASS'):
        base_candidates.append(Path(sys._MEIPASS))
        
    # Candidate 2: Executable directory (Contents/MacOS)
    exe_path = Path(sys.executable).parent
    base_candidates.append(exe_path)
    
    # Candidate 3: macOS Bundle Resources (Contents/Resources)
    # exe is in .../Contents/MacOS/NoBG -> .../Contents/Resources
    base_candidates.append(exe_path.parent / "Resources")
    
    BASE_DIR = None
    BUNDLED_MODEL_DIR = None

    for base in base_candidates:
        candidate = base / "models" / "RMBG-2.0"
        if candidate.exists():
            BASE_DIR = base
            BUNDLED_MODEL_DIR = candidate
            break
            
    if BUNDLED_MODEL_DIR is None:
        # Fallback to first candidate if none found (will likely fail but keep structure)
        BASE_DIR = base_candidates[0] if base_candidates else Path(".")
        BUNDLED_MODEL_DIR = BASE_DIR / "models" / "RMBG-2.0"

else:
    # Development (Script)
    BASE_DIR = Path(__file__).parent.parent.parent
    BUNDLED_MODEL_DIR = BASE_DIR / "models" / "RMBG-2.0"

class BackgroundRemover:
    def __init__(self, progress_callback=None):
        self.device = torch.device(settings.DEVICE)
        logger.info(f"Using device: {self.device}")
        
        self.progress_callback = progress_callback
        self.model = self._load_model()
        
    def _load_model(self):
        logger.info(f"Loading {settings.MODEL_ID} model...")
        
        # Check if bundled model exists
        bundled_weights = BUNDLED_MODEL_DIR / "model.safetensors"
        use_bundled = bundled_weights.exists()
        
        if use_bundled:
            logger.info(f"Using bundled model from {BUNDLED_MODEL_DIR}")
        else:
            logger.info("Bundled model not found, will download from HuggingFace")
        
        try:
            # Load configuration
            if self.progress_callback:
                msg = "Loading configuration..." if use_bundled else "Downloading configuration..."
                self.progress_callback(0.1, msg)
            
            if use_bundled:
                config = AutoConfig.from_pretrained(
                    str(BUNDLED_MODEL_DIR),
                    trust_remote_code=True,
                    local_files_only=True
                )
            else:
                config = AutoConfig.from_pretrained(
                    settings.MODEL_ID,
                    trust_remote_code=True
                )
            
            # Create model architecture
            if self.progress_callback:
                self.progress_callback(0.3, "Creating model architecture...")
            model = AutoModelForImageSegmentation.from_config(config, trust_remote_code=True)
            
            # Load weights
            if self.progress_callback:
                msg = "Loading model weights..." if use_bundled else "Downloading model weights..."
                self.progress_callback(0.5, msg)
            
            if use_bundled:
                model_path = bundled_weights
            else:
                model_path = hf_hub_download(
                    repo_id=settings.MODEL_ID,
                    filename="model.safetensors"
                )
            
            if self.progress_callback:
                self.progress_callback(0.7, "Loading weights into model...")
            state_dict = load_file(str(model_path))
            model.load_state_dict(state_dict, strict=True)
            
            # Transfer to device
            if self.progress_callback:
                self.progress_callback(0.9, "Transferring to device...")
            model.to(self.device)
            model.eval()
            
            if self.progress_callback:
                self.progress_callback(1.0, "Ready!")
            logger.info("Model loaded successfully!")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Could not load RMBG-2.0 model: {e}")

    def preprocess_image(self, image: Image.Image, input_size: Tuple[int, int] = (1024, 1024)) -> torch.Tensor:
        """Preprocess input image - Standard Resize"""
        image = image.convert("RGB")
        
        transform = transforms.Compose([
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        return transform(image).unsqueeze(0).to(self.device)

    def postprocess_mask(self, mask: torch.Tensor, original_size: Tuple[int, int]) -> Image.Image:
        """Postprocess predicted mask"""
        # mask is tensor (1024, 1024) range 0-1
        
        # Use ToPILImage to handle 0-1 to 0-255 conversion correctly
        pred_pil = transforms.ToPILImage()(mask)
        
        # Resize back to original size using BICUBIC for better edges
        mask_image = pred_pil.resize(original_size, Image.BILINEAR)
        return mask_image

    def remove_background(self, image: Union[Image.Image, str], return_mask: bool = False) -> Union[Image.Image, Tuple[Image.Image, Image.Image]]:
        """Remove background from image"""
        if not isinstance(image, Image.Image):
             image = Image.open(image)
             
        original_size = image.size # Width, Height
        input_tensor = self.preprocess_image(image)

        with torch.no_grad():
            preds = self.model(input_tensor)
        
        # Handle output types to match space app usage: preds[-1]
        if isinstance(preds, (list, tuple)):
            # Official space uses the LAST element [-1]
            preds = preds[-1]
        elif hasattr(preds, 'logits'):
            preds = preds.logits
            
        # Apply sigmoid
        preds = preds.sigmoid().cpu()
        
        # Squeeze to get (H, W) or (C, H, W)
        pred = preds[0].squeeze()

        # preds is the mask
        mask_image = self.postprocess_mask(pred, original_size)
        
        result_image = image.convert("RGBA")
        result_image.putalpha(mask_image)

        if return_mask:
            return result_image, mask_image
        return result_image
