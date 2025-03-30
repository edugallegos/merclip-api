from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ElementConfig(BaseModel):
    type: str
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    font_size: Optional[int] = None
    color: Optional[str] = None
    animation: Optional[str] = None
    start: Optional[float] = None
    duration: Optional[float] = None
    loop: Optional[bool] = None

class ElementOverride(BaseModel):
    id: str
    content: str
    config: ElementConfig

class ClipRequest(BaseModel):
    template_id: str
    overrides: List[ElementOverride]

class ClipResponse(BaseModel):
    clip_id: str
    status: str
    url: Optional[str] = None
    error: Optional[str] = None 