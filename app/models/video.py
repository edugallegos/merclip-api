from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

class ElementType(str, Enum):
    VIDEO = "video"
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"

class JobStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Resolution(BaseModel):
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)

class Output(BaseModel):
    resolution: Resolution
    frame_rate: int = Field(..., gt=0)
    format: str = Field(..., pattern="^(mp4|mov|avi)$")
    duration: float = Field(..., gt=0)
    background_color: str = Field(..., pattern="^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$")

class Timeline(BaseModel):
    start: float = Field(..., ge=0)
    duration: float = Field(..., gt=0)
    in_: Optional[float] = Field(None, ge=0, alias="in")

class Position(BaseModel):
    x: Union[int, str]
    y: Union[int, str]

class Transform(BaseModel):
    scale: Optional[float] = Field(None, gt=0)
    position: Position
    opacity: Optional[float] = Field(None, ge=0, le=1)

class Style(BaseModel):
    font_family: str
    font_size: int = Field(..., gt=0)
    color: str = Field(..., pattern="^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$")
    background_color: Optional[str] = Field(None, pattern="^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$|^rgba\(\d+,\d+,\d+,\d*\.?\d+\)$")
    alignment: str = Field(..., pattern="^(left|center|right)$")

class Element(BaseModel):
    type: ElementType
    id: str
    source: Optional[str] = None
    text: Optional[str] = None
    timeline: Timeline
    transform: Optional[Transform] = None
    style: Optional[Style] = None
    audio: Optional[bool] = None
    # Audio properties
    volume: Optional[float] = None
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None

    @validator('source', 'text')
    def validate_source_text(cls, v, values):
        if 'type' in values:
            if values['type'] == ElementType.TEXT and not v:
                raise ValueError('text is required for text elements')
            if values['type'] in [ElementType.VIDEO, ElementType.AUDIO, ElementType.IMAGE] and not v:
                raise ValueError('source is required for video, audio, and image elements')
        return v

    @validator('style')
    def validate_style(cls, v, values):
        if 'type' in values and values['type'] == ElementType.TEXT and not v:
            raise ValueError('style is required for text elements')
        return v

    @validator('transform')
    def validate_transform(cls, v, values):
        if 'type' in values and values['type'] != ElementType.AUDIO and not v:
            raise ValueError('transform is required for video, image, and text elements')
        return v

    @validator('audio')
    def validate_audio(cls, v, values):
        if 'type' in values and values['type'] == ElementType.VIDEO and v is None:
            raise ValueError('audio property is required for video elements')
        return v

class VideoRequest(BaseModel):
    output: Output
    elements: List[Element]

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    output_url: Optional[str] = None 