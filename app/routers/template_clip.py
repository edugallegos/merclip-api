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
    """Transform template and elements into a VideoRequest.
    
    This function merges user-provided elements with template defaults.
    Special properties like 'position', 'size', etc. are handled to convert from simplified
    notation to the full template format.
    
    Args:
        template: The template definition with defaults
        elements: User-provided elements to be merged with template defaults
        
    Returns:
        VideoRequest: A complete video request ready for processing
    """
    # Get the output settings from template
    output = template["output"]
    
    # Calculate total duration from elements
    total_duration = max(
        (elem.timeline.start + elem.timeline.duration for elem in elements),
        default=output.get("duration", 10)  # Default to template duration or 10 seconds
    )
    
    # Add duration to output
    output["duration"] = total_duration
    
    # Transform elements using template defaults
    transformed_elements = []
    for element in elements:
        element_type = element.type
        template_defaults = template["defaults"].get(element_type.value, {})
        
        # Process special properties first
        processed_element = element.process_special_properties()
        
        # Create base element with required fields
        transformed_element = {
            "type": element_type,
            "id": f"{element_type}-{len(transformed_elements)}",
            "timeline": element.timeline.dict()
        }
        
        # Handle element-type specific properties
        if element_type in [ElementType.VIDEO, ElementType.IMAGE, ElementType.AUDIO]:
            transformed_element["source"] = element.source
        elif element_type == ElementType.TEXT:
            transformed_element["text"] = element.text
        
        # ----- Handle transforms and element-specific properties -----
        
        # Only add transform for non-audio elements
        if element_type != ElementType.AUDIO:
            # Start with template defaults for transform
            template_transform = template_defaults.get("transform", {})
            
            # Apply user-provided transform properties if available
            if "transform" in processed_element:
                user_transform = processed_element["transform"]
                
                # If user provided a position, merge it with template position
                if "position" in user_transform:
                    user_position = user_transform.pop("position", {})
                    template_position = template_transform.get("position", {})
                    
                    # Create merged position
                    merged_position = template_position.copy()
                    for key, value in user_position.items():
                        if value is not None:
                            merged_position[key] = value
                    
                    # Update template transform with merged position
                    template_transform_copy = template_transform.copy()
                    template_transform_copy["position"] = merged_position
                    
                    # Apply remaining transform properties
                    for key, value in user_transform.items():
                        if value is not None:
                            template_transform_copy[key] = value
                    
                    transformed_element["transform"] = template_transform_copy
                else:
                    # Just merge the transforms
                    merged_transform = {**template_transform, **user_transform}
                    transformed_element["transform"] = merged_transform
            else:
                # No user transform, use template defaults
                transformed_element["transform"] = template_transform
        
        # Handle audio-specific properties
        if element_type == ElementType.AUDIO:
            # Add audio properties with template defaults and user overrides
            for prop in ["volume", "fade_in", "fade_out"]:
                user_value = getattr(element, prop, None)
                default_value = template_defaults.get(prop)
                
                # Use user value if provided, otherwise template default
                if user_value is not None:
                    transformed_element[prop] = user_value
                elif default_value is not None:
                    transformed_element[prop] = default_value
        
        # Handle video-specific properties
        if element_type == ElementType.VIDEO:
            # Set audio enabled/disabled
            transformed_element["audio"] = template_defaults.get("audio", True)
        
        # Handle text-specific style properties
        if element_type == ElementType.TEXT:
            # Start with template style defaults
            style_defaults = template_defaults.get("style", {})
            transformed_style = {
                "font_family": style_defaults.get("font_family", "Arial"),
                "font_size": style_defaults.get("font_size", 48),
                "color": style_defaults.get("color", "white"),
                "alignment": style_defaults.get("alignment", "center"),
                "background_color": style_defaults.get("background_color", "rgba(0,0,0,0.3)")
            }
            
            # Override with user-provided style if available
            if hasattr(element, "style") and element.style:
                user_style = element.style.dict(exclude_unset=True)
                for key, value in user_style.items():
                    if value is not None:
                        transformed_style[key] = value
            
            transformed_element["style"] = transformed_style
        
        transformed_elements.append(transformed_element)
    
    # Create final VideoRequest
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