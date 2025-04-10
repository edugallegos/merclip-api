import os
import base64
import logging
import io
from PIL import Image, ImageDraw
from io import BytesIO
from google import genai
from google.genai import types
from typing import List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def create_blank_canvas(width=540, height=960):
    """Create a blank white canvas with specified dimensions"""
    img = Image.new('RGB', (width, height), color='white')
    
    # Draw a very light gray border to ensure it's not completely blank
    # Sometimes APIs have trouble with completely blank images
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (width-1, height-1)], outline=(240, 240, 240))
    
    logger.debug(f"Created blank canvas with dimensions {width}x{height}")
    return img

def create_simple_doodle(width=540, height=960):
    """Create a simple doodle for testing - a circle in the middle"""
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw a circle in the middle
    center_x, center_y = width // 2, height // 2
    radius = min(width, height) // 10
    draw.ellipse((center_x - radius, center_y - radius, 
                  center_x + radius, center_y + radius), 
                 outline=(0, 0, 0))
    
    logger.debug(f"Created simple doodle canvas with dimensions {width}x{height}")
    return img

def get_api_key():
    """Get the API key from environment variables"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return api_key

def get_output_directory():
    """Create and return an output directory structure with parent/child folders
    
    Returns a path with structure: 
    /generated_images/YYYY-MM-DD/
    """
    # Create parent directory
    parent_dir = os.path.join(os.getcwd(), "generated_images")
    os.makedirs(parent_dir, exist_ok=True)
    
    # Create date subdirectory with format YYYY-MM-DD
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(parent_dir, date_str)
    
    # Ensure the directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

def get_next_sequence_number(directory):
    """Get the next sequence number for file naming"""
    # List all png files in the directory
    files = [f for f in os.listdir(directory) if f.endswith('.png') and f.startswith('image_')]
    
    # If no files exist, start with 1
    if not files:
        return 1
    
    # Extract sequence numbers from filenames
    sequence_numbers = []
    for filename in files:
        try:
            # Extract number from format "image_001.png"
            num = int(filename.replace('image_', '').replace('.png', ''))
            sequence_numbers.append(num)
        except ValueError:
            continue
    
    # Return next number in sequence
    return max(sequence_numbers) + 1 if sequence_numbers else 1

def encode_image_to_base64(image):
    """Encode a PIL Image to base64 string"""
    buffered = BytesIO()
    # Save as PNG with maximum quality
    image.save(buffered, format="PNG", quality=100)
    img_bytes = buffered.getvalue()
    img_str = base64.b64encode(img_bytes).decode('utf-8')
    
    # Log image details for debugging
    logger.debug(f"Encoded image: format={image.format}, mode={image.mode}, size={image.size}")
    logger.debug(f"Base64 length: {len(img_str)} chars, first 50 chars: {img_str[:50]}")
    
    # Save the input image to debug
    debug_dir = "debug_images"
    os.makedirs(debug_dir, exist_ok=True)
    debug_path = os.path.join(debug_dir, f"input_canvas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    image.save(debug_path)
    logger.debug(f"Saved input canvas for debugging to {debug_path}")
    
    return img_str

def generate_image(prompt: str, input_image=None, custom_output_dir: str = None, use_doodle=False):
    """Generate an image using Gemini API and save it to the output directory
    
    Args:
        prompt: Text prompt for image generation
        input_image: Optional input image (PIL.Image) - blank canvas with specified aspect ratio
        custom_output_dir: Optional custom output directory
        use_doodle: Whether to use a simple doodle instead of blank canvas
        
    Returns:
        Tuple of (success: bool, image_path: str or None, error: str or None)
    """
    try:
        # Get output directory (date-based in project root by default)
        output_dir = custom_output_dir if custom_output_dir else get_output_directory()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get API key from environment
        api_key = get_api_key()
        
        # Initialize client
        client = genai.Client(api_key=api_key)
        
        logger.info(f"Generating image for prompt: {prompt}")
        
        # Create appropriate input image
        if input_image is None:
            if use_doodle:
                input_image = create_simple_doodle()
            else:
                input_image = create_blank_canvas()
        
        # Save the input image for debugging
        debug_dir = "debug_images"
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f"input_canvas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        input_image.save(debug_path)
        logger.debug(f"Saved input canvas for debugging to {debug_path}")
        
        logger.debug(f"Creating content with image and text using proper Part formatting")
        
        # Convert PIL image to bytes
        buffer = BytesIO()
        input_image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        
        # Use the proper Part format from the documentation
        try:
            # Create proper content with parts
            prompt_text = f"{prompt}. Keep the same minimal line doodle style."
            
            # For older versions of the library
            try:
                # First try using Content and Part objects
                content = types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="image/png",
                                data=image_bytes
                            )
                        ),
                        types.Part(text=prompt_text)
                    ]
                )
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp-image-generation",
                    contents=content,
                    config=types.GenerateContentConfig(
                        response_modalities=['Text', 'Image']
                    )
                )
            except Exception as format_error:
                logger.warning(f"First format attempt failed: {str(format_error)}")
                logger.info("Trying alternative format")
                
                # Try alternative format
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp-image-generation",
                    contents=[
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(image_bytes).decode('utf-8')
                            }
                        },
                        {
                            "text": prompt_text
                        }
                    ],
                    config=types.GenerateContentConfig(
                        response_modalities=['Text', 'Image']
                    )
                )
                
        except Exception as api_error:
            # If we used a blank canvas and that failed, try with a simple doodle
            if not use_doodle:
                logger.warning(f"Blank canvas approach failed: {str(api_error)}")
                logger.info("Trying again with a simple doodle instead of blank canvas")
                return generate_image(prompt, None, custom_output_dir, use_doodle=True)
            else:
                # Both approaches failed
                raise api_error
    
        logger.info(f"Response received from API")
        
        # Check if response has candidates
        if not response.candidates or len(response.candidates) == 0:
            logger.error("No candidates in response")
            return False, None, "No candidates in response"
        
        # Check if response has parts
        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
            logger.error("No content parts in response")
            return False, None, "No content parts in response"
        
        # Find parts that have inline_data (the image)
        image_parts = []
        for part in candidate.content.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                image_parts.append(part)
        
        if not image_parts:
            logger.error("No image parts found in response")
            return False, None, "No image parts found in response"
        
        # Get the first image part
        image_part = image_parts[0]
        
        # Get next sequence number for filename
        seq_num = get_next_sequence_number(output_dir)
        
        # Generate sequential filename (e.g., image_001.png)
        filename = f"image_{seq_num:03d}.png"
        filepath = os.path.join(output_dir, filename)
        
        logger.info(f"Saving image to {filepath}")
        
        try:
            # Using the official approach from Google's example:
            # for part in response.candidates[0].content.parts:
            #   if part.text is not None:
            #     print(part.text)
            #   elif part.inline_data is not None:
            #     image = Image.open(BytesIO((part.inline_data.data)))
            #     image.save('gemini-native-image.png')

            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(part.text)
                elif part.inline_data is not None:
                    image = Image.open(BytesIO((part.inline_data.data)))
                    image.save(filepath)
                    logger.info(f"Image saved successfully to {filepath}")
                    return True, filepath, None
            
            #if image_part.inline_data is not None:
            #    image = Image.open(BytesIO(image_part.inline_data.data))
            #    image.save(filepath)
            #    logger.info(f"Image saved successfully to {filepath}")
            #    return True, filepath, None
            else:
                logger.error("Image part does not have inline_data")
                return False, None, "Image part does not have inline_data"
            
        except Exception as inner_e:
            logger.error(f"Error saving image: {str(inner_e)}")
            return False, None, f"Error saving image: {str(inner_e)}"
        
    except Exception as e:
        error_message = f"Error generating image: {str(e)}"
        logger.error(error_message)
        import traceback
        logger.error(traceback.format_exc())
        return False, None, error_message

async def generate_multiple_images(prompts: List[str], output_dir: str = None) -> List[dict]:
    """Generate multiple images for a list of prompts
    
    Args:
        prompts: List of text prompts
        output_dir: Optional custom output directory
        
    Returns:
        List of dictionaries with generation results
    """
    results = []
    
    for prompt in prompts:
        # Try to generate the image
        success, image_path, error = generate_image(prompt, None, output_dir)
        
        result = {
            "prompt": prompt,
            "success": success,
        }
        
        if success:
            result["image_path"] = image_path
        else:
            result["error"] = error
            
        results.append(result)
    
    return results 