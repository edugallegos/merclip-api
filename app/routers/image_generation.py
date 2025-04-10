import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from app.services.image_generator import generate_multiple_images, get_output_directory

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/images",
    tags=["image-generation"],
    responses={404: {"description": "Not found"}}
)

class ImagePrompt(BaseModel):
    prompt: str

class BatchImageGeneration(BaseModel):
    prompts: List[str]
    output_dir: Optional[str] = None  # Now optional, will use date-based directory by default

class ImageGenerationResult(BaseModel):
    prompt: str
    success: bool
    image_path: Optional[str] = None
    error: Optional[str] = None

@router.post("/generate", response_model=List[ImageGenerationResult])
async def generate_images(batch: BatchImageGeneration):
    """
    Generate images from a list of prompts using Gemini API.
    
    The images will be saved to a directory structure:
    /generated_images/YYYY-MM-DD/
    
    Files will be named sequentially (image_001.png, image_002.png, etc.)
    
    A custom output directory can be provided if desired.
    """
    try:
        logger.info(f"Generating images for {len(batch.prompts)} prompts")
        
        # Validate input
        if not batch.prompts:
            logger.warning("No prompts provided in request")
            raise HTTPException(status_code=400, detail="No prompts provided")
        
        # Check if API key is set in environment
        if not os.getenv("GEMINI_API_KEY"):
            logger.error("GEMINI_API_KEY environment variable not set")
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY environment variable not set"
            )
        
        # Get the output directory (for logging purposes)
        if batch.output_dir:
            output_dir = batch.output_dir
        else:
            output_dir = get_output_directory()
        logger.info(f"Images will be saved to: {output_dir}")
        
        # Generate the images
        results = await generate_multiple_images(
            prompts=batch.prompts,
            output_dir=batch.output_dir
        )
        
        # Log results
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"Image generation complete: {success_count}/{len(results)} successful")
        
        return results
    
    except Exception as e:
        logger.error(f"Error in image generation endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 