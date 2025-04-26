"""
DEPRECATED: This module is maintained for backward compatibility.
Please use app.services.video_pipeline instead.
"""

import logging
from app.services.video_pipeline import VideoProcessor

logger = logging.getLogger(__name__)
logger.warning(
    "The twitter_downloader module is deprecated. "
    "Please use app.services.video_pipeline instead."
)

class TwitterDownloader(VideoProcessor):
    """Legacy class for backward compatibility."""
    pass 