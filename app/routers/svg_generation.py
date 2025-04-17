import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
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
import asyncio
from app.services.job_status import JobStatus, JobStatusManager, FrameResult
from fastapi.responses import FileResponse

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
    job_id: str
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
    job_id: str
    results: List[FrameGenerationResult]
    output_directory: str

class VideoGenerationRequest(BaseModel):
    request_id: str
    fps: Optional[int] = 30

class VideoGenerationResponse(BaseModel):
    request_id: str
    job_id: str
    output_directory: str

class CombinedVideoGenerationRequest(BaseModel):
    request_id: str
    fps: Optional[int] = 30
    transition_duration: Optional[float] = 0.5  # Duration of transition between sequences in seconds

class CombinedVideoGenerationResponse(BaseModel):
    request_id: str
    job_id: str
    output_directory: str

# Initialize job status manager
job_status_manager = JobStatusManager()

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

async def process_svg_generation(
    job_id: str,
    request_id: str,
    prompts: List[str],
    output_dir: str
) -> None:
    """Process SVG generation for all prompts in the background"""
    try:
        logger.info(f"Starting SVG generation for job {job_id}")
        
        # Generate SVGs for each prompt
        for i, prompt in enumerate(prompts):
            logger.info(f"Processing prompt {i+1}/{len(prompts)}")
            result = await asyncio.to_thread(
                generate_single_svg,
                prompt=prompt,
                output_dir=output_dir,
                index=i
            )
            
            # Update job status with result
            frame_result = FrameResult(
                id=str(i),
                success=result.success,
                error=result.error
            )
            job_status_manager.update_job(job_id, frame_result)
        
        logger.info("All SVGs generated successfully")
        job_status_manager.update_job_status(job_id, "completed")
            
    except Exception as e:
        error_msg = f"Error in SVG generation: {str(e)}"
        logger.error(error_msg)
        job_status_manager.set_job_error(job_id, error_msg)

@router.post("/generate", response_model=SVGGenerationResponse)
async def generate_svgs(
    request: SVGGenerationRequest,
    background_tasks: BackgroundTasks
):
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
        
        # Create a job ID for tracking
        job_id = str(uuid.uuid4())
        logger.info(f"Created job_id: {job_id}")
        
        # Initialize job status
        job_status_manager.create_job(job_id, request_id, len(request.prompts))
        logger.info(f"Initialized job status for {len(request.prompts)} prompts")
        
        # Create response
        response = SVGGenerationResponse(
            request_id=request_id,
            job_id=job_id,
            output_directory=output_dir
        )
        
        # Add background task
        logger.info("Adding background task for SVG generation")
        background_tasks.add_task(
            process_svg_generation,
            job_id=job_id,
            request_id=request_id,
            prompts=request.prompts,
            output_dir=output_dir
        )
        
        logger.info("Background task added, returning response")
        return response
        
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
            "animation": "color",
            "hold_duration": 1.5  # Duration to hold the complete image at the end
        }
        
        # Merge with provided config
        merged_config = {**default_config, **(config or {})}
        
        from_color = parse_color(merged_config["from"])
        to_color = parse_color(merged_config["to"])
        fps = merged_config["fps"]
        width = merged_config["width"]
        height = merged_config["height"]
        animation = merged_config["animation"]
        hold_duration = merged_config["hold_duration"]
        
        # Calculate total frames
        total_frames = round(duration * fps)
        hold_frames = round(hold_duration * fps)
        animation_frames = total_frames - hold_frames

        # Ensure animation_frames is not negative
        if animation_frames < 0:
            animation_frames = 0
            hold_frames = total_frames
        
        logger.info(f"Generating {total_frames} frames: {animation_frames} animation frames + {hold_frames} hold frames")
        
        # Load the original SVG and get all elements
        original_svg = load_svg(svg_path)
        elements = [elem for elem in original_svg.iter() if elem.tag.endswith('path') and elem.get("fill") != "rgb(254,254,254)"]
        total_elements = len(elements)
        logger.info(f"Found {total_elements} elements in SVG")
        
        # Generate animation frames only if animation_frames > 0
        if animation_frames > 0:
            # Calculate elements per frame
            elements_per_frame = total_elements / animation_frames
            logger.info(f"Elements per frame: {elements_per_frame}")

            for frame in range(animation_frames):
                svg_tree = load_svg(svg_path)
                visible_elements = int(frame * elements_per_frame)
                
                # Process each element
                for i, elem in enumerate(svg_tree.iter()):
                    if elem.tag.endswith('path') and elem.get("fill") != "rgb(254,254,254)":
                        # Set visibility based on frame
                        if i < visible_elements:
                            elem.set("opacity", "1")
                            if animation in ['color', 'both']:
                                # Calculate color progress
                                color_progress = min(1.0, i / total_elements)
                                new_color = interpolate_color(from_color, to_color, color_progress)
                                elem.set("fill", new_color)
                        else:
                            elem.set("opacity", "0")
                
                tmp_svg = os.path.join(output_dir, 'tmp.svg')
                save_svg(svg_tree, tmp_svg)
                output_path = os.path.join(output_dir, f'frame_{frame:04d}.png')
                svg_to_png(tmp_svg, output_path, width, height)
        else:
            logger.info("Skipping animation frames generation as animation_frames is 0 or less.")
        
        # Generate hold frames (complete image without changes)
        logger.info(f"Generating {hold_frames} hold frames")
        for frame in range(hold_frames):
            # Use the last animation frame as the base for hold frames
            svg_tree = load_svg(svg_path)
            
            # Make all elements visible with final color
            for elem in svg_tree.iter():
                if elem.tag.endswith('path') and elem.get("fill") != "rgb(254,254,254)":
                    elem.set("opacity", "1")
                    if animation in ['color', 'both']:
                        elem.set("fill", to_color)
            
            tmp_svg = os.path.join(output_dir, 'tmp.svg')
            save_svg(svg_tree, tmp_svg)
            # Adjust frame numbering if there were no animation frames
            frame_index = frame if animation_frames <= 0 else frame + animation_frames
            output_path = os.path.join(output_dir, f'frame_{frame_index:04d}.png')
            svg_to_png(tmp_svg, output_path, width, height)
        
        # Clean up temporary file
        if os.path.exists(tmp_svg):
            os.remove(tmp_svg)
        
        logger.info(f"Successfully generated {total_frames} frames")
        return True
    
    except Exception as e:
        logger.error(f"Error generating frames: {str(e)}")
        return False

@router.post("/generate-frames", response_model=FrameGenerationResponse)
async def generate_svg_frames(
    request: FrameGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate frames from existing SVGs using the provided request_id and durations.
    The frames will be saved to a directory structure:
    /generated_images/{request_id}/frames_{id}/frame_0000.png, frame_0001.png, etc.
    """
    try:
        logger.info(f"Starting frame generation for request_id: {request.request_id}")
        
        # Validate input
        if not request.frames:
            logger.warning("No frames configuration provided")
            raise HTTPException(status_code=400, detail="No frames configuration provided")
        
        # Get the base directory for the request
        base_dir = os.path.join(os.getcwd(), "generated_images", request.request_id)
        if not os.path.exists(base_dir):
            logger.error(f"Base directory not found: {base_dir}")
            raise HTTPException(status_code=404, detail="Request ID not found")
        
        # Create a job ID for tracking
        job_id = str(uuid.uuid4())
        logger.info(f"Created job_id: {job_id}")
        
        # Initialize job status
        job_status_manager.create_job(job_id, request.request_id, len(request.frames))
        logger.info(f"Initialized job status for {len(request.frames)} frames")
        
        # Create response first
        response = {
            "request_id": request.request_id,
            "job_id": job_id,
            "results": [],
            "output_directory": base_dir
        }
        
        # Add background tasks for each frame
        for frame_config in request.frames:
            logger.info(f"Adding background task for frame {frame_config.id}")
            background_tasks.add_task(
                process_frame_generation,
                job_id=job_id,
                request_id=request.request_id,
                frame_config=frame_config,
                config=request.config,
                base_dir=base_dir
            )
        
        logger.info("All background tasks added, returning response")
        # Return immediately with job_id
        return response
    
    except Exception as e:
        error_message = f"Error in frame generation endpoint: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

async def process_frame_generation(
    job_id: str,
    request_id: str,
    frame_config: FrameConfig,
    config: Optional[Dict],
    base_dir: str
) -> None:
    """Process frame generation for a single SVG in the background"""
    try:
        logger.info(f"Starting frame generation for job {job_id}, frame {frame_config.id}")
        
        # Find the corresponding SVG file
        svg_path = os.path.join(base_dir, f"output_{frame_config.id}.svg")
        logger.info(f"Looking for SVG file at: {svg_path}")
        
        if not os.path.exists(svg_path):
            logger.error(f"SVG file not found: {svg_path}")
            result = FrameResult(
                id=frame_config.id,
                success=False,
                error=f"SVG file not found for id {frame_config.id}"
            )
            job_status_manager.update_job(job_id, result)
            return
        
        # Create frames directory (remove if exists)
        frames_dir = os.path.join(base_dir, f"frames_{frame_config.id}")
        logger.info(f"Processing frames directory: {frames_dir}")
        
        if os.path.exists(frames_dir):
            logger.info(f"Removing existing frames directory: {frames_dir}")
            await asyncio.to_thread(shutil.rmtree, frames_dir)
        
        logger.info(f"Creating new frames directory: {frames_dir}")
        await asyncio.to_thread(os.makedirs, frames_dir, exist_ok=True)
        
        # Generate frames
        logger.info(f"Starting frame generation for SVG: {svg_path}")
        success = await asyncio.to_thread(
            generate_frames_for_svg,
            svg_path=svg_path,
            output_dir=frames_dir,
            duration=frame_config.duration,
            config=config
        )
        
        logger.info(f"Frame generation completed with success={success}")
        result = FrameResult(
            id=frame_config.id,
            success=success,
            frames_path=frames_dir if success else None,
            error=None if success else "Failed to generate frames"
        )
        
        job_status_manager.update_job(job_id, result)
        logger.info(f"Updated job status for frame {frame_config.id}")
        
    except Exception as e:
        logger.error(f"Error processing frame generation: {str(e)}")
        result = FrameResult(
            id=frame_config.id,
            success=False,
            error=str(e)
        )
        job_status_manager.update_job(job_id, result)
        logger.error(f"Updated job status with error for frame {frame_config.id}")

@router.get("/job-status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a background job"""
    job_status = job_status_manager.get_job(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_status

def generate_video_from_frames(frames_dir: str, output_path: str, fps: int) -> bool:
    """Generate a video from a sequence of frames using ffmpeg"""
    try:
        # Construct ffmpeg command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if exists
            "-framerate", str(fps),
            "-i", os.path.join(frames_dir, "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",  # Required for compatibility
            "-preset", "medium",  # Balance between speed and compression
            "-crf", "23",  # Quality setting (0-51, lower is better)
            output_path
        ]
        
        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        return False

async def process_video_generation(
    job_id: str,
    request_id: str,
    base_dir: str,
    fps: int
) -> None:
    """Process video generation for all frame sequences in the background"""
    try:
        logger.info(f"Starting video generation for job {job_id}")
        
        # Create videos directory
        videos_dir = os.path.join(base_dir, "videos")
        await asyncio.to_thread(os.makedirs, videos_dir, exist_ok=True)
        
        # Find all frames_XXX directories
        frame_dirs = [d for d in os.listdir(base_dir) if d.startswith("frames_")]
        
        if not frame_dirs:
            logger.error("No frame directories found")
            job_status_manager.set_job_error(job_id, "No frame directories found")
            return
        
        total_success = True
        for frame_dir in frame_dirs:
            frames_path = os.path.join(base_dir, frame_dir)
            sequence_id = frame_dir.replace("frames_", "")
            output_path = os.path.join(videos_dir, f"video_{sequence_id}.mp4")
            
            logger.info(f"Generating video for sequence {sequence_id}")
            success = await asyncio.to_thread(
                generate_video_from_frames,
                frames_path,
                output_path,
                fps
            )
            
            if not success:
                total_success = False
                logger.error(f"Failed to generate video for sequence {sequence_id}")
        
        if total_success:
            logger.info("All videos generated successfully")
            job_status_manager.update_job_status(job_id, "completed")
        else:
            logger.error("Some videos failed to generate")
            job_status_manager.set_job_error(job_id, "Some videos failed to generate")
            
    except Exception as e:
        error_msg = f"Error in video generation: {str(e)}"
        logger.error(error_msg)
        job_status_manager.set_job_error(job_id, error_msg)

@router.post("/generate-videos", response_model=VideoGenerationResponse)
async def generate_videos(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate videos from frame sequences in frames_XXX folders.
    The videos will be saved to:
    /generated_images/{request_id}/videos/video_XXX.mp4
    """
    try:
        logger.info(f"Starting video generation for request_id: {request.request_id}")
        
        # Get the base directory for the request
        base_dir = os.path.join(os.getcwd(), "generated_images", request.request_id)
        if not os.path.exists(base_dir):
            logger.error(f"Base directory not found: {base_dir}")
            raise HTTPException(status_code=404, detail="Request ID not found")
        
        # Create a job ID for tracking
        job_id = str(uuid.uuid4())
        logger.info(f"Created job_id: {job_id}")
        
        # Initialize job status
        job_status_manager.create_job(job_id, request.request_id, 1)  # Single job for all videos
        logger.info("Initialized job status")
        
        # Create response
        response = {
            "request_id": request.request_id,
            "job_id": job_id,
            "output_directory": os.path.join(base_dir, "videos")
        }
        
        # Add background task
        logger.info("Adding background task for video generation")
        background_tasks.add_task(
            process_video_generation,
            job_id=job_id,
            request_id=request.request_id,
            base_dir=base_dir,
            fps=request.fps
        )
        
        logger.info("Background task added, returning response")
        return response
        
    except Exception as e:
        error_message = f"Error in video generation endpoint: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

def generate_combined_video(frames_dirs: List[str], output_path: str, fps: int, transition_duration: float) -> bool:
    """Generate a single video combining all frame sequences"""
    try:
        logger.info(f"Starting combined video generation with {len(frames_dirs)} frame directories")
        logger.info(f"FPS: {fps}")
        
        # Create a temporary directory for the concatenated frames
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_frames")
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Created temporary directory: {temp_dir}")
        
        # Sort frame directories numerically
        def get_frame_number(dir_path):
            dir_name = os.path.basename(dir_path)
            return int(dir_name.replace("frames_", ""))
        
        sorted_frames_dirs = sorted(frames_dirs, key=get_frame_number)
        logger.info(f"Sorted frame directories: {[os.path.basename(d) for d in sorted_frames_dirs]}")
        
        # Process each sequence and copy frames to temp directory
        all_frames = []
        frame_count = 0
        for i, frames_dir in enumerate(sorted_frames_dirs):
            logger.info(f"Processing sequence {i+1} from directory: {frames_dir}")
            
            # Get all frames in the directory and sort them
            frames = sorted([f for f in os.listdir(frames_dir) if f.startswith('frame_') and f.endswith('.png')])
            logger.info(f"Found {len(frames)} frames in sequence {i+1}")
            
            # Copy frames to temp directory with new sequential numbering
            for frame in frames:
                frame_path = os.path.join(frames_dir, frame)
                new_frame_name = f"frame_{frame_count:04d}.png"
                new_frame_path = os.path.join(temp_dir, new_frame_name)
                shutil.copy2(frame_path, new_frame_path)
                all_frames.append(new_frame_path)
                frame_count += 1
                logger.debug(f"Copied frame: {frame_path} -> {new_frame_path}")
        
        logger.info(f"Total frames in final video: {len(all_frames)}")
        
        # Use ffmpeg to create the final video
        cmd = [
            "ffmpeg",
            "-y",
            "-framerate", str(fps),
            "-i", os.path.join(temp_dir, "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "23",
            output_path
        ]
        
        logger.info("Starting final video generation with ffmpeg")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary files
        shutil.rmtree(temp_dir)
        logger.info("Cleaned up temporary files")
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
        logger.info(f"Successfully generated combined video: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error generating combined video: {str(e)}")
        return False

async def process_combined_video_generation(
    job_id: str,
    request_id: str,
    base_dir: str,
    fps: int,
    transition_duration: float
) -> None:
    """Process combined video generation in the background"""
    try:
        logger.info(f"Starting combined video generation for job {job_id}")
        
        # Create videos directory
        videos_dir = os.path.join(base_dir, "videos")
        await asyncio.to_thread(os.makedirs, videos_dir, exist_ok=True)
        
        # Find all frames_XXX directories
        frame_dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if d.startswith("frames_")]
        
        if not frame_dirs:
            logger.error("No frame directories found")
            job_status_manager.set_job_error(job_id, "No frame directories found")
            return
        
        # Generate the combined video
        output_path = os.path.join(videos_dir, "combined_video.mp4")
        success = await asyncio.to_thread(
            generate_combined_video,
            frame_dirs,
            output_path,
            fps,
            transition_duration
        )
        
        if success:
            logger.info("Combined video generated successfully")
            job_status_manager.update_job_status(job_id, "completed")
        else:
            logger.error("Failed to generate combined video")
            job_status_manager.set_job_error(job_id, "Failed to generate combined video")
            
    except Exception as e:
        error_msg = f"Error in combined video generation: {str(e)}"
        logger.error(error_msg)
        job_status_manager.set_job_error(job_id, error_msg)

@router.post("/generate-combined-video", response_model=CombinedVideoGenerationResponse)
async def generate_combined_video_endpoint(
    request: CombinedVideoGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a single video combining all frame sequences with transitions.
    The video will be saved to:
    /generated_images/{request_id}/videos/combined_video.mp4
    """
    try:
        logger.info(f"Starting combined video generation for request_id: {request.request_id}")
        
        # Get the base directory for the request
        base_dir = os.path.join(os.getcwd(), "generated_images", request.request_id)
        if not os.path.exists(base_dir):
            logger.error(f"Base directory not found: {base_dir}")
            raise HTTPException(status_code=404, detail="Request ID not found")
        
        # Create a job ID for tracking
        job_id = str(uuid.uuid4())
        logger.info(f"Created job_id: {job_id}")
        
        # Initialize job status
        job_status_manager.create_job(job_id, request.request_id, 1)  # Single job for the combined video
        logger.info("Initialized job status")
        
        # Create response
        response = {
            "request_id": request.request_id,
            "job_id": job_id,
            "output_directory": os.path.join(base_dir, "videos")
        }
        
        # Add background task
        logger.info("Adding background task for combined video generation")
        background_tasks.add_task(
            process_combined_video_generation,
            job_id=job_id,
            request_id=request.request_id,
            base_dir=base_dir,
            fps=request.fps,
            transition_duration=request.transition_duration
        )
        
        logger.info("Background task added, returning response")
        return response
        
    except Exception as e:
        error_message = f"Error in combined video generation endpoint: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

@router.get("/download-video/{request_id}")
async def download_combined_video(request_id: str):
    """
    Download the combined video file for a specific request_id.
    """
    try:
        # Construct the path to the combined video file
        base_dir = os.path.join(os.getcwd(), "generated_images", request_id)
        video_path = os.path.join(base_dir, "videos", "combined_video.mp4")
        
        # Check if the video file exists
        if not os.path.exists(video_path):
            logger.error(f"Combined video not found at path: {video_path}")
            raise HTTPException(status_code=404, detail="Combined video not found for the specified request_id")
        
        # Return the file as a downloadable response
        return FileResponse(
            path=video_path,
            filename=f"combined_video_{request_id}.mp4",
            media_type="video/mp4"
        )
            
    except Exception as e:
        error_message = f"Error downloading combined video: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message) 