import logging
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from huggingface_hub import hf_hub_download
from transformers import AutoConfig, AutoModelForImageSegmentation
from safetensors.torch import load_file
from typing import Tuple, Union, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class BackgroundRemover:
    def __init__(self):
        self.device = torch.device(settings.DEVICE)
        logger.info(f"Using device: {self.device}")
        
        self.model = self._load_model()
        
    def _load_model(self):
        logger.info(f"Loading {settings.MODEL_ID} model...")
        try:
            config = AutoConfig.from_pretrained(settings.MODEL_ID, trust_remote_code=True)
            model = AutoModelForImageSegmentation.from_config(config, trust_remote_code=True)
            
            # Load weights manually to ensure safe tensors loading
            model_path = hf_hub_download(repo_id=settings.MODEL_ID, filename="model.safetensors")
            state_dict = load_file(model_path)
            model.load_state_dict(state_dict, strict=True)
            
            model.to(self.device)
            model.eval()
            logger.info("Model loaded successfully!")
            return model
            
        except Exception as e:
            logger.warning(f"Failed to load model manually: {e}. Trying pipeline method...")
            from transformers import pipeline
            pipe = pipeline("image-segmentation", model=settings.MODEL_ID, trust_remote_code=True, device=0 if self.device.type == "cuda" else -1)
            return pipe.model

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
