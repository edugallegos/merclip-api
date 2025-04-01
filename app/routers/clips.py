from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from typing import Dict, Any, List
from ..models.video import VideoRequest, JobResponse, JobStatus
from ..services.ffmpeg import FFmpegService
import uuid
import os
import logging

router = APIRouter(
    prefix="/clip",
    tags=["clip"]
)

@router.post("", response_model=JobResponse)
async def create_clip(request: VideoRequest, background_tasks: BackgroundTasks):
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Save the job input and initialize status
    input_path = FFmpegService.save_job(request, job_id)
    
    # Generate FFmpeg command
    output_path = FFmpegService.get_output_path(job_id)
    command = FFmpegService.generate_command(request, output_path)
    
    # Start background task to render the video
    background_tasks.add_task(FFmpegService.render_video, job_id, command)
    
    # Return initial job status
    return JobResponse(**FFmpegService.get_job_status(job_id))

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get the status of a video rendering job."""
    status = FFmpegService.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobResponse(**status)

@router.get("/{job_id}/download")
async def download_video(job_id: str):
    """Download the rendered video file."""
    # Get job status
    status = FFmpegService.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if status["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Video not ready. Current status: {status['status']}")
    
    # Get video file path
    video_path = FFmpegService.get_output_path(job_id)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Get filename from path
    filename = os.path.basename(video_path)
    
    # Return file as download
    return Response(
        content=open(video_path, "rb").read(),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    ) 