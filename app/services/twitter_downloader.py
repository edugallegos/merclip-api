import os
import uuid
import logging
from typing import Optional
import snscrape.modules.twitter as sntwitter
import yt_dlp

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, output_dir: str = "generated_images/videos"):
        self.output_dir = output_dir
        self.twitter_dir = os.path.join(output_dir, "twitter")
        self.tiktok_dir = os.path.join(output_dir, "tiktok")
        os.makedirs(self.twitter_dir, exist_ok=True)
        os.makedirs(self.tiktok_dir, exist_ok=True)
        logger.info(f"VideoDownloader initialized with output directory: {output_dir}")

    def _get_unique_filename(self, video_id: str) -> str:
        """Generate a unique filename for the downloaded video based on video ID."""
        unique_id = uuid.uuid4().hex[:8]
        return f"{video_id}_{unique_id}"
    
    def _extract_video_id(self, url: str) -> tuple:
        """Extract video ID and platform from URL."""
        if "twitter.com" in url or "x.com" in url:
            video_id = url.split('/')[-1].split('?')[0]
            return video_id, "twitter"
        elif "tiktok.com" in url:
            # TikTok URLs can be in different formats
            if "/video/" in url:
                video_id = url.split('/video/')[-1].split('?')[0]
            else:
                # For share URLs like vm.tiktok.com/XXXXXXX/
                video_id = url.split('/')[-1].split('?')[0]
            return video_id, "tiktok"
        else:
            logger.error(f"Invalid URL format: {url}")
            return None, None
    
    def download_video(self, url: str) -> Optional[str]:
        """Download video from a Twitter or TikTok URL.
        
        Args:
            url: The URL of the post containing the video
            
        Returns:
            The path to the downloaded video file, or None if download failed
        """
        try:
            # Extract video ID and platform from URL
            video_id, platform = self._extract_video_id(url)
            
            if not video_id:
                return None
            
            # Set the appropriate output directory
            if platform == "twitter":
                output_dir = self.twitter_dir
            elif platform == "tiktok":
                output_dir = self.tiktok_dir
            else:
                logger.error(f"Unsupported platform: {platform}")
                return None
            
            # Create a unique filename for this download
            filename = self._get_unique_filename(video_id)
            output_path = os.path.join(output_dir, filename)
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best',
                'outtmpl': f"{output_path}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
            }
            
            # Download the video
            logger.info(f"Starting download for {platform} video: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    # Get the actual filename with extension
                    downloaded_path = f"{output_path}.{info.get('ext', 'mp4')}"
                    logger.info(f"Successfully downloaded {platform} video to: {downloaded_path}")
                    return downloaded_path
                else:
                    logger.error(f"No video information found for {platform} video: {url}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None

# For backward compatibility
TwitterDownloader = VideoDownloader 