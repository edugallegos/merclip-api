from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..models.clip import ClipRequest, ClipResponse
from .template import TEMPLATES
import uuid

router = APIRouter(
    prefix="/clip",
    tags=["clip"]
)

@router.post("", response_model=ClipResponse)
async def create_clip(request: ClipRequest):
    # Validate template exists
    if request.template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")
    
    # Generate a unique clip ID
    clip_id = str(uuid.uuid4())
    
    # For now, return a mock response
    # In production, this would trigger an async job to render the video
    return ClipResponse(
        clip_id=clip_id,
        status="processing",
        url=None
    ) 