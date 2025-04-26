import os
import uuid
import logging
from typing import Optional, Tuple, Dict, Any, List, Callable
import snscrape.modules.twitter as sntwitter
import yt_dlp
import subprocess
from dataclasses import dataclass, field
import assemblyai as aai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure AssemblyAI
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    logger.info("AssemblyAI API key configured successfully")
else:
    logger.warning("ASSEMBLYAI_API_KEY environment variable is not set, transcription will be disabled")

@dataclass
class VideoContext:
    """Data container for passing information between pipeline steps."""
    url: str
    video_id: Optional[str] = None
    platform: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None
    transcript_srt: Optional[str] = None
    srt_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

class VideoDownloader:
    def __init__(self, output_dir: str = "generated_images/videos"):
        self.output_dir = output_dir
        self.twitter_dir = os.path.join(output_dir, "twitter")
        self.tiktok_dir = os.path.join(output_dir, "tiktok")
        self.audio_dir = os.path.join(output_dir, "audio")
        self.transcripts_dir = os.path.join(output_dir, "transcripts")
        os.makedirs(self.twitter_dir, exist_ok=True)
        os.makedirs(self.tiktok_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)
        
        # Define the default pipeline steps
        self.pipeline_steps = [
            self._identify_platform,
            self._download_video,
            self._extract_audio,
            self._transcribe_audio
        ]
        
        # Step configuration (enabled/disabled)
        self.step_config = {
            "identify_platform": True,
            "download_video": True,
            "extract_audio": True,
            "transcribe_audio": ASSEMBLYAI_API_KEY is not None
        }
        
        logger.info(f"VideoDownloader initialized with output directory: {output_dir}")

    def _get_unique_filename(self, video_id: str) -> str:
        """Generate a unique filename for the downloaded video based on video ID."""
        unique_id = uuid.uuid4().hex[:8]
        return f"{video_id}_{unique_id}"
    
    def _identify_platform(self, context: VideoContext) -> VideoContext:
        """Identify platform and extract video ID from URL."""
        if not self.step_config["identify_platform"]:
            logger.info("Platform identification step disabled")
            return context
            
        try:
            url = context.url
            if "twitter.com" in url or "x.com" in url:
                video_id = url.split('/')[-1].split('?')[0]
                context.video_id = video_id
                context.platform = "twitter"
                logger.info(f"Identified as Twitter video: {video_id}")
            elif "tiktok.com" in url:
                # TikTok URLs can be in different formats
                if "/video/" in url:
                    video_id = url.split('/video/')[-1].split('?')[0]
                else:
                    # For share URLs like vm.tiktok.com/XXXXXXX/
                    video_id = url.split('/')[-1].split('?')[0]
                context.video_id = video_id
                context.platform = "tiktok"
                logger.info(f"Identified as TikTok video: {video_id}")
            else:
                error_msg = f"Unsupported platform for URL: {url}"
                logger.error(error_msg)
                context.errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error identifying platform: {str(e)}"
            logger.error(error_msg)
            context.errors.append(error_msg)
            
        return context
    
    def _download_video(self, context: VideoContext) -> VideoContext:
        """Download video from identified platform."""
        if not self.step_config["download_video"]:
            logger.info("Video download step disabled")
            return context
            
        # Skip if there were errors or if platform/video_id is missing
        if context.errors or not context.platform or not context.video_id:
            return context
            
        try:
            # Set the appropriate output directory
            if context.platform == "twitter":
                output_dir = self.twitter_dir
            elif context.platform == "tiktok":
                output_dir = self.tiktok_dir
            else:
                error_msg = f"Unsupported platform: {context.platform}"
                logger.error(error_msg)
                context.errors.append(error_msg)
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
            logger.info(f"Starting download for {context.platform} video: {context.url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(context.url, download=True)
                if info:
                    # Get the actual filename with extension
                    context.video_path = f"{output_path}.{info.get('ext', 'mp4')}"
                    context.metadata["video_info"] = info
                    logger.info(f"Successfully downloaded {context.platform} video to: {context.video_path}")
                else:
                    error_msg = f"No video information found for {context.platform} video: {context.url}"
                    logger.error(error_msg)
                    context.errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error downloading video: {str(e)}"
            logger.error(error_msg)
            context.errors.append(error_msg)
            
        return context
    
    def _extract_audio(self, context: VideoContext) -> VideoContext:
        """Extract audio from downloaded video."""
        if not self.step_config["extract_audio"]:
            logger.info("Audio extraction step disabled")
            return context
            
        # Skip if there were errors or if video_path is missing
        if context.errors or not context.video_path or not os.path.exists(context.video_path):
            return context
            
        try:
            # Generate output filename for audio
            basename = os.path.basename(context.video_path).split('.')[0]
            audio_path = os.path.join(self.audio_dir, f"{basename}.mp3")
            
            # Use FFmpeg to extract audio
            logger.info(f"Extracting audio from {context.video_path} to {audio_path}")
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
                logger.error(error_msg)
                context.errors.append(error_msg)
            else:
                context.audio_path = audio_path
                logger.info(f"Successfully extracted audio to: {audio_path}")
                
        except Exception as e:
            error_msg = f"Error extracting audio: {str(e)}"
            logger.error(error_msg)
            context.errors.append(error_msg)
            
        return context
    
    def _transcribe_audio(self, context: VideoContext) -> VideoContext:
        """Transcribe audio using AssemblyAI."""
        if not self.step_config["transcribe_audio"]:
            logger.info("Audio transcription step disabled")
            return context
            
        # Skip if there were errors or if audio_path is missing
        if (context.errors or not context.audio_path or 
            not os.path.exists(context.audio_path) or not ASSEMBLYAI_API_KEY):
            return context
            
        try:
            logger.info(f"Starting transcription for audio: {context.audio_path}")
            
            # Convert local file path to a URL that AssemblyAI can access
            # For local files, we need to upload them first
            logger.info("Uploading audio file to AssemblyAI")
            transcriber = aai.Transcriber()
            audio_url = transcriber.upload_file(context.audio_path)
            
            # Create transcription config with Spanish language (can be configured)
            language_code = context.metadata.get("language_code", "es")  # Default to Spanish
            config = aai.TranscriptionConfig(
                language_code=language_code,
                punctuate=True,  # Enable automatic punctuation
                format_text=True  # Enable text formatting
            )
            
            # Create a transcriber object with config
            transcriber = aai.Transcriber(config=config)
            
            # Start the transcription
            logger.info("Submitting transcription job to AssemblyAI")
            transcript = transcriber.transcribe(audio_url)
            
            if transcript.status == aai.TranscriptStatus.error:
                error_message = transcript.error
                logger.error(f"Transcription failed with error: {error_message}")
                context.errors.append(f"Transcription failed: {error_message}")
                return context
            
            logger.info("Transcription completed successfully")
            
            # Get the transcript text and SRT
            context.transcript_text = transcript.text
            context.transcript_srt = transcript.export_subtitles_srt()
            
            # Save SRT to file
            basename = os.path.basename(context.audio_path).split('.')[0]
            srt_path = os.path.join(self.transcripts_dir, f"{basename}.srt")
            
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(context.transcript_srt)
                
            context.srt_path = srt_path
            logger.info(f"Successfully saved transcript SRT to: {srt_path}")
            
        except Exception as e:
            error_msg = f"Error transcribing audio: {str(e)}"
            logger.error(error_msg)
            context.errors.append(error_msg)
            
        return context
    
    def enable_step(self, step_name: str, enabled: bool = True) -> None:
        """Enable or disable a specific pipeline step."""
        if step_name in self.step_config:
            self.step_config[step_name] = enabled
            logger.info(f"Step '{step_name}' {'enabled' if enabled else 'disabled'}")
        else:
            logger.error(f"Unknown step name: {step_name}")
    
    def add_custom_step(self, step_function: Callable[[VideoContext], VideoContext], position: int = -1) -> None:
        """Add a custom step to the pipeline at the specified position."""
        if position < 0 or position >= len(self.pipeline_steps):
            self.pipeline_steps.append(step_function)
        else:
            self.pipeline_steps.insert(position, step_function)
        logger.info(f"Added custom step at position {position if position >= 0 else 'end'}")
    
    def download_video(self, url: str, language_code: str = "es") -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Process video through the pipeline.
        
        Args:
            url: The URL of the post containing the video
            language_code: The language code to use for transcription (default: es)
            
        Returns:
            Tuple with:
            - The path to the downloaded video file, or None if download failed
            - The path to the extracted audio file, or None if extraction failed
            - The path to the transcript SRT file, or None if transcription failed
        """
        # Initialize context
        context = VideoContext(url=url)
        context.metadata["language_code"] = language_code
        
        # Run through pipeline steps
        for step in self.pipeline_steps:
            context = step(context)
            
            # Stop processing if there are errors
            if context.errors:
                logger.warning(f"Pipeline stopped due to errors: {context.errors}")
                break
        
        return context.video_path, context.audio_path, context.srt_path

# For backward compatibility
TwitterDownloader = VideoDownloader 