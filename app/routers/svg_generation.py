import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging
import replicate
import uuid

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/svg",
    tags=["svg-generation"],
    responses={404: {"description": "Not found"}}
)

class SVGGenerationRequest(BaseModel):
    prompts: List[str]

class SVGGenerationResult(BaseModel):
    prompt: str
    success: bool
    svg_path: Optional[str] = None
    error: Optional[str] = None

class SVGGenerationResponse(BaseModel):
    request_id: str
    results: List[SVGGenerationResult]
    output_directory: str

def get_output_directory(request_id: str):
    """Create and return an output directory structure using request ID"""
    parent_dir = os.path.join(os.getcwd(), "generated_images")
    os.makedirs(parent_dir, exist_ok=True)
    
    # Create request-specific directory
    output_dir = os.path.join(parent_dir, request_id)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

def generate_single_svg(prompt: str, output_dir: str, index: int) -> SVGGenerationResult:
    """Generate a single SVG image for a prompt"""
    try:
        # Configure Replicate
        replicate.api_token = os.getenv("REPLICATE_API_TOKEN")
        
        # Generate the SVG
        input = {
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "style": "vector_illustration/doodle_line_art",
        }
        
        output = replicate.run(
            "recraft-ai/recraft-20b-svg",
            input=input
        )
        
        # Save the SVG file with sequential numbering
        svg_path = os.path.join(output_dir, f"output_{index:03d}.svg")
        with open(svg_path, "wb") as file:
            file.write(output.read())
        
        logger.info(f"SVG saved successfully to {svg_path}")
        
        return SVGGenerationResult(
            prompt=prompt,
            success=True,
            svg_path=svg_path
        )
    
    except Exception as e:
        error_message = f"Error generating SVG: {str(e)}"
        logger.error(error_message)
        return SVGGenerationResult(
            prompt=prompt,
            success=False,
            error=error_message
        )

@router.post("/generate", response_model=SVGGenerationResponse)
async def generate_svgs(request: SVGGenerationRequest):
    """
    Generate SVG images from a list of prompts using Replicate's recraft-ai model.
    
    The SVGs will be saved to a directory structure:
    /generated_images/{request_id}/output_001.svg, output_002.svg, etc.
    """
    try:
        logger.info(f"Generating SVGs for {len(request.prompts)} prompts")
        
        # Validate input
        if not request.prompts:
            logger.warning("No prompts provided in request")
            raise HTTPException(status_code=400, detail="No prompts provided")
        
        # Check if API key is set in environment
        if not os.getenv("REPLICATE_API_TOKEN"):
            logger.error("REPLICATE_API_TOKEN environment variable not set")
            raise HTTPException(
                status_code=500,
                detail="REPLICATE_API_TOKEN environment variable not set"
            )
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        output_dir = get_output_directory(request_id)
        
        # Generate SVGs for each prompt
        results = []
        for i, prompt in enumerate(request.prompts):
            result = generate_single_svg(prompt, output_dir, i)
            results.append(result)
        
        # Log results
        success_count = sum(1 for r in results if r.success)
        logger.info(f"SVG generation complete: {success_count}/{len(results)} successful")
        
        return SVGGenerationResponse(
            request_id=request_id,
            results=results,
            output_directory=output_dir
        )
    
    except Exception as e:
        error_message = f"Error in SVG generation endpoint: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message) 