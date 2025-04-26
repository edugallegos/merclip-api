from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import os
import logging
from typing import Optional, List
from app.services.twitter_downloader import VideoDownloader

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/video",
    tags=["video"],
    responses={404: {"description": "Not found"}},
)

# Initialize the VideoDownloader service
video_downloader = VideoDownloader()

# Configure pipeline steps as needed
# Example: Disable audio extraction
# video_downloader.enable_step("extract_audio", False)

class VideoRequest(BaseModel):
    url: HttpUrl
    
class VideoResponse(BaseModel):
    status: str
    message: str
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    platform: Optional[str] = None
    errors: List[str] = []
    
@router.post("/download", response_model=VideoResponse)
async def download_video(request: VideoRequest, request_info: Request):
    """
    Download a video from a Twitter/X or TikTok post URL.
    """
    try:
        # Determine platform from URL for response
        url = str(request.url)
        platform = "unknown"
        if "twitter.com" in url or "x.com" in url:
            platform = "twitter"
        elif "tiktok.com" in url:
            platform = "tiktok"
        
        # Download the video through the pipeline
        file_path, audio_path = video_downloader.download_video(url)
        
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
            
            return VideoResponse(
                status="success",
                message=f"{platform.capitalize()} video downloaded successfully",
                file_path=file_path,
                file_url=file_url,
                audio_path=audio_path,
                audio_url=audio_url,
                platform=platform
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No video found in the provided {platform} URL or download failed"
            )
    
    except Exception as e:
        logger.error(f"Error processing video download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

@router.get("/twitter/{video_id}")
async def get_twitter_video(video_id: str):
    """
    Retrieve a previously downloaded Twitter video by video ID.
    This endpoint will search for a matching video file and serve it.
    """
    try:
        # Look for files with the video ID prefix in the Twitter output directory
        video_dir = video_downloader.twitter_dir
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
        video_dir = video_downloader.tiktok_dir
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
            video_dir = video_downloader.twitter_dir
        elif platform == "tiktok":
            video_dir = video_downloader.tiktok_dir
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
        audio_dir = video_downloader.audio_dir
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

@router.get("/audio/{video_id}")
async def get_audio(video_id: str):
    """
    Retrieve a previously extracted audio by video ID.
    This endpoint will search for a matching audio file and serve it.
    """
    try:
        # Look for files with the video ID prefix in the audio output directory
        audio_dir = video_downloader.audio_dir
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