from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from typing import Dict, Any, List
from ..models.video import VideoRequest, JobResponse, JobStatus
from ..services.ffmpeg import FFmpegService
import uuid
import asyncio
import subprocess
from datetime import datetime
import os
import logging

router = APIRouter(
    prefix="/clip",
    tags=["clip"]
)

async def render_video(job_id: str, command: List[str]):
    """Background task to render the video."""
    try:
        # Log the full command for debugging
        command_str = " ".join(command)
        print(f"Executing FFmpeg command: {command_str}")
        
        # Write command to debug log in job folder
        debug_log_path = os.path.join(FFmpegService.get_job_dir(job_id), "command.log")
        with open(debug_log_path, "w") as f:
            f.write(command_str)
        
        # Execute FFmpeg command with command list
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for the process to complete
        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode()
        stderr_text = stderr.decode()
        
        # Write output to log files
        stdout_path = os.path.join(FFmpegService.get_job_dir(job_id), "stdout.log")
        stderr_path = os.path.join(FFmpegService.get_job_dir(job_id), "stderr.log")
        
        with open(stdout_path, "w") as f:
            f.write(stdout_text)
        
        with open(stderr_path, "w") as f:
            f.write(stderr_text)
        
        if process.returncode != 0:
            # Update status to failed
            error_msg = stderr_text
            FFmpegService.update_job_status(job_id, JobStatus.FAILED, error_msg)
            print(f"Error rendering video for job {job_id}: {error_msg}")
        else:
            # Check if output file exists and has content
            output_path = FFmpegService.get_output_path(job_id)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # Update status to completed
                FFmpegService.update_job_status(job_id, JobStatus.COMPLETED)
                print(f"Successfully rendered video for job {job_id}")
            else:
                error_msg = "FFmpeg executed successfully but output file is empty or missing"
                FFmpegService.update_job_status(job_id, JobStatus.FAILED, error_msg)
                print(f"Error with output file for job {job_id}: {error_msg}")
            
    except Exception as e:
        # Update status to failed
        error_msg = str(e)
        FFmpegService.update_job_status(job_id, JobStatus.FAILED, error_msg)
        print(f"Exception while rendering video for job {job_id}: {error_msg}")

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
    background_tasks.add_task(render_video, job_id, command)
    
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