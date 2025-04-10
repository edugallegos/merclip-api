import os
import base64
import logging
from PIL import Image
from io import BytesIO
from google import genai
from google.genai import types
from typing import List, Dict
from datetime import datetime
import uuid

# Configure logging
logger = logging.getLogger(__name__)

# Target aspect ratio constants
TARGET_WIDTH = 1080  # Common width for 9:16 content
TARGET_HEIGHT = 1920  # Common height for 9:16 content

def load_base_image():
    """Load the base image to use as canvas"""
    base_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'base.png')
    try:
        img = Image.open(base_path)
        logger.debug(f"Loaded base image from {base_path}")
        return img
    except Exception as e:
        logger.error(f"Failed to load base image: {str(e)}")
        raise

def get_api_key():
    """Get the API key from environment variables"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return api_key

def get_output_directory(request_id: str):
    """Create and return an output directory structure using request ID"""
    parent_dir = os.path.join(os.getcwd(), "generated_images")
    os.makedirs(parent_dir, exist_ok=True)
    
    # Create request-specific directory
    output_dir = os.path.join(parent_dir, request_id)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

def get_next_sequence_number(directory):
    """Get the next sequence number for file naming"""
    files = [f for f in os.listdir(directory) if f.endswith('.png') and f.startswith('image_')]
    if not files:
        return 1
    sequence_numbers = []
    for filename in files:
        try:
            num = int(filename.replace('image_', '').replace('.png', ''))
            sequence_numbers.append(num)
        except ValueError:
            continue
    return max(sequence_numbers) + 1 if sequence_numbers else 1

def resize_to_9_16(image: Image.Image) -> Image.Image:
    """Resize image to 9:16 aspect ratio with white background
    
    Args:
        image: Input PIL Image
        
    Returns:
        Resized PIL Image with 9:16 aspect ratio
    """
    # Calculate new dimensions maintaining aspect ratio
    width, height = image.size
    
    # Use full width of target canvas
    new_width = TARGET_WIDTH
    # Calculate height to maintain aspect ratio
    new_height = int((new_width * height) / width)
    
    # Create canvas with calculated height (at least TARGET_HEIGHT)
    canvas_height = max(new_height, TARGET_HEIGHT)
    canvas = Image.new('RGB', (TARGET_WIDTH, canvas_height), 'white')
    
    # Resize image
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Paste the resized image at the top of the canvas
    canvas.paste(resized_image, (0, 0))
    
    return canvas

def generate_image(prompt: str, request_id: str):
    """Generate an image using Gemini API and save it to the request-specific directory
    
    Args:
        prompt: Text prompt for image generation
        request_id: Unique identifier for this request
        
    Returns:
        Tuple of (success: bool, image_path: str or None, error: str or None)
    """
    try:
        output_dir = get_output_directory(request_id)
        
        api_key = get_api_key()
        client = genai.Client(api_key=api_key)
        
        logger.info(f"Generating image for prompt: {prompt}")
        
        # Load the base image
        input_image = load_base_image()
        
        prompt_text = f"{prompt}. Keep the same minimal line doodle style portrait aspect ratio."

        content = [prompt_text, input_image]
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=content,
            config=types.GenerateContentConfig(
                response_modalities=['Text', 'Image']
            )
        )
        
        if not response.candidates or len(response.candidates) == 0:
            logger.error("No candidates in response")
            return False, None, "No candidates in response"
        
        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
            logger.error("No content parts in response")
            return False, None, "No content parts in response"
        
        seq_num = get_next_sequence_number(output_dir)
        filename = f"image_{seq_num:03d}.png"
        filepath = os.path.join(output_dir, filename)
        
        logger.info(f"Saving image to {filepath}")
        
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO((part.inline_data.data)))
                # Resize image to 9:16 aspect ratio
                resized_image = resize_to_9_16(image)
                resized_image.save(filepath)
                logger.info(f"Image saved successfully to {filepath}")
                return True, filepath, None
        
        logger.error("No image data found in response")
        return False, None, "No image data found in response"
        
    except Exception as e:
        error_message = f"Error generating image: {str(e)}"
        logger.error(error_message)
        import traceback
        logger.error(traceback.format_exc())
        return False, None, error_message

async def generate_multiple_images(prompts: List[str]) -> Dict:
    """Generate multiple images for a list of prompts
    
    Returns:
        Dictionary containing request_id and list of generation results
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    results = []
    for prompt in prompts:
        success, image_path, error = generate_image(prompt, request_id)
        result = {
            "prompt": prompt,
            "success": success,
        }
        if success:
            result["image_path"] = image_path
        else:
            result["error"] = error
        results.append(result)
    
    return {
        "request_id": request_id,
        "results": results,
        "output_directory": get_output_directory(request_id)
    } 