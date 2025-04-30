import os
import logging
import base64
from typing import Optional, Tuple, List, Type, Callable, Dict, Any
from app.services.video_pipeline.context import VideoContext
from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.steps import (
    IdentifyPlatformStep,
    DownloadVideoStep,
    ExtractAudioStep,
    TranscribeAudioStep,
    CreateCollageStep
)

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Main class that orchestrates the video processing pipeline.
    
    This class manages the pipeline steps and provides a simple interface for
    downloading and processing videos from various platforms.
    """
    
    def __init__(self, output_dir: str = "generated_images/videos"):
        """Initialize the video processor.
        
        Args:
            output_dir: Base directory for all output files
        """
        self.output_dir = output_dir
        self.twitter_dir = os.path.join(output_dir, "twitter")
        self.tiktok_dir = os.path.join(output_dir, "tiktok")
        self.youtube_dir = os.path.join(output_dir, "youtube")
        self.audio_dir = os.path.join(output_dir, "audio")
        self.transcripts_dir = os.path.join(output_dir, "transcripts")
        self.collages_dir = os.path.join(output_dir, "collages")
        
        # Create output directories
        os.makedirs(self.twitter_dir, exist_ok=True)
        os.makedirs(self.tiktok_dir, exist_ok=True)
        os.makedirs(self.youtube_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)
        os.makedirs(self.collages_dir, exist_ok=True)
        
        # Initialize pipeline steps
        self.steps = self._create_default_steps()
        
        logger.info(f"VideoProcessor initialized with output directory: {output_dir}")
        
    def _create_default_steps(self) -> List[BaseStep]:
        """Create the default pipeline steps.
        
        Returns:
            A list of pipeline steps in execution order
        """
        return [
            IdentifyPlatformStep(),
            DownloadVideoStep(output_dir=self.output_dir),
            ExtractAudioStep(output_dir=self.audio_dir),
            TranscribeAudioStep(output_dir=self.transcripts_dir),
            CreateCollageStep(output_dir=self.collages_dir)
        ]
    
    def get_step(self, step_name: str) -> Optional[BaseStep]:
        """Get a step by name.
        
        Args:
            step_name: The name of the step to get
            
        Returns:
            The step if found, None otherwise
        """
        for step in self.steps:
            if step.name == step_name:
                return step
        return None
    
    def enable_step(self, step_name: str, enabled: bool = True) -> None:
        """Enable or disable a step by name.
        
        Args:
            step_name: The name of the step to enable/disable
            enabled: Whether to enable or disable the step
        """
        step = self.get_step(step_name)
        if step:
            step.enabled = enabled
            logger.info(f"Step '{step_name}' {'enabled' if enabled else 'disabled'}")
        else:
            logger.error(f"Unknown step name: {step_name}")
    
    def add_step(self, step: BaseStep, position: int = -1) -> None:
        """Add a custom step to the pipeline.
        
        Args:
            step: The step to add
            position: The position to insert the step at, -1 for append
        """
        if position < 0 or position >= len(self.steps):
            self.steps.append(step)
            logger.info(f"Added step '{step.name}' at the end of the pipeline")
        else:
            self.steps.insert(position, step)
            logger.info(f"Added step '{step.name}' at position {position}")
    
    def download_video(self, url: str, language_code: str = "es") -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Download and process a video from a URL.
        
        Args:
            url: The URL of the video to download
            language_code: The language code for transcription (default: es)
            
        Returns:
            A tuple of (video_path, audio_path, srt_path, collage_path), any of which may be None if that step failed
        """
        # Initialize the context
        context = VideoContext(url=url)
        context.metadata["language_code"] = language_code
        
        # Run the pipeline
        for step in self.steps:
            # Keep track of errors before this step
            previous_errors = context.errors.copy()
            
            # Run the step
            context = step(context)
            
            # Only break on critical early steps (platform identification, download, or audio extraction)
            if context.has_errors() and step.name in ["identify_platform", "download_video", "extract_audio"]:
                logger.warning(f"Pipeline stopped due to critical error in {step.name}: {context.errors}")
                break
                
            # For non-critical steps (transcription, collage), log errors but continue
            if context.has_errors() and len(context.errors) > len(previous_errors):
                new_errors = context.errors[len(previous_errors):]
                logger.warning(f"Non-critical errors in {step.name}, continuing pipeline: {new_errors}")
        
        logger.info(f"Pipeline completed. Results: video_path={context.video_path}, audio_path={context.audio_path}, srt_path={context.srt_path}, collage_path={context.collage_path}")
        
        return context.video_path, context.audio_path, context.srt_path, context.collage_path
    
    def download_video_extended(self, url: str, language_code: str = "es") -> Dict[str, Any]:
        """Download and process a video from a URL with extended results.
        
        Args:
            url: The URL of the video to download
            language_code: The language code for transcription (default: es)
            
        Returns:
            A dictionary containing file paths and raw SRT content
        """
        # Initialize the context
        context = VideoContext(url=url)
        context.metadata["language_code"] = language_code
        
        # Run the pipeline
        for step in self.steps:
            # Keep track of errors before this step
            previous_errors = context.errors.copy()
            
            # Run the step
            context = step(context)
            
            # Only break on critical early steps (platform identification, download, or audio extraction)
            if context.has_errors() and step.name in ["identify_platform", "download_video", "extract_audio"]:
                logger.warning(f"Pipeline stopped due to critical error in {step.name}: {context.errors}")
                break
                
            # For non-critical steps (transcription, collage), log errors but continue
            if context.has_errors() and len(context.errors) > len(previous_errors):
                new_errors = context.errors[len(previous_errors):]
                logger.warning(f"Non-critical errors in {step.name}, continuing pipeline: {new_errors}")
        
        # Initialize result dictionary
        result = {
            "video_path": context.video_path,
            "audio_path": context.audio_path,
            "srt_path": context.srt_path,
            "collage_path": context.collage_path,
            "transcript_text": context.transcript_text,
            "srt_content": None,
            "metadata": context.metadata  # Include metadata in the result
        }
        
        # Get SRT content if available
        if context.srt_path and os.path.exists(context.srt_path):
            try:
                with open(context.srt_path, "r", encoding="utf-8") as srt_file:
                    result["srt_content"] = srt_file.read()
                    logger.info(f"Successfully read SRT content")
            except Exception as e:
                logger.error(f"Error reading SRT content: {str(e)}")
        
        logger.info(f"Extended pipeline completed. Results include raw data and file paths: {', '.join(key for key, val in result.items() if val)}")
        
        return result
    
    def get_srt_content(self, srt_path: str) -> Optional[str]:
        """Get the raw content of an SRT file as a string.
        
        Args:
            srt_path: Path to the SRT file
            
        Returns:
            String content of the SRT file, or None if the file doesn't exist or there's an error
        """
        if not srt_path or not os.path.exists(srt_path):
            logger.error(f"SRT path is missing or does not exist: {srt_path}")
            return None
            
        try:
            with open(srt_path, "r", encoding="utf-8") as srt_file:
                return srt_file.read()
        except Exception as e:
            logger.error(f"Error reading SRT content: {str(e)}")
            return None 