from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..models.template import TemplateCreate, TemplateResponse, TemplatesResponse
import uuid

router = APIRouter(
    prefix="/template",
    tags=["template"]
)

# In-memory storage for templates (replace with database in production)
TEMPLATES: Dict[str, Dict[str, Any]] = {
    "test-template": {
        "id": "test-template",
        "name": "Test Template",
        "elements": [
            {
                "id": "title",
                "type": "text",
                "content": "Default Title",
                "x": 100,
                "y": 100,
                "font_size": 48,
                "color": "#FFFFFF",
                "animation": "fade-in",
                "start": 0,
                "duration": 5
            },
            {
                "id": "subtitle", 
                "type": "text",
                "content": "Default Subtitle",
                "x": 100,
                "y": 200,
                "font_size": 32,
                "color": "#CCCCCC",
                "animation": "slide-up",
                "start": 1,
                "duration": 4
            }
        ]
    }
}

@router.post("", response_model=TemplateResponse)
async def create_template(template: TemplateCreate):
    # Generate a unique template ID
    template_id = str(uuid.uuid4())
    
    # Create the template
    template_data = {
        "id": template_id,
        "name": template.name,
        "elements": [element.dict() for element in template.elements]
    }
    
    # Store the template
    TEMPLATES[template_id] = template_data
    
    return TemplateResponse(**template_data)

@router.get("", response_model=TemplatesResponse)
async def get_templates():
    return TemplatesResponse(
        templates=[
            TemplateResponse(**template)
            for template in TEMPLATES.values()
        ]
    )

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return TemplateResponse(**TEMPLATES[template_id]) 