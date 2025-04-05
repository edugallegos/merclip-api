# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import clips, template, template_clip
import os
import logging
from app.services.ffmpeg import FFmpegService

# Create logger for this module
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    # Setup logging
    log_file = FFmpegService.setup_logging()
    logger.info(f"Application started. Logs will be written to: {log_file}")
    
    # Ensure jobs directory exists
    jobs_dir = os.path.join(os.getcwd(), "jobs")
    os.makedirs(jobs_dir, exist_ok=True)

# Mount the jobs directory to serve rendered videos
jobs_dir = os.path.join(os.getcwd(), "jobs")
app.mount("/jobs", StaticFiles(directory=jobs_dir), name="jobs")

app.include_router(clips.router)
app.include_router(template.router)
app.include_router(template_clip.router)