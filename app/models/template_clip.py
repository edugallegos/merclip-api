from typing import List, Optional
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

class Element(BaseModel):
    type: ElementType
    source: Optional[str] = None
    text: Optional[str] = None
    timeline: Timeline

    @validator('source', 'text')
    def validate_source_text(cls, v, values):
        if 'type' in values:
            if values['type'] == ElementType.TEXT and not v:
                raise ValueError('text is required for text elements')
            if values['type'] in [ElementType.VIDEO, ElementType.AUDIO, ElementType.IMAGE] and not v:
                raise ValueError('source is required for video, audio, and image elements')
        return v

class TemplateClipRequest(BaseModel):
    template_id: str
    elements: List[Element] 