# app/main.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
import sys
from app.routers import example, transcription, image_generation

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

# Create logger for this module
logger = logging.getLogger(__name__)

app = FastAPI()

# Include routers
app.include_router(example.router)
app.include_router(transcription.router)
app.include_router(image_generation.router)

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