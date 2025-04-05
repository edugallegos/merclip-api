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
    x: Union[int, str] = "center"
    y: Union[int, str] = "center"
    
    @validator('x', 'y')
    def validate_position(cls, v):
        if isinstance(v, str) and v not in ["center", "top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right", "mid-top", "mid-bottom"]:
            raise ValueError('String position must be one of: center, top, bottom, left, right, top-left, top-right, bottom-left, bottom-right, mid-top, mid-bottom')
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
    # Simple position helper
    position: Optional[str] = None  # Can be "center", "top", etc.

    @validator('source', 'text')
    def validate_source_text(cls, v, values):
        if 'type' in values:
            if values['type'] == ElementType.TEXT and not v:
                raise ValueError('text is required for text elements')
            if values['type'] in [ElementType.VIDEO, ElementType.AUDIO, ElementType.IMAGE] and not v:
                raise ValueError('source is required for video, audio, and image elements')
        return v
        
    @validator('transform')
    def set_transform_from_position(cls, v, values):
        # If position shorthand is provided but transform is not, create transform
        if not v and 'position' in values and values['position']:
            position = Position(x=values['position'], y=values['position'])
            return Transform(position=position)
        return v

class TemplateClipRequest(BaseModel):
    template_id: str
    elements: List[Element] 