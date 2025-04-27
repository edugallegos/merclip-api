from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.context import VideoContext
import requests
import re

class IdentifyPlatformStep(BaseStep):
    """Step to identify the platform from the URL and extract the video ID."""
    
    def __init__(self, enabled: bool = True):
        super().__init__("identify_platform", enabled)
    
    def _resolve_tiktok_short_url(self, url: str) -> str:
        """Resolve TikTok short URL to get the full URL.
        
        Args:
            url: The shortened TikTok URL
            
        Returns:
            The resolved URL or the original URL if resolution fails
        """
        try:
            self.logger.info(f"Resolving short TikTok URL: {url}")
            response = requests.head(url, allow_redirects=True, timeout=10)
            resolved_url = response.url
            self.logger.info(f"Resolved to: {resolved_url}")
            return resolved_url
        except Exception as e:
            self.logger.error(f"Error resolving short URL {url}: {str(e)}")
            return url  # Return original URL on failure
    
    def _extract_tiktok_id(self, url: str) -> str:
        """Extract TikTok video ID from the URL.
        
        Args:
            url: The TikTok URL
            
        Returns:
            The extracted video ID
        """
        # Check if it's a short URL (vm.tiktok.com or vt.tiktok.com)
        if "vm.tiktok.com" in url or "vt.tiktok.com" in url:
            # Resolve the short URL to get the full URL
            url = self._resolve_tiktok_short_url(url)
        
        # Extract video ID from regular TikTok URL formats
        if "/video/" in url:
            # Format: tiktok.com/@username/video/1234567890123456789
            video_id = url.split('/video/')[-1].split('?')[0]
        elif "/v/" in url:
            # Format: tiktok.com/v/1234567890123456789
            video_id = url.split('/v/')[-1].split('?')[0]
        else:
            # Try to extract with regex for numeric ID
            match = re.search(r'(\d{19})', url)
            if match:
                video_id = match.group(1)
            else:
                # Fallback: use the last path component
                video_id = url.split('/')[-1].split('?')[0]
                # If still empty, generate a timestamp-based ID to avoid download failures
                if not video_id:
                    import time
                    video_id = f"tiktok_{int(time.time())}"
                    self.logger.warning(f"Could not extract TikTok video ID, using generated ID: {video_id}")
        
        return video_id
    
    def process(self, context: VideoContext) -> VideoContext:
        """Process the video context to identify platform and extract video ID.
        
        Args:
            context: The video context containing the URL
            
        Returns:
            The updated video context with platform and video_id set
        """
        url = context.url
        
        if "twitter.com" in url or "x.com" in url:
            video_id = url.split('/')[-1].split('?')[0]
            context.video_id = video_id
            context.platform = "twitter"
            self.logger.info(f"Identified as Twitter video: {video_id}")
        elif "tiktok.com" in url:
            # Extract TikTok video ID using the dedicated method
            video_id = self._extract_tiktok_id(url)
            context.video_id = video_id
            context.platform = "tiktok"
            self.logger.info(f"Identified as TikTok video: {video_id}")
        else:
            error_msg = f"Unsupported platform for URL: {url}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
        
        return context 