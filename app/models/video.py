from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum
import logging
from datetime import datetime
import sqlite3
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class VideoStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    DONE = "done"
    FAILED = "failed"

class ProcessedVideo(BaseModel):
    """Model for a processed video and its associated files."""
    video_id: str
    url: str
    platform: str
    file_path: str
    file_url: str
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    srt_path: Optional[str] = None
    srt_url: Optional[str] = None
    collage_path: Optional[str] = None
    collage_url: Optional[str] = None
    status: VideoStatusEnum = VideoStatusEnum.PROCESSED
    created_at: datetime
    updated_at: datetime
    language_code: str = "es"
    metadata: Dict = {} 