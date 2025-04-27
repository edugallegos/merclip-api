import os
import logging
from fastapi import Request

logger = logging.getLogger(__name__)

def get_base_url(request_info: Request) -> str:
    """
    Get the base URL with the appropriate scheme (http or https).
    Uses HTTPS when running on Fly.io.
    
    Args:
        request_info: The FastAPI request object
        
    Returns:
        The base URL with the appropriate scheme
    """
    base_url = str(request_info.base_url)
    
    # Check if running on Fly.io by looking for the FLY_APP_NAME environment variable
    if os.getenv("FLY_APP_NAME"):
        # Force HTTPS for Fly.io deployments
        if base_url.startswith("http:"):
            base_url = "https:" + base_url[5:]
            logger.info(f"Running on Fly.io, forcing HTTPS. Base URL: {base_url}")
    
    logger.debug(f"Generated base_url: {base_url}")
    return base_url 