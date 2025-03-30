from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class Element(BaseModel):
    id: str
    type: str
    default_content: str
    default_config: Dict[str, Any]

class Template(BaseModel):
    id: str
    name: str
    elements: List[Element]

class TemplateCreate(BaseModel):
    name: str
    elements: List[Element]

class TemplateResponse(BaseModel):
    id: str
    name: str
    elements: List[Element]

class TemplatesResponse(BaseModel):
    templates: List[TemplateResponse] 