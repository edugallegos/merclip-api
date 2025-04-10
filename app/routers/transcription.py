from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from typing import Optional
from dotenv import load_dotenv
import logging
import assemblyai as aai

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

router = APIRouter(
    prefix="/transcription",
    tags=["transcription"],
    responses={404: {"description": "Not found"}},
)

class TranscriptionRequest(BaseModel):
    audio_url: str
    language_code: Optional[str] = "es"  # Default to Spanish

class TranscriptionResponse(BaseModel):
    text: str
    srt: str

# Get AssemblyAI API key from environment variable
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    logger.error("ASSEMBLYAI_API_KEY environment variable is not set")
    raise ValueError("ASSEMBLYAI_API_KEY environment variable is not set")

# Configure AssemblyAI
aai.settings.api_key = ASSEMBLYAI_API_KEY

@router.post("/", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest):
    try:
        logger.info(f"Starting transcription for audio URL: {request.audio_url}")
        logger.info(f"Using language code: {request.language_code}")
        
        # Create transcription config with Spanish language
        config = aai.TranscriptionConfig(
            language_code=request.language_code,
            punctuate=True,  # Enable automatic punctuation
            format_text=True  # Enable text formatting
        )
        
        # Create a transcriber object with config
        transcriber = aai.Transcriber(config=config)
        
        # Start the transcription
        logger.info("Submitting transcription job to AssemblyAI")
        transcript = transcriber.transcribe(request.audio_url)
        
        if transcript.status == aai.TranscriptStatus.error:
            error_message = transcript.error
            logger.error(f"Transcription failed with error: {error_message}")
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {error_message}"
            )
        
        logger.info("Transcription completed successfully")
        
        # Get the SRT format
        logger.info("Fetching SRT format")
        srt = transcript.export_subtitles_srt()
        
        return TranscriptionResponse(
            text=transcript.text,
            srt=srt
        )
            
    except Exception as e:
        logger.exception("An unexpected error occurred during transcription")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 