from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import os
import logging
from typing import Optional
from app.services.twitter_downloader import TwitterDownloader

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/twitter",
    tags=["twitter"],
    responses={404: {"description": "Not found"}},
)

# Initialize the TwitterDownloader service
twitter_downloader = TwitterDownloader()

class TwitterVideoRequest(BaseModel):
    url: HttpUrl
    
class TwitterVideoResponse(BaseModel):
    status: str
    message: str
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    
@router.post("/download-video", response_model=TwitterVideoResponse)
async def download_twitter_video(request: TwitterVideoRequest, request_info: Request):
    """
    Download a video from a Twitter/X post URL.
    """
    try:
        # Download the video
        file_path = twitter_downloader.download_video(str(request.url))
        
        if file_path and os.path.exists(file_path):
            # Extract tweet_id and filename from the file_path
            filename = os.path.basename(file_path)
            tweet_id = filename.split('_')[0]
            
            # Generate URL for the file
            base_url = str(request_info.base_url)
            file_url = f"{base_url}twitter/serve-video/{tweet_id}/{filename}"
            
            return TwitterVideoResponse(
                status="success",
                message="Video downloaded successfully",
                file_path=file_path,
                file_url=file_url
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="No video found in the provided tweet or download failed"
            )
    
    except Exception as e:
        logger.error(f"Error processing Twitter video download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

@router.get("/video/{tweet_id}")
async def get_twitter_video(tweet_id: str):
    """
    Retrieve a previously downloaded Twitter video by tweet ID.
    This endpoint will search for a matching video file and serve it.
    """
    try:
        # Look for files with the tweet ID prefix in the output directory
        video_dir = twitter_downloader.output_dir
        matching_files = [f for f in os.listdir(video_dir) if f.startswith(tweet_id)]
        
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
                detail=f"No downloaded video found for tweet ID: {tweet_id}"
            )
    
    except Exception as e:
        logger.error(f"Error retrieving Twitter video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve video: {str(e)}")

@router.get("/serve-video/{tweet_id}/{filename}")
async def serve_twitter_video(tweet_id: str, filename: str):
    """
    Serve a specific Twitter video file by tweet ID and filename.
    This endpoint provides direct access to the video file.
    """
    try:
        video_dir = twitter_downloader.output_dir
        video_path = os.path.join(video_dir, filename)
        
        if os.path.exists(video_path) and filename.startswith(tweet_id):
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
        logger.error(f"Error serving Twitter video file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve video: {str(e)}") 