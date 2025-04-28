"""
DEPRECATED: This module is maintained for backward compatibility.
Please use app.services.video_pipeline instead.
"""

import logging
import os
from app.services.video_pipeline import VideoProcessor

logger = logging.getLogger(__name__)
logger.warning(
    "The twitter_downloader module is deprecated. "
    "Please use app.services.video_pipeline instead."
)

class VideoDownloader(VideoProcessor):
    """Legacy class for backward compatibility."""
    
    def __init__(self, output_dir: str = "generated_images/videos"):
        super().__init__(output_dir)
        # Ensure the youtube directory exists
        self.youtube_dir = os.path.join(output_dir, "youtube")
        os.makedirs(self.youtube_dir, exist_ok=True)
        logger.info(f"VideoDownloader initialized with youtube_dir: {self.youtube_dir}") 