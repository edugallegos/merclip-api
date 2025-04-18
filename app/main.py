# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
from app.routers import example, transcription, image_generation, svg_generation

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

# Create logger for this module
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# API Key middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Skip API key check for root path (health check)
    if request.url.path == "/":
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