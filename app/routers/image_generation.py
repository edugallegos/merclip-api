import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
from app.services.image_generator import generate_multiple_images

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

class ImageGenerationResult(BaseModel):
    prompt: str
    success: bool
    image_path: Optional[str] = None
    error: Optional[str] = None

class BatchGenerationResponse(BaseModel):
    request_id: str
    results: List[ImageGenerationResult]
    output_directory: str

@router.post("/generate", response_model=BatchGenerationResponse)
async def generate_images(batch: BatchImageGeneration):
    """
    Generate images from a list of prompts using Gemini API.
    
    The images will be saved to a directory structure:
    /generated_images/{request_id}/
    
    Files will be named sequentially (image_001.png, image_002.png, etc.)
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
        
        # Generate the images
        result = await generate_multiple_images(prompts=batch.prompts)
        
        # Log results
        success_count = sum(1 for r in result["results"] if r["success"])
        logger.info(f"Image generation complete: {success_count}/{len(result['results'])} successful")
        
        return BatchGenerationResponse(
            request_id=result["request_id"],
            results=result["results"],
            output_directory=result["output_directory"]
        )
    
    except Exception as e:
        logger.error(f"Error in image generation endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 