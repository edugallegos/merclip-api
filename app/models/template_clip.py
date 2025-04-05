from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

class ElementType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"

class Timeline(BaseModel):
    start: float = Field(..., ge=0)
    duration: float = Field(..., gt=0)

class Position(BaseModel):
    """Position model for element positioning.
    
    This class supports both numeric pixel values and string position presets.
    When used in templates, these values determine where elements appear in the video frame.
    
    String position presets include:
    - Basic positions: "center", "top", "bottom", "left", "right"
    - Corner positions: "top-left", "top-right", "bottom-left", "bottom-right"
    - Mid positions: "mid-top", "mid-bottom"
    
    These values are converted to pixel coordinates during rendering based on the video dimensions.
    
    Example:
        To position an element at the top center of the video:
        position = Position(x="center", y="top")
    """
    x: Union[int, str] = "center"
    y: Union[int, str] = "center"
    
    @validator('x', 'y')
    def validate_position(cls, v):
        """Validate that string position values are one of the allowed presets."""
        allowed_positions = [
            "center", "top", "bottom", "left", "right", 
            "top-left", "top-right", "bottom-left", "bottom-right", 
            "mid-top", "mid-bottom"
        ]
        if isinstance(v, str) and v not in allowed_positions:
            raise ValueError(f'String position must be one of: {", ".join(allowed_positions)}')
        return v

class Transform(BaseModel):
    position: Optional[Position] = None
    scale: Optional[float] = None

class Style(BaseModel):
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    color: Optional[str] = None
    background_color: Optional[str] = None
    alignment: Optional[str] = None

class Element(BaseModel):
    """Element model for template-based clip requests.
    
    This model includes both standard element properties and special shorthand properties
    that simplify element creation. When processed, these elements are merged with template
    defaults to create the final video elements.
    
    Special properties:
    - position: A string shorthand for positioning elements (e.g., "center", "top-left").
                This is converted to a full Transform.position object during processing.
    
    Standard properties follow the VideoRequest element structure, and all optional 
    properties will use template defaults if not specified.
    """
    type: ElementType
    source: Optional[str] = None
    text: Optional[str] = None
    timeline: Timeline
    # Optional fields for different element types
    transform: Optional[Transform] = None
    style: Optional[Style] = None
    # Audio properties
    volume: Optional[float] = None
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None
    # Simple position helper - special property
    position: Optional[str] = None  # Can be "center", "top", "bottom", "left", "right", etc.

    @validator('source', 'text')
    def validate_source_text(cls, v, values):
        """Validate that source or text is provided based on element type."""
        if 'type' in values:
            if values['type'] == ElementType.TEXT and not v:
                raise ValueError('text is required for text elements')
            if values['type'] in [ElementType.VIDEO, ElementType.AUDIO, ElementType.IMAGE] and not v:
                raise ValueError('source is required for video, audio, and image elements')
        return v
        
    @validator('transform')
    def set_transform_from_position(cls, v, values):
        """Create transform from position shorthand if transform not provided."""
        # If position shorthand is provided but transform is not, create transform
        if not v and 'position' in values and values['position']:
            position = Position(x=values['position'], y=values['position'])
            return Transform(position=position)
        return v

class TemplateClipRequest(BaseModel):
    template_id: str
    elements: List[Element] 