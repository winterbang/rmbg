import torch
from PIL import Image
import numpy as np
from torchvision import transforms
from huggingface_hub import hf_hub_download
from transformers import AutoConfig, AutoModelForImageSegmentation
from safetensors.torch import load_file
import os

class BackgroundRemover:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        self.model = self._load_model()
        
    def _load_model(self):
        print("Loading RMBG-2.0 model...")
        try:
            # Prevent meta tensors issues by environment variable if needed, 
            # though usually handled by transformers now.
            # os.environ["TRANSFORMERS_NO_META_DEVICE"] = "1"
            
            config = AutoConfig.from_pretrained("briaai/RMBG-2.0", trust_remote_code=True)
            model = AutoModelForImageSegmentation.from_config(config, trust_remote_code=True)
            
            # Load weights manually to ensure safe tensors loading
            model_path = hf_hub_download(repo_id="briaai/RMBG-2.0", filename="model.safetensors")
            state_dict = load_file(model_path)
            model.load_state_dict(state_dict, strict=True)
            
            model.to(self.device)
            model.eval()
            print("Model loaded successfully!")
            return model
            
        except Exception as e:
            print(f"Failed to load model manually: {e}")
            print("Trying pipeline method...")
            from transformers import pipeline
            pipe = pipeline("image-segmentation", model="briaai/RMBG-2.0", trust_remote_code=True, device=0 if torch.cuda.is_available() else -1)
            return pipe.model

    def preprocess_image(self, image, input_size=(1024, 1024)):
        """Preprocess input image - Standard Resize"""
        image = image.convert("RGB")
        
        # Space uses simple resize, no letterbox
        transform = transforms.Compose([
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        return transform(image).unsqueeze(0).to(self.device)

    def postprocess_mask(self, mask, original_size):
        """Postprocess predicted mask - Match Official Space"""
        # mask is tensor (1024, 1024) range 0-1
        
        # Use ToPILImage to handle 0-1 to 0-255 conversion correctly
        pred_pil = transforms.ToPILImage()(mask)
        
        # Resize back to original size
        # Space uses default resize (BILINEAR), we can use BICUBIC for slightly better edges
        mask_image = pred_pil.resize(original_size, Image.BILINEAR)
        return mask_image

    def remove_background(self, image, return_mask=False):
        """Remove background from image"""
        if not isinstance(image, Image.Image):
             image = Image.open(image)
             
        original_size = image.size # Width, Height
        input_tensor = self.preprocess_image(image)

        with torch.no_grad():
            preds = self.model(input_tensor)
        
        # Handle output types to match space app usage: preds[-1]
        if isinstance(preds, (list, tuple)):
            print(f"DEBUG: Output is list/tuple of length {len(preds)}")
            # Official space uses the LAST element [-1]
            preds = preds[-1]
        elif hasattr(preds, 'logits'):
            preds = preds.logits
            
        # Apply sigmoid (as in space app)
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
