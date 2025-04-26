import os
import uuid
import yt_dlp
from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.context import VideoContext

class DownloadVideoStep(BaseStep):
    """Step to download a video from the identified platform."""
    
    def __init__(self, output_dir: str = "generated_images/videos", enabled: bool = True):
        super().__init__("download_video", enabled)
        self.output_dir = output_dir
        self.twitter_dir = os.path.join(output_dir, "twitter")
        self.tiktok_dir = os.path.join(output_dir, "tiktok")
        os.makedirs(self.twitter_dir, exist_ok=True)
        os.makedirs(self.tiktok_dir, exist_ok=True)
    
    def _get_unique_filename(self, video_id: str) -> str:
        """Generate a unique filename for the downloaded video based on video ID."""
        unique_id = uuid.uuid4().hex[:8]
        return f"{video_id}_{unique_id}"
    
    def process(self, context: VideoContext) -> VideoContext:
        """Process the video context to download the video.
        
        Args:
            context: The video context containing URL, platform, and video_id
            
        Returns:
            The updated video context with video_path set
        """
        # Skip if platform or video_id is missing
        if not context.platform or not context.video_id:
            self.logger.error("Missing platform or video_id, cannot download video")
            context.add_error("Missing platform or video_id")
            return context
        
        # Set the appropriate output directory
        if context.platform == "twitter":
            output_dir = self.twitter_dir
        elif context.platform == "tiktok":
            output_dir = self.tiktok_dir
        else:
            error_msg = f"Unsupported platform: {context.platform}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
            return context
        
        # Create a unique filename for this download
        filename = self._get_unique_filename(context.video_id)
        output_path = os.path.join(output_dir, filename)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best',
            'outtmpl': f"{output_path}.%(ext)s",
            'quiet': True,
            'no_warnings': True,
        }
        
        # Download the video
        self.logger.info(f"Starting download for {context.platform} video: {context.url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(context.url, download=True)
            if info:
                # Get the actual filename with extension
                context.video_path = f"{output_path}.{info.get('ext', 'mp4')}"
                context.metadata["video_info"] = info
                self.logger.info(f"Successfully downloaded {context.platform} video to: {context.video_path}")
            else:
                error_msg = f"No video information found for {context.platform} video: {context.url}"
                self.logger.error(error_msg)
                context.add_error(error_msg)
        
        return context 