import os
import subprocess
from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.context import VideoContext

class ExtractAudioStep(BaseStep):
    """Step to extract audio from a downloaded video."""
    
    def __init__(self, output_dir: str = "generated_images/videos/audio", enabled: bool = True):
        super().__init__("extract_audio", enabled)
        self.audio_dir = output_dir
        os.makedirs(self.audio_dir, exist_ok=True)
    
    def process(self, context: VideoContext) -> VideoContext:
        """Process the video context to extract audio from the video.
        
        Args:
            context: The video context containing video_path
            
        Returns:
            The updated video context with audio_path set
        """
        # Skip if video_path is missing or doesn't exist
        if not context.video_path or not os.path.exists(context.video_path):
            self.logger.error("Missing or nonexistent video_path, cannot extract audio")
            context.add_error("Missing or nonexistent video_path")
            return context
        
        # Generate output filename for audio
        basename = os.path.basename(context.video_path).split('.')[0]
        audio_path = os.path.join(self.audio_dir, f"{basename}.mp3")
        
        # Use FFmpeg to extract audio
        self.logger.info(f"Extracting audio from {context.video_path} to {audio_path}")
        command = [
            "ffmpeg", 
            "-i", context.video_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "-ar", "44100",
            "-y",  # Overwrite output file if it exists
            audio_path
        ]
        
        # Run FFmpeg command
        process = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            error_msg = f"FFmpeg error: {process.stderr}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
            return context
        
        context.audio_path = audio_path
        self.logger.info(f"Successfully extracted audio to: {audio_path}")
        
        return context 