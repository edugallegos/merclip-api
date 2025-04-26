import os
import assemblyai as aai
from dotenv import load_dotenv
from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.context import VideoContext

# Load environment variables for API key
load_dotenv()

# Configure AssemblyAI
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

class TranscribeAudioStep(BaseStep):
    """Step to transcribe audio using AssemblyAI."""
    
    def __init__(self, output_dir: str = "generated_images/videos/transcripts", enabled: bool = True):
        # Auto-disable if no API key is available
        if not ASSEMBLYAI_API_KEY:
            enabled = False
        
        super().__init__("transcribe_audio", enabled)
        self.transcripts_dir = output_dir
        os.makedirs(self.transcripts_dir, exist_ok=True)
        
        if not ASSEMBLYAI_API_KEY:
            self.logger.warning("No AssemblyAI API key found, transcription step disabled")
    
    def process(self, context: VideoContext) -> VideoContext:
        """Process the video context to transcribe the audio.
        
        Args:
            context: The video context containing audio_path
            
        Returns:
            The updated video context with transcript_text, transcript_srt, and srt_path set
        """
        # Skip if audio_path is missing or doesn't exist
        if not context.audio_path or not os.path.exists(context.audio_path):
            self.logger.error("Missing or nonexistent audio_path, cannot transcribe")
            context.add_error("Missing or nonexistent audio_path")
            return context
        
        # Skip if no API key is available
        if not ASSEMBLYAI_API_KEY:
            self.logger.warning("No AssemblyAI API key found, skipping transcription")
            return context
        
        self.logger.info(f"Starting transcription for audio: {context.audio_path}")
        
        try:
            # Upload the audio file to AssemblyAI
            self.logger.info("Uploading audio file to AssemblyAI")
            transcriber = aai.Transcriber()
            audio_url = transcriber.upload_file(context.audio_path)
            
            # Create transcription config with the specified language
            language_code = context.get_language_code()
            config = aai.TranscriptionConfig(
                language_code=language_code,
                punctuate=True,  # Enable automatic punctuation
                format_text=True  # Enable text formatting
            )
            
            # Create a transcriber object with config
            transcriber = aai.Transcriber(config=config)
            
            # Start the transcription
            self.logger.info(f"Submitting transcription job to AssemblyAI with language: {language_code}")
            transcript = transcriber.transcribe(audio_url)
            
            if transcript.status == aai.TranscriptStatus.error:
                error_message = transcript.error
                self.logger.error(f"Transcription failed with error: {error_message}")
                context.add_error(f"Transcription failed: {error_message}")
                return context
            
            self.logger.info("Transcription completed successfully")
            
            # Get the transcript text and SRT
            context.transcript_text = transcript.text
            context.transcript_srt = transcript.export_subtitles_srt()
            
            # Save SRT to file
            basename = os.path.basename(context.audio_path).split('.')[0]
            srt_path = os.path.join(self.transcripts_dir, f"{basename}.srt")
            
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(context.transcript_srt)
                
            context.srt_path = srt_path
            self.logger.info(f"Successfully saved transcript SRT to: {srt_path}")
            
        except Exception as e:
            error_msg = f"Error transcribing audio: {str(e)}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
        
        return context 