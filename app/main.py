# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
from app.routers import example, transcription, image_generation, svg_generation, audio_processing, video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set DEBUG level for our specific modules
logging.getLogger('app.services.image_generator').setLevel(logging.DEBUG)
logging.getLogger('app.routers.image_generation').setLevel(logging.DEBUG)
logging.getLogger('app.routers.svg_generation').setLevel(logging.DEBUG)
logging.getLogger('app.services.twitter_downloader').setLevel(logging.DEBUG)
logging.getLogger('app.routers.twitter_video').setLevel(logging.DEBUG)
logging.getLogger('app.services.video_manager').setLevel(logging.INFO)

# Create logger for this module
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# API Key middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Skip API key check for certain paths
    path = request.url.path
    
    # Skip API key check for OPTIONS requests (preflight)
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Public paths that don't require API key
    public_paths = [
        "/",  # Root/health check (exact match)
        "/video/serve/",  # Video files
        "/video/serve-audio/",  # Audio files
        "/video/serve-transcript/",  # Transcript files
        "/video/serve-collage/",  # Collage images
    ]
    
    # Check if the path is public (exact match for root, prefix match for others)
    is_public_path = path == "/" or any(
        path.startswith(public_path) for public_path in public_paths if public_path != "/"
    )
    
    if is_public_path:
        return await call_next(request)
    
    # Get API key from environment
    api_key = os.getenv("API_KEY")
    if not api_key:
        logger.error("API_KEY environment variable not set")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Server configuration error"}
        )
    
    # Check if the API key is in the request headers
    request_api_key = request.headers.get("x-api-key")
    if not request_api_key or request_api_key != api_key:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or missing API key"}
        )
    
    return await call_next(request)

# Include routers
app.include_router(example.router)
app.include_router(transcription.router)
app.include_router(image_generation.router)
app.include_router(svg_generation.router)
app.include_router(audio_processing.router)
app.include_router(video.router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    logger.info("Application started")

# Add root route for health checks
@app.get("/")
async def root():
    return JSONResponse({
        "status": "ok",
        "message": "API is running",
        "version": "1.0.0"
    })

# Import and include your routers here
# Example:
# from app.routers import example_router
# app.include_router(example_router.router)