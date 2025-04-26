from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class VideoContext:
    """Data container for passing information between pipeline steps.
    
    This class represents the state of a video processing job as it moves through the pipeline.
    Each processing step updates the context with new information or results.
    """
    url: str
    video_id: Optional[str] = None
    platform: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None
    transcript_srt: Optional[str] = None
    srt_path: Optional[str] = None
    collage_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def has_errors(self) -> bool:
        """Check if there are any errors in the context."""
        return len(self.errors) > 0
    
    def add_error(self, error_msg: str) -> None:
        """Add an error message to the context."""
        self.errors.append(error_msg)
    
    def get_language_code(self) -> str:
        """Get the language code from metadata or return the default."""
        return self.metadata.get("language_code", "es")  # Default to Spanish 