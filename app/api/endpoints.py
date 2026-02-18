from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import Response, JSONResponse
from typing import List
import io
import base64
import zipfile
import os
import torch
import logging
from PIL import Image

# Import from our new structure
from app.core.model import BackgroundRemover
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instance
bg_remover = None

def get_remover():
    global bg_remover
    if bg_remover is None:
        bg_remover = BackgroundRemover()
    return bg_remover

@router.get("/health")
async def health_check():
    remover = get_remover()
    status = {
        "status": "healthy",
        "model": settings.MODEL_ID,
        "device": str(remover.device),
        "cuda_available": torch.cuda.is_available()
    }
    logger.info(f"Health check: {status}")
    return status

@router.post("/remove-bg")
async def remove_background_endpoint(
    files: List[UploadFile] = File(...),
    return_mask: bool = False,
    output_format: str = "png"
):
    remover = get_remover()
    try:
        # Single file
        if len(files) == 1:
            file = files[0]
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))
            filename = file.filename
            
            logger.info(f"Processing single file: {filename}")

            if return_mask:
                result_image, mask_image = remover.remove_background(image, return_mask=True)
            else:
                result_image = remover.remove_background(image, return_mask=False)

            output = io.BytesIO()

            if output_format.lower() == "png":
                result_image.save(output, format="PNG")
                media_type = "image/png"
            elif output_format.lower() in ["jpg", "jpeg"]:
                bg = Image.new("RGB", result_image.size, (255, 255, 255))
                bg.paste(result_image, mask=result_image.split()[3])
                bg.save(output, format="JPEG")
                media_type = "image/jpeg"
            else:
                raise HTTPException(status_code=400, detail="Unsupported output format")

            output.seek(0)

            if return_mask:
                result_b64 = base64.b64encode(output.getvalue()).decode()

                mask_output = io.BytesIO()
                mask_image.save(mask_output, format="PNG")
                mask_output.seek(0)
                mask_b64 = base64.b64encode(mask_output.getvalue()).decode()

                return JSONResponse({
                    "result": result_b64,
                    "mask": mask_b64,
                    "format": output_format,
                    "filename": filename
                })
            else:
                return Response(content=output.getvalue(), media_type=media_type)
        
        # Batch processing (ZIP)
        else:
            logger.info(f"Processing batch of {len(files)} files")
            zip_output = io.BytesIO()
            with zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file in files:
                    contents = await file.read()
                    image = Image.open(io.BytesIO(contents))
                    filename = file.filename
                    base_name = os.path.splitext(filename)[0]

                    if return_mask:
                        result_image, mask_image = remover.remove_background(image, return_mask=True)
                    else:
                        result_image = remover.remove_background(image, return_mask=False)

                    # Save result image
                    img_output = io.BytesIO()
                    if output_format.lower() == "png":
                        result_image.save(img_output, format="PNG")
                        ext = "png"
                    elif output_format.lower() in ["jpg", "jpeg"]:
                        bg = Image.new("RGB", result_image.size, (255, 255, 255))
                        bg.paste(result_image, mask=result_image.split()[3])
                        bg.save(img_output, format="JPEG")
                        ext = "jpg"
                    else:
                        continue 
                    
                    zip_file.writestr(f"no_bg_{base_name}.{ext}", img_output.getvalue())

                    if return_mask:
                        mask_output = io.BytesIO()
                        mask_image.save(mask_output, format="PNG")
                        zip_file.writestr(f"mask_{base_name}.png", mask_output.getvalue())
            
            zip_output.seek(0)
            return Response(
                content=zip_output.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename=processed_images.zip"}
            )

    except Exception as e:
        logger.error(f"Error processing upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

from pydantic import BaseModel

class Base64Request(BaseModel):
    image_base64: str
    return_mask: bool = False
    output_format: str = "png"

@router.post("/remove-bg-base64")
async def remove_background_base64(req: Base64Request):
    image_base64 = req.image_base64
    return_mask = req.return_mask
    output_format = req.output_format
    remover = get_remover()
    try:
        # Check if base64 string has header, e.g. "data:image/png;base64,..."
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
            
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        logger.info("Processing base64 image")

        if return_mask:
            result_image, mask_image = remover.remove_background(image, return_mask=True)
        else:
            result_image = remover.remove_background(image, return_mask=False)

        output = io.BytesIO()

        if output_format.lower() == "png":
            result_image.save(output, format="PNG")
        elif output_format.lower() in ["jpg", "jpeg"]:
            bg = Image.new("RGB", result_image.size, (255, 255, 255))
            bg.paste(result_image, mask=result_image.split()[3])
            bg.save(output, format="JPEG")
        else:
            raise HTTPException(status_code=400, detail="Unsupported output format")

        output.seek(0)
        result_b64 = base64.b64encode(output.getvalue()).decode()

        response = {
            "result": result_b64,
            "format": output_format
        }

        if return_mask:
            mask_output = io.BytesIO()
            mask_image.save(mask_output, format="PNG")
            mask_output.seek(0)
            mask_b64 = base64.b64encode(mask_output.getvalue()).decode()
            response["mask"] = mask_b64

        return JSONResponse(response)

    except Exception as e:
        logger.error(f"Error processing base64 image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
