import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import replicate
import uuid
import json
import shutil
from lxml import etree
from PIL import Image
import subprocess
import io

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

class FrameConfig(BaseModel):
    id: str
    duration: float

class FrameGenerationRequest(BaseModel):
    request_id: str
    frames: List[FrameConfig]
    config: Optional[Dict] = None

class FrameGenerationResult(BaseModel):
    id: str
    success: bool
    frames_path: Optional[str] = None
    error: Optional[str] = None

class FrameGenerationResponse(BaseModel):
    request_id: str
    results: List[FrameGenerationResult]
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

def parse_color(color_str: str) -> str:
    """Parse color string to hex format"""
    if color_str.startswith("#"):
        return color_str
    elif color_str.startswith("rgb("):
        rgb_values = color_str[4:-1].split(",")
        r, g, b = map(int, rgb_values)
        return f"#{r:02x}{g:02x}{b:02x}"
    else:
        return color_str

def interpolate_color(from_color: str, to_color: str, progress: float) -> str:
    """Interpolate between two colors based on progress (0-1)"""
    from_r = int(from_color[1:3], 16)
    from_g = int(from_color[3:5], 16)
    from_b = int(from_color[5:7], 16)
    
    to_r = int(to_color[1:3], 16)
    to_g = int(to_color[3:5], 16)
    to_b = int(to_color[5:7], 16)
    
    r = int(from_r + (to_r - from_r) * progress)
    g = int(from_g + (to_g - from_g) * progress)
    b = int(from_b + (to_b - from_b) * progress)
    
    return f"#{r:02x}{g:02x}{b:02x}"

def load_svg(svg_path: str) -> etree._ElementTree:
    """Load SVG file and return its tree"""
    return etree.parse(svg_path)

def save_svg(svg_tree: etree._ElementTree, output_path: str):
    """Save SVG tree to file"""
    svg_tree.write(output_path, pretty_print=True)

def svg_to_png(svg_path: str, output_path: str, width: int, height: int):
    """Convert SVG to PNG with specified dimensions using rsvg-convert"""
    try:
        subprocess.run([
            "rsvg-convert",
            svg_path,
            "-w", str(width),
            "-h", str(height),
            "-o", output_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting SVG to PNG: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error converting SVG to PNG: {str(e)}")
        raise

def apply_global_color_morph(svg_tree, from_color, to_color, frame, total_frames):
    """Apply color morphing to SVG elements"""
    progress = frame / total_frames

    for elem in svg_tree.iter():
        fill = elem.get("fill")
        if fill:
            current_color = parse_color(fill)
            if current_color.startswith("#") and current_color != "#fefefe":
                new_color = interpolate_color(from_color, to_color, progress)
                elem.set("fill", new_color)

def apply_sequential_reveal(svg_tree, frame, total_frames):
    """Apply sequential reveal animation to SVG elements"""
    paths = [elem for elem in svg_tree.iter() if elem.tag.endswith('path') and 
             elem.get("fill") != "rgb(254,254,254)"]
    
    total_shapes = len(paths)
    shapes_per_frame = total_shapes / total_frames
    visible_shapes = int(frame * shapes_per_frame)
    
    for path in paths:
        path.set("opacity", "0")
    
    for i in range(visible_shapes):
        if i < len(paths):
            paths[i].set("opacity", "1")

def generate_frames_for_svg(svg_path: str, output_dir: str, duration: float, config: Dict) -> bool:
    """Generate frames for a single SVG"""
    try:
        # Default configuration
        default_config = {
            "from": "#000000",
            "to": "#ff0000",
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "animation": "color"
        }
        
        # Merge with provided config
        merged_config = {**default_config, **(config or {})}
        
        from_color = parse_color(merged_config["from"])
        to_color = parse_color(merged_config["to"])
        fps = merged_config["fps"]
        width = merged_config["width"]
        height = merged_config["height"]
        animation = merged_config["animation"]
        
        total_frames = round(duration * fps)
        
        for frame in range(total_frames):
            svg_tree = load_svg(svg_path)
            
            if animation in ['color', 'both']:
                apply_global_color_morph(svg_tree, from_color, to_color, frame, total_frames)
            
            if animation in ['reveal', 'both']:
                apply_sequential_reveal(svg_tree, frame, total_frames)
            
            tmp_svg = os.path.join(output_dir, 'tmp.svg')
            save_svg(svg_tree, tmp_svg)
            output_path = os.path.join(output_dir, f'frame_{frame:04d}.png')
            svg_to_png(tmp_svg, output_path, width, height)
        
        # Clean up temporary file
        if os.path.exists(tmp_svg):
            os.remove(tmp_svg)
        
        return True
    
    except Exception as e:
        logger.error(f"Error generating frames: {str(e)}")
        return False

@router.post("/generate-frames", response_model=FrameGenerationResponse)
async def generate_svg_frames(request: FrameGenerationRequest):
    """
    Generate frames from existing SVGs using the provided request_id and durations.
    
    The frames will be saved to a directory structure:
    /generated_images/{request_id}/frames_{id}/frame_0000.png, frame_0001.png, etc.
    """
    try:
        logger.info(f"Generating frames for request_id: {request.request_id}")
        
        # Validate input
        if not request.frames:
            logger.warning("No frames configuration provided")
            raise HTTPException(status_code=400, detail="No frames configuration provided")
        
        # Get the base directory for the request
        base_dir = os.path.join(os.getcwd(), "generated_images", request.request_id)
        if not os.path.exists(base_dir):
            raise HTTPException(status_code=404, detail="Request ID not found")
        
        results = []
        for frame_config in request.frames:
            # Find the corresponding SVG file
            svg_path = os.path.join(base_dir, f"output_{frame_config.id}.svg")
            if not os.path.exists(svg_path):
                results.append(FrameGenerationResult(
                    id=frame_config.id,
                    success=False,
                    error=f"SVG file not found for id {frame_config.id}"
                ))
                continue
            
            # Create frames directory
            frames_dir = os.path.join(base_dir, f"frames_{frame_config.id}")
            os.makedirs(frames_dir, exist_ok=True)
            
            # Generate frames
            success = generate_frames_for_svg(
                svg_path=svg_path,
                output_dir=frames_dir,
                duration=frame_config.duration,
                config=request.config
            )
            
            results.append(FrameGenerationResult(
                id=frame_config.id,
                success=success,
                frames_path=frames_dir if success else None,
                error=None if success else "Failed to generate frames"
            ))
        
        return FrameGenerationResponse(
            request_id=request.request_id,
            results=results,
            output_directory=base_dir
        )
    
    except Exception as e:
        error_message = f"Error in frame generation endpoint: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message) 