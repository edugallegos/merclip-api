from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import os
import logging
from typing import Optional, List
from app.services.video_pipeline import VideoProcessor
from app.services.video_manager import VideoManager
from app.models.video import ProcessedVideo, VideoStatusEnum
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/video",
    tags=["video"],
    responses={404: {"description": "Not found"}},
)

# Initialize the VideoProcessor and VideoManager
video_processor = VideoProcessor()
video_manager = VideoManager()

# Configure pipeline steps as needed
# Example: Disable transcription
# video_processor.enable_step("transcribe_audio", False)

class VideoRequest(BaseModel):
    url: HttpUrl
    language_code: Optional[str] = "es"  # Default language for transcription
    
class VideoResponse(BaseModel):
    status: str
    message: str
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    srt_path: Optional[str] = None
    srt_url: Optional[str] = None
    collage_path: Optional[str] = None
    collage_url: Optional[str] = None
    srt_content: Optional[str] = None     # Raw SRT content as string
    transcript_text: Optional[str] = None  # Plain text transcript
    platform: Optional[str] = None
    video_id: Optional[str] = None
    errors: List[str] = []

class VideoListResponse(BaseModel):
    videos: List[ProcessedVideo]
    total: int
    limit: int
    offset: int
    status: Optional[str] = None
    
class VideoStatusUpdate(BaseModel):
    status: VideoStatusEnum
    
@router.post("/download", response_model=VideoResponse)
async def download_video(request: VideoRequest, request_info: Request):
    """
    Download a video from a Twitter/X or TikTok post URL.
    Extracts audio, generates transcription, and creates a collage if enabled.
    Returns SRT content as string when available.
    """
    try:
        # Determine platform from URL for response
        url = str(request.url)
        platform = "unknown"
        if "twitter.com" in url or "x.com" in url:
            platform = "twitter"
        elif "tiktok.com" in url:
            platform = "tiktok"
        
        # Download the video through the extended pipeline
        result = video_processor.download_video_extended(url, request.language_code)
        file_path = result["video_path"]
        audio_path = result["audio_path"]
        srt_path = result["srt_path"]
        collage_path = result["collage_path"]
        srt_content = result["srt_content"]
        transcript_text = result["transcript_text"]
        
        logger.info(f"Router received: file_path={file_path}, audio_path={audio_path}, srt_path={srt_path}, collage_path={collage_path}")
        
        # Explicit collage check
        if collage_path:
            if os.path.exists(collage_path):
                logger.info(f"Router verified: Collage file exists at {collage_path}")
            else:
                logger.warning(f"Router warning: Collage path was provided but file does not exist at {collage_path}")
        
        if file_path and os.path.exists(file_path):
            # Extract video_id and filename from the file_path
            filename = os.path.basename(file_path)
            video_id = filename.split('_')[0]
            
            # Generate URL for the file
            base_url = str(request_info.base_url)
            file_url = f"{base_url}video/serve/{platform}/{video_id}/{filename}"
            
            # Generate audio URL if audio was extracted
            audio_url = None
            if audio_path and os.path.exists(audio_path):
                audio_filename = os.path.basename(audio_path)
                audio_url = f"{base_url}video/serve-audio/{video_id}/{audio_filename}"
            
            # Generate SRT URL if transcription was successful
            srt_url = None
            if srt_path and os.path.exists(srt_path):
                srt_filename = os.path.basename(srt_path)
                srt_url = f"{base_url}video/serve-transcript/{video_id}/{srt_filename}"
            
            # Generate collage URL if collage was created
            collage_url = None
            if collage_path and os.path.exists(collage_path):
                collage_filename = os.path.basename(collage_path)
                collage_url = f"{base_url}video/serve-collage/{video_id}/{collage_filename}"
            
            # Store the processed video in the database
            now = datetime.utcnow()
            processed_video = ProcessedVideo(
                video_id=video_id,
                url=str(request.url),
                platform=platform,
                file_path=file_path,
                file_url=file_url,
                audio_path=audio_path,
                audio_url=audio_url,
                srt_path=srt_path,
                srt_url=srt_url,
                collage_path=collage_path,
                collage_url=collage_url,
                status=VideoStatusEnum.PROCESSED,
                created_at=now,
                updated_at=now,
                language_code=request.language_code
            )
            video_manager.save_video(processed_video)
            logger.info(f"Saved processed video to database: {video_id}")
            
            return VideoResponse(
                status="success",
                message=f"{platform.capitalize()} video processed successfully",
                file_path=file_path,
                file_url=file_url,
                audio_path=audio_path,
                audio_url=audio_url,
                srt_path=srt_path,
                srt_url=srt_url,
                collage_path=collage_path,
                collage_url=collage_url,
                srt_content=srt_content,
                transcript_text=transcript_text,
                platform=platform,
                video_id=video_id
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No video found in the provided {platform} URL or download failed"
            )
    
    except Exception as e:
        logger.error(f"Error processing video download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

@router.get("/library", response_model=VideoListResponse)
async def list_videos(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None
):
    """
    List processed videos, optionally filtered by status.
    Results are sorted by creation date (newest first).
    """
    try:
        # Get count before applying limit and offset
        conn = sqlite3.connect(str(video_manager.db_path))
        cursor = conn.cursor()
        
        if status:
            cursor.execute("SELECT COUNT(*) FROM processed_videos WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM processed_videos")
        
        total = cursor.fetchone()[0]
        conn.close()
        
        # Get videos with limit and offset
        videos = video_manager.get_videos(limit=limit, offset=offset, status=status)
        
        return VideoListResponse(
            videos=videos,
            total=total,
            limit=limit,
            offset=offset,
            status=status
        )
    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")

@router.put("/status/{video_id}", response_model=ProcessedVideo)
async def update_video_status(video_id: str, status_update: VideoStatusUpdate):
    """
    Update the status of a processed video.
    This can be used to mark videos as DONE after they've been used.
    """
    try:
        updated_video = video_manager.update_status(video_id, status_update.status)
        
        if not updated_video:
            raise HTTPException(
                status_code=404,
                detail=f"Video not found with ID: {video_id}"
            )
        
        return updated_video
    except Exception as e:
        logger.error(f"Error updating video status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update video status: {str(e)}")

@router.get("/twitter/{video_id}")
async def get_twitter_video(video_id: str):
    """
    Retrieve a previously downloaded Twitter video by video ID.
    This endpoint will search for a matching video file and serve it.
    """
    try:
        # Look for files with the video ID prefix in the Twitter output directory
        video_dir = video_processor.twitter_dir
        matching_files = [f for f in os.listdir(video_dir) if f.startswith(video_id)]
        
        if matching_files:
            # Use the most recently downloaded file if multiple exist
            video_path = os.path.join(video_dir, matching_files[0])
            return FileResponse(
                path=video_path,
                media_type="video/mp4",
                filename=os.path.basename(video_path)
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No downloaded video found for Twitter video ID: {video_id}"
            )
    
    except Exception as e:
        logger.error(f"Error retrieving Twitter video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve video: {str(e)}")

@router.get("/tiktok/{video_id}")
async def get_tiktok_video(video_id: str):
    """
    Retrieve a previously downloaded TikTok video by video ID.
    This endpoint will search for a matching video file and serve it.
    """
    try:
        # Look for files with the video ID prefix in the TikTok output directory
        video_dir = video_processor.tiktok_dir
        matching_files = [f for f in os.listdir(video_dir) if f.startswith(video_id)]
        
        if matching_files:
            # Use the most recently downloaded file if multiple exist
            video_path = os.path.join(video_dir, matching_files[0])
            return FileResponse(
                path=video_path,
                media_type="video/mp4",
                filename=os.path.basename(video_path)
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No downloaded video found for TikTok video ID: {video_id}"
            )
    
    except Exception as e:
        logger.error(f"Error retrieving TikTok video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve video: {str(e)}")

@router.get("/serve/{platform}/{video_id}/{filename}")
async def serve_video(platform: str, video_id: str, filename: str):
    """
    Serve a specific video file by platform, video ID, and filename.
    This endpoint provides direct access to the video file.
    """
    try:
        if platform == "twitter":
            video_dir = video_processor.twitter_dir
        elif platform == "tiktok":
            video_dir = video_processor.tiktok_dir
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform: {platform}"
            )
            
        video_path = os.path.join(video_dir, filename)
        
        if os.path.exists(video_path) and filename.startswith(video_id):
            return FileResponse(
                path=video_path,
                media_type="video/mp4",
                filename=filename
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {filename}"
            )
    
    except Exception as e:
        logger.error(f"Error serving video file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve video: {str(e)}") 

@router.get("/serve-audio/{video_id}/{filename}")
async def serve_audio(video_id: str, filename: str):
    """
    Serve a specific audio file by video ID and filename.
    This endpoint provides direct access to the extracted audio file.
    """
    try:
        audio_dir = video_processor.audio_dir
        audio_path = os.path.join(audio_dir, filename)
        
        if os.path.exists(audio_path) and filename.startswith(video_id):
            return FileResponse(
                path=audio_path,
                media_type="audio/mpeg",
                filename=filename
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Audio file not found: {filename}"
            )
    
    except Exception as e:
        logger.error(f"Error serving audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve audio: {str(e)}")

@router.get("/serve-transcript/{video_id}/{filename}")
async def serve_transcript(video_id: str, filename: str):
    """
    Serve a specific SRT transcript file by video ID and filename.
    This endpoint provides direct access to the transcript file.
    """
    try:
        transcript_dir = video_processor.transcripts_dir
        transcript_path = os.path.join(transcript_dir, filename)
        
        if os.path.exists(transcript_path) and filename.startswith(video_id):
            return FileResponse(
                path=transcript_path,
                media_type="application/x-subrip",
                filename=filename
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript file not found: {filename}"
            )
    
    except Exception as e:
        logger.error(f"Error serving transcript file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve transcript: {str(e)}")

@router.get("/serve-collage/{video_id}/{filename}")
async def serve_collage(video_id: str, filename: str):
    """
    Serve a specific collage image file by video ID and filename.
    This endpoint provides direct access to the collage image.
    """
    try:
        collage_dir = video_processor.collages_dir
        collage_path = os.path.join(collage_dir, filename)
        
        if os.path.exists(collage_path) and filename.startswith(video_id):
            return FileResponse(
                path=collage_path,
                media_type="image/jpeg",
                filename=filename
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Collage file not found: {filename}"
            )
    
    except Exception as e:
        logger.error(f"Error serving collage file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve collage: {str(e)}")

@router.get("/audio/{video_id}")
async def get_audio(video_id: str):
    """
    Retrieve a previously extracted audio by video ID.
    This endpoint will search for a matching audio file and serve it.
    """
    try:
        # Look for files with the video ID prefix in the audio output directory
        audio_dir = video_processor.audio_dir
        matching_files = [f for f in os.listdir(audio_dir) if f.startswith(video_id)]
        
        if matching_files:
            # Use the most recently created file if multiple exist
            audio_path = os.path.join(audio_dir, matching_files[0])
            return FileResponse(
                path=audio_path,
                media_type="audio/mpeg",
                filename=os.path.basename(audio_path)
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No extracted audio found for video ID: {video_id}"
            )
    
    except Exception as e:
        logger.error(f"Error retrieving audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audio: {str(e)}")

@router.get("/transcript/{video_id}")
async def get_transcript(video_id: str):
    """
    Retrieve a previously generated transcript by video ID.
    This endpoint will search for a matching SRT file and serve it.
    """
    try:
        # Look for files with the video ID prefix in the transcripts output directory
        transcript_dir = video_processor.transcripts_dir
        matching_files = [f for f in os.listdir(transcript_dir) if f.startswith(video_id)]
        
        if matching_files:
            # Use the most recently created file if multiple exist
            transcript_path = os.path.join(transcript_dir, matching_files[0])
            return FileResponse(
                path=transcript_path,
                media_type="application/x-subrip",
                filename=os.path.basename(transcript_path)
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No transcript found for video ID: {video_id}"
            )
    
    except Exception as e:
        logger.error(f"Error retrieving transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transcript: {str(e)}")

@router.get("/collage/{video_id}")
async def get_collage(video_id: str):
    """
    Retrieve a previously generated collage by video ID.
    This endpoint will search for a matching collage image and serve it.
    """
    try:
        # Look for files with the video ID prefix in the collages output directory
        collage_dir = video_processor.collages_dir
        matching_files = [f for f in os.listdir(collage_dir) if f.startswith(video_id)]
        
        if matching_files:
            # Use the most recently created file if multiple exist
            collage_path = os.path.join(collage_dir, matching_files[0])
            return FileResponse(
                path=collage_path,
                media_type="image/jpeg",
                filename=os.path.basename(collage_path)
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No collage found for video ID: {video_id}"
            )
    
    except Exception as e:
        logger.error(f"Error retrieving collage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve collage: {str(e)}")

@router.get("/library/{video_id}", response_model=ProcessedVideo)
async def get_video_by_id(video_id: str):
    """
    Get details of a specific processed video by its ID.
    Returns 404 if the video is not found.
    """
    try:
        video = video_manager.get_video(video_id)
        
        if not video:
            raise HTTPException(
                status_code=404,
                detail=f"Video not found with ID: {video_id}"
            )
        
        return video
    except Exception as e:
        logger.error(f"Error retrieving video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve video: {str(e)}") 