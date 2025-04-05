from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, TypeVar, Union, Optional
import json
import os
from ..models.template_clip import TemplateClipRequest, Element
from ..models.video import VideoRequest, JobResponse, ElementType
from ..services.ffmpeg import FFmpegService
import uuid
import logging

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/template-clip",
    tags=["template-clip"]
)

T = TypeVar('T')

def deep_merge(template: Dict[str, Any], user_values: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries with nested structures.
    
    This function merges user-provided values into a template dictionary,
    properly handling nested objects by recursively merging them.
    
    Args:
        template: The template dictionary with default values
        user_values: User-provided values to override the template
        
    Returns:
        A new dictionary with the merged values
    """
    result = template.copy()
    
    for key, value in user_values.items():
        # Skip None values
        if value is None:
            continue
            
        # If both values are dictionaries, recursively merge them
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = deep_merge(result[key], value)
        else:
            # Otherwise just override the value
            result[key] = value
            
    return result

def get_property_with_defaults(
    element: Element,
    template_defaults: Dict[str, Any], 
    processed_element: Dict[str, Any],
    property_name: str
) -> Dict[str, Any]:
    """Get a property with merged defaults and user values.
    
    This function handles the common pattern of merging template defaults
    with user-provided values for a specific property group.
    
    Priority order:
    1. Element-specific properties (from element attributes)
    2. Special properties (from processed_element)
    3. Template defaults (fallback)
    
    Args:
        element: The element being processed
        template_defaults: Template defaults for this element type
        processed_element: Processed element with special properties
        property_name: The name of the property to process (e.g., "transform", "style")
        
    Returns:
        The merged property dictionary
    """
    # Start with template defaults for this property
    result = template_defaults.get(property_name, {}).copy()
    
    # Apply special properties from processed element if available (2nd priority)
    if property_name in processed_element:
        result = deep_merge(result, processed_element[property_name])
    
    # Apply element attributes if available (highest priority)
    if hasattr(element, property_name) and getattr(element, property_name) is not None:
        user_property = getattr(element, property_name).dict(exclude_unset=True)
        result = deep_merge(result, user_property)
        
    return result

def load_template(template_id: str) -> Dict[str, Any]:
    """Load a template from the templates directory."""
    template_path = os.path.join("templates", f"{template_id}.json")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    try:
        with open(template_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error parsing template: {str(e)}")

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
            # Get and merge transform properties
            transformed_element["transform"] = get_property_with_defaults(
                element, 
                template_defaults, 
                processed_element, 
                "transform"
            )
        
        # Handle audio-specific properties
        if element_type == ElementType.AUDIO:
            # Add audio properties using the same pattern as other properties
            for prop in ["volume", "fade_in", "fade_out"]:
                # Get template default first
                default_value = template_defaults.get(prop)
                
                # Check if user provided a value
                user_value = getattr(element, prop, None)
                
                # Apply user value if available, otherwise use template default
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
            # Get style properties from the template, not hardcoded
            transformed_element["style"] = get_property_with_defaults(
                element, 
                template_defaults, 
                processed_element, 
                "style"
            )
        
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