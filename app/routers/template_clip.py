from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import json
import os
from ..models.template_clip import TemplateClipRequest, Element
from ..models.video import VideoRequest, JobResponse, ElementType
from ..services.ffmpeg import FFmpegService
import uuid

router = APIRouter(
    prefix="/template-clip",
    tags=["template-clip"]
)

def load_template(template_id: str) -> Dict[str, Any]:
    """Load a template from the templates directory."""
    template_path = os.path.join("templates", f"{template_id}.json")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    with open(template_path, "r") as f:
        return json.load(f)

def transform_to_video_request(template: Dict[str, Any], elements: list[Element]) -> VideoRequest:
    """Transform template and elements into a VideoRequest."""
    # Get the output settings from template
    output = template["output"]
    
    # Calculate total duration from elements
    total_duration = max(
        (elem.timeline.start + elem.timeline.duration for elem in elements),
        default=0
    )
    
    # Add duration to output
    output["duration"] = total_duration
    
    # Transform elements using template defaults
    transformed_elements = []
    for element in elements:
        element_type = element.type
        template_defaults = template["defaults"].get(element_type, {})
        
        # Create base element with template defaults
        transformed_element = {
            "type": element_type,
            "id": f"{element_type}-{len(transformed_elements)}",
            "timeline": element.timeline.dict()
        }
        
        # Handle position shorthand if provided
        if hasattr(element, 'position') and element.position:
            # Create transform with position from shorthand
            position = {"x": element.position, "y": element.position}
            transformed_element["transform"] = {"position": position}
        # Add transform only for non-audio elements
        elif element_type != ElementType.AUDIO:
            transformed_element["transform"] = template_defaults.get("transform", {})
        
        # Add source or text based on type
        if element_type in [ElementType.VIDEO, ElementType.IMAGE, ElementType.AUDIO]:
            transformed_element["source"] = element.source
            
            # Add audio properties for audio elements
            if element_type == ElementType.AUDIO:
                # Use user-provided values first, then fall back to template defaults
                transformed_element["volume"] = getattr(element, 'volume', template_defaults.get("volume", 1.0))
                transformed_element["fade_in"] = getattr(element, 'fade_in', template_defaults.get("fade_in", 0))
                transformed_element["fade_out"] = getattr(element, 'fade_out', template_defaults.get("fade_out", 0))
        else:
            transformed_element["text"] = element.text
        
        # Add audio property for video elements
        if element_type == ElementType.VIDEO:
            transformed_element["audio"] = template_defaults.get("audio", True)
        
        # Add style only for text elements
        if element_type == ElementType.TEXT:
            style_defaults = template_defaults.get("style", {})
            transformed_element["style"] = {
                "font_family": style_defaults.get("font_family", "Arial"),
                "font_size": style_defaults.get("font_size", 48),
                "color": style_defaults.get("color", "white"),
                "alignment": style_defaults.get("alignment", "center"),
                "background_color": style_defaults.get("background_color", "rgba(0,0,0,0.3)")
            }
            
            # Override with user-provided style if available
            if hasattr(element, 'style') and element.style:
                for key, value in element.style.dict(exclude_unset=True).items():
                    if value is not None:
                        transformed_element["style"][key] = value
        
        transformed_elements.append(transformed_element)
    
    return VideoRequest(
        output=output,
        elements=transformed_elements
    )

@router.post("", response_model=JobResponse)
async def create_template_clip(request: TemplateClipRequest, background_tasks: BackgroundTasks):
    # Load the template
    template = load_template(request.template_id)
    
    # Transform the request into a VideoRequest
    video_request = transform_to_video_request(template, request.elements)
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Save the job input and initialize status
    input_path = FFmpegService.save_job(video_request, job_id)
    
    # Generate FFmpeg command
    output_path = FFmpegService.get_output_path(job_id)
    command = FFmpegService.generate_command(video_request, output_path)
    
    # Start background task to render the video
    background_tasks.add_task(FFmpegService.render_video, job_id, command)
    
    # Return initial job status
    return JobResponse(**FFmpegService.get_job_status(job_id)) 