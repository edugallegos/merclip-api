from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Query, Body
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
from app.utils.url import get_base_url

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
    
class AIReviewUpdate(BaseModel):
    ai_review: str
    
    class Config:
        # Add example for documentation
        schema_extra = {
            "example": {
                "ai_review": "This video contains educational content with a speaker explaining technical concepts."
            }
        }

@router.post("/download", response_model=VideoResponse)
async def download_video(request: VideoRequest, request_info: Request):
    """
    Download a video from a Twitter/X or TikTok post URL.
    Extracts audio, generates transcription, and creates a collage if enabled.
    Returns SRT content as string when available.
    """
    try:
        logger.info(f"Received video download request for URL: {request.url}")
        logger.info(f"Language code: {request.language_code}")
        
        # Determine platform from URL for response
        url = str(request.url)
        platform = "unknown"
        if "twitter.com" in url or "x.com" in url:
            platform = "twitter"
        elif "tiktok.com" in url:
            platform = "tiktok"
        
        logger.info(f"Detected platform: {platform}")
        
        # Download the video through the extended pipeline
        logger.info("Starting video download and processing pipeline")
        result = video_processor.download_video_extended(url, request.language_code)
        
        logger.debug(f"Pipeline result keys: {', '.join(result.keys())}")
        
        file_path = result["video_path"]
        audio_path = result["audio_path"]
        srt_path = result["srt_path"]
        collage_path = result["collage_path"]
        srt_content = result["srt_content"]
        transcript_text = result["transcript_text"]
        
        logger.info(f"Pipeline completed with results: file_path={file_path}, audio_path={audio_path}, srt_path={srt_path}, collage_path={collage_path}")
        logger.debug(f"SRT content available: {srt_content is not None}")
        logger.debug(f"Transcript text available: {transcript_text is not None}")
        
        # Explicit collage check
        if collage_path:
            if os.path.exists(collage_path):
                logger.info(f"Collage file exists at {collage_path}")
            else:
                logger.warning(f"Collage path was provided but file does not exist at {collage_path}")
        
        if file_path and os.path.exists(file_path):
            # Extract video_id and filename from the file_path
            filename = os.path.basename(file_path)
            video_id = filename.split('_')[0]
            logger.info(f"Extracted video_id: {video_id} from filename: {filename}")
            
            # Generate URL for the file
            base_url = get_base_url(request_info)
            file_url = f"{base_url}video/serve/{platform}/{video_id}/{filename}"
            logger.debug(f"Generated file_url: {file_url}")
            
            # Generate audio URL if audio was extracted
            audio_url = None
            if audio_path and os.path.exists(audio_path):
                audio_filename = os.path.basename(audio_path)
                audio_url = f"{base_url}video/serve-audio/{video_id}/{audio_filename}"
                logger.debug(f"Generated audio_url: {audio_url}")
            
            # Generate SRT URL if transcription was successful
            srt_url = None
            if srt_path and os.path.exists(srt_path):
                srt_filename = os.path.basename(srt_path)
                srt_url = f"{base_url}video/serve-transcript/{video_id}/{srt_filename}"
                logger.debug(f"Generated srt_url: {srt_url}")
            
            # Generate collage URL if collage was created
            collage_url = None
            if collage_path and os.path.exists(collage_path):
                collage_filename = os.path.basename(collage_path)
                collage_url = f"{base_url}video/serve-collage/{video_id}/{collage_filename}"
                logger.debug(f"Generated collage_url: {collage_url}")
            
            # Store the processed video in the database
            now = datetime.utcnow()
            logger.info(f"Creating ProcessedVideo object for database storage")
            try:
                # Create a metadata dictionary with useful information
                metadata = {
                    "download_timestamp": now.isoformat(),
                    "source": "api_download",
                    "processed_at": now.isoformat(),
                    "language": request.language_code,
                    "has_transcript": srt_path is not None,
                    "has_collage": collage_path is not None,
                    "video_size": os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
                }
                
                logger.debug(f"Created metadata for ProcessedVideo: {metadata}")
                
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
                    language_code=request.language_code,
                    ai_review=None,
                    metadata=metadata  # Use the explicitly created metadata dictionary
                )
                logger.debug(f"ProcessedVideo object created successfully")
                logger.debug(f"ProcessedVideo metadata: {processed_video.metadata}")
            except Exception as model_err:
                logger.error(f"Error creating ProcessedVideo model: {str(model_err)}")
                raise
            
            try:
                logger.info(f"Saving video to database via VideoManager")
                video_manager.save_video(processed_video)
                logger.info(f"Successfully saved video to database: {video_id}")
            except Exception as db_err:
                logger.error(f"Error saving video to database: {str(db_err)}")
                raise
            
            logger.info(f"Preparing response for video_id: {video_id}")
            response = VideoResponse(
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
            logger.info(f"Download request completed successfully for URL: {request.url}")
            return response
        else:
            logger.error(f"File not found: file_path={file_path}, exists={os.path.exists(file_path) if file_path else False}")
            raise HTTPException(
                status_code=404,
                detail=f"No video found in the provided {platform} URL or download failed"
            )
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error processing video download for URL {request.url}: {str(e)}")
        logger.error(f"Error traceback: {error_trace}")
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

@router.put("/ai-review/{video_id}", response_model=ProcessedVideo)
async def update_ai_review(
    video_id: str, 
    review_update: AIReviewUpdate = Body(..., 
        example={"ai_review": "This video contains educational content"})
):
    """
    Update the AI review of a processed video.
    This endpoint allows adding machine-generated analysis or review of the video content.
    
    Example request body:
    ```json
    {
        "ai_review": "This video contains educational content with a speaker explaining technical concepts."
    }
    ```
    """
    try:
        logger.info(f"Received AI review update request for video_id: {video_id}")
        logger.debug(f"AI review content: {review_update.ai_review[:100]}...")  # Log first 100 chars
        
        updated_video = video_manager.update_ai_review(video_id, review_update.ai_review)
        
        if not updated_video:
            logger.warning(f"Video not found with ID: {video_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Video not found with ID: {video_id}"
            )
        
        logger.info(f"Successfully updated AI review for video_id: {video_id}")
        return updated_video
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error updating AI review for video_id {video_id}: {str(e)}")
        logger.error(f"Request data type: {type(review_update)}")
        logger.error(f"Error trace: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to update AI review: {str(e)}")

@router.put("/ai-review-raw/{video_id}")
async def update_ai_review_raw(video_id: str, request: Request):
    """
    Raw endpoint for debugging - update the AI review of a processed video.
    This accepts raw JSON and handles it manually to diagnose issues.
    """
    try:
        logger.info(f"Received raw AI review update request for video_id: {video_id}")
        
        # Get the raw request body
        try:
            body_bytes = await request.body()
            body_str = body_bytes.decode('utf-8')
            logger.info(f"Raw request body: '{body_str}'")
            
            if not body_bytes:
                return {"error": "Empty request body", "status": "failed"}
            
            # Try to parse as JSON
            try:
                import json
                body_json = json.loads(body_str)
                logger.info(f"Parsed JSON: {body_json}")
                
                # Extract ai_review field
                if "ai_review" not in body_json:
                    return {"error": "Missing 'ai_review' field", "status": "failed"}
                
                ai_review = body_json["ai_review"]
                logger.info(f"Extracted ai_review value: '{ai_review}'")
                
                # Try to get the video first to see if that's where the error is
                try:
                    video = video_manager.get_video(video_id)
                    if not video:
                        return {"error": f"Video not found with ID: {video_id}", "status": "failed"}
                    
                    logger.info(f"Successfully retrieved video with ID: {video_id}")
                    
                    # Update the video
                    try:
                        updated_video = video_manager.update_ai_review(video_id, ai_review)
                        logger.info(f"Successfully updated AI review for video_id: {video_id}")
                        
                        # Return a simplified response
                        return {
                            "status": "success", 
                            "message": "AI review updated successfully",
                            "video_id": video_id
                        }
                    except Exception as update_err:
                        logger.error(f"Error in update_ai_review: {str(update_err)}")
                        return {"error": f"Failed to update AI review: {str(update_err)}", "status": "failed"}
                        
                except Exception as get_err:
                    logger.error(f"Error in get_video: {str(get_err)}")
                    return {"error": f"Failed to get video: {str(get_err)}", "status": "failed"}
                
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {str(json_err)}")
                return {"error": f"Invalid JSON: {str(json_err)}", "status": "failed"}
                
        except Exception as req_err:
            logger.error(f"Request body read error: {str(req_err)}")
            return {"error": f"Failed to read request body: {str(req_err)}", "status": "failed"}
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Unexpected error in raw endpoint for video_id {video_id}: {str(e)}")
        logger.error(f"Error trace: {error_trace}")
        return {"error": f"Unexpected error: {str(e)}", "status": "failed"}

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
async def serve_video(platform: str, video_id: str, filename: str, request: Request):
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
            # Get the origin from the request headers
            origin = request.headers.get("origin")
            
            # Create response with CORS headers
            response = FileResponse(
                path=video_path,
                media_type="video/mp4",
                filename=filename
            )
            
            # Add CORS headers manually
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"

            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            
            return response
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {filename}"
            )
    
    except Exception as e:
        logger.error(f"Error serving video file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve video: {str(e)}")

@router.get("/serve-audio/{video_id}/{filename}")
async def serve_audio(video_id: str, filename: str, request: Request):
    """
    Serve a specific audio file by video ID and filename.
    This endpoint provides direct access to the extracted audio file.
    """
    try:
        audio_dir = video_processor.audio_dir
        audio_path = os.path.join(audio_dir, filename)
        
        if os.path.exists(audio_path) and filename.startswith(video_id):
            # Get the origin from the request headers
            origin = request.headers.get("origin", "*")
            
            # Create response with CORS headers
            response = FileResponse(
                path=audio_path,
                media_type="audio/mpeg",
                filename=filename
            )
            
            # Add CORS headers manually
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            
            return response
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Audio file not found: {filename}"
            )
    
    except Exception as e:
        logger.error(f"Error serving audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve audio: {str(e)}")

@router.get("/serve-transcript/{video_id}/{filename}")
async def serve_transcript(video_id: str, filename: str, request: Request):
    """
    Serve a specific SRT transcript file by video ID and filename.
    This endpoint provides direct access to the transcript file.
    """
    try:
        transcript_dir = video_processor.transcripts_dir
        transcript_path = os.path.join(transcript_dir, filename)
        
        if os.path.exists(transcript_path) and filename.startswith(video_id):
            # Get the origin from the request headers
            origin = request.headers.get("origin", "*")
            
            # Create response with CORS headers
            response = FileResponse(
                path=transcript_path,
                media_type="application/x-subrip",
                filename=filename
            )
            
            # Add CORS headers manually
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            
            return response
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript file not found: {filename}"
            )
    
    except Exception as e:
        logger.error(f"Error serving transcript file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve transcript: {str(e)}")

@router.get("/serve-collage/{video_id}/{filename}")
async def serve_collage(video_id: str, filename: str, request: Request):
    """
    Serve a specific collage image file by video ID and filename.
    This endpoint provides direct access to the collage image.
    """
    try:
        collage_dir = video_processor.collages_dir
        collage_path = os.path.join(collage_dir, filename)
        
        if os.path.exists(collage_path) and filename.startswith(video_id):
            # Get the origin from the request headers
            origin = request.headers.get("origin", "*")
            
            # Create response with CORS headers
            response = FileResponse(
                path=collage_path,
                media_type="image/jpeg",
                filename=filename
            )
            
            # Add CORS headers manually
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            
            return response
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