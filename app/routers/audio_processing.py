from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
from io import BytesIO
from pydub import AudioSegment
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/audio",
    tags=["audio"],
    responses={404: {"description": "Not found"}},
)

class AudioTrimRequest(BaseModel):
    original: str
    modified: str

def download_audio(url: str) -> AudioSegment:
    """Download audio from a URL and return as AudioSegment."""
    try:
        logger.info(f"Downloading audio from: {url}")
        r = requests.get(url)
        r.raise_for_status()
        return AudioSegment.from_file(BytesIO(r.content))
    except Exception as e:
        logger.error(f"Error downloading audio from {url}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download audio: {str(e)}"
        )

@router.post("/trim", response_class=StreamingResponse)
def trim_audio(data: AudioTrimRequest):
    """Trim the modified audio to match the duration of the original audio."""
    try:
        logger.info("Starting audio trimming process")
        audio_original = download_audio(data.original)
        audio_modified = download_audio(data.modified)

        duration = len(audio_original)
        logger.info(f"Original audio duration: {duration}ms")
        logger.info(f"Modified audio duration: {len(audio_modified)}ms")
        
        if len(audio_modified) < duration:
            logger.warning("Modified audio is shorter than original, returning unmodified")
            trimmed = audio_modified
        else:
            logger.info(f"Trimming modified audio to: {duration}ms")
            trimmed = audio_modified[:duration]

        out_io = BytesIO()
        logger.info("Exporting trimmed audio to MP3 format")
        trimmed.export(out_io, format="mp3")
        out_io.seek(0)

        logger.info("Audio trimming completed successfully")
        return StreamingResponse(
            out_io, 
            media_type="audio/mpeg", 
            headers={"Content-Disposition": "inline; filename=trimmed.mp3"}
        )
    except Exception as e:
        logger.exception("An unexpected error occurred during audio trimming")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 