import os
import uuid
import logging
from typing import Optional
import snscrape.modules.twitter as sntwitter
import yt_dlp

logger = logging.getLogger(__name__)

class TwitterDownloader:
    def __init__(self, output_dir: str = "generated_images/twitter_videos"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"TwitterDownloader initialized with output directory: {output_dir}")

    def _get_unique_filename(self, tweet_id: str) -> str:
        """Generate a unique filename for the downloaded video based on tweet ID."""
        unique_id = uuid.uuid4().hex[:8]
        return f"{tweet_id}_{unique_id}"
    
    def download_video(self, tweet_url: str) -> Optional[str]:
        """Download video from a tweet URL.
        
        Args:
            tweet_url: The URL of the tweet containing the video
            
        Returns:
            The path to the downloaded video file, or None if download failed
        """
        try:
            # Extract tweet ID from URL
            if "twitter.com" in tweet_url or "x.com" in tweet_url:
                tweet_id = tweet_url.split('/')[-1].split('?')[0]
            else:
                logger.error(f"Invalid Twitter URL format: {tweet_url}")
                return None
            
            # Create a unique filename for this download
            filename = self._get_unique_filename(tweet_id)
            output_path = os.path.join(self.output_dir, filename)
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best',
                'outtmpl': f"{output_path}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
            }
            
            # Download the video
            logger.info(f"Starting download for tweet: {tweet_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(tweet_url, download=True)
                if info:
                    # Get the actual filename with extension
                    downloaded_path = f"{output_path}.{info.get('ext', 'mp4')}"
                    logger.info(f"Successfully downloaded video to: {downloaded_path}")
                    return downloaded_path
                else:
                    logger.error(f"No video information found for tweet: {tweet_url}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error downloading Twitter video: {str(e)}")
            return None 