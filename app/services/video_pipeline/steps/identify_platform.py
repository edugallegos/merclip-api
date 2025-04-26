from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.context import VideoContext

class IdentifyPlatformStep(BaseStep):
    """Step to identify the platform from the URL and extract the video ID."""
    
    def __init__(self, enabled: bool = True):
        super().__init__("identify_platform", enabled)
    
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
            # TikTok URLs can be in different formats
            if "/video/" in url:
                video_id = url.split('/video/')[-1].split('?')[0]
            else:
                # For share URLs like vm.tiktok.com/XXXXXXX/
                video_id = url.split('/')[-1].split('?')[0]
            context.video_id = video_id
            context.platform = "tiktok"
            self.logger.info(f"Identified as TikTok video: {video_id}")
        else:
            error_msg = f"Unsupported platform for URL: {url}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
        
        return context 