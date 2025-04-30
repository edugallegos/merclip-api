import os
import uuid
import yt_dlp
import tempfile
import logging
import shutil
from datetime import datetime
from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.context import VideoContext

class DownloadVideoStep(BaseStep):
    """Step to download a video from the identified platform."""
    
    def __init__(self, output_dir: str = "generated_images/videos", enabled: bool = True):
        super().__init__("download_video", enabled)
        self.output_dir = output_dir
        self.twitter_dir = os.path.join(output_dir, "twitter")
        self.tiktok_dir = os.path.join(output_dir, "tiktok")
        self.youtube_dir = os.path.join(output_dir, "youtube")
        os.makedirs(self.twitter_dir, exist_ok=True)
        os.makedirs(self.tiktok_dir, exist_ok=True)
        os.makedirs(self.youtube_dir, exist_ok=True)
    
    def _get_unique_filename(self, video_id: str) -> str:
        """Generate a unique filename for the downloaded video based on video ID."""
        unique_id = uuid.uuid4().hex[:8]
        return f"{video_id}_{unique_id}"
    
    def _find_cookies_file(self):
        """Find the cookies file by checking multiple possible locations."""
        # List of possible cookie file locations
        cookie_paths = [
            os.path.join("app", "utils", "cookies.txt"),
            os.path.join("/app", "app", "utils", "cookies.txt"),
            os.path.join(os.getcwd(), "app", "utils", "cookies.txt"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "utils", "cookies.txt"),
            "cookies.txt"
        ]
        
        for path in cookie_paths:
            self.logger.info(f"Checking for cookies at: {path}")
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                self.logger.info(f"Found cookies file at: {path} (size: {file_size} bytes)")
                
                # Quick check for minimum file size to be valid
                if file_size < 100:
                    self.logger.warning(f"Cookie file is suspiciously small ({file_size} bytes)")
                
                return path
        
        self.logger.warning("No cookies file found in any of the standard locations")
        return None
    
    def _list_formats(self, url: str, cookies_path: str = None) -> None:
        """List available formats for debugging purposes."""
        try:
            self.logger.info(f"Listing formats for URL: {url}")
            
            # Base options
            ydl_opts = {
                'listformats': True,
                'quiet': False,
                'no_warnings': False,
                'logger': self.logger,
            }
            
            # Add cookies if available
            if cookies_path and os.path.exists(cookies_path):
                self.logger.info(f"Using cookies file for format listing: {cookies_path}")
                ydl_opts['cookiefile'] = cookies_path
            
            # Configure a temporary YoutubeDL instance just for format listing
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info without downloading - just to see formats
                ydl.extract_info(url, download=False)
        except Exception as e:
            self.logger.error(f"Error listing formats: {str(e)}")
    
    def process(self, context: VideoContext) -> VideoContext:
        """Process the video context to download the video."""
        # Skip if platform or video_id is missing
        if not context.platform or not context.video_id:
            self.logger.error("Missing platform or video_id, cannot download video")
            context.add_error("Missing platform or video_id")
            return context
        
        # Set the appropriate output directory
        if context.platform == "twitter":
            output_dir = self.twitter_dir
        elif context.platform == "tiktok":
            output_dir = self.tiktok_dir
        elif context.platform == "youtube":
            output_dir = self.youtube_dir
        else:
            error_msg = f"Unsupported platform: {context.platform}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
            return context
        
        # Create a unique filename for this download
        filename = self._get_unique_filename(context.video_id)
        output_path = os.path.join(output_dir, filename)
        
        # Configure base yt-dlp options
        ydl_opts = {
            'outtmpl': f"{output_path}.%(ext)s",
            'quiet': False,  # Show output for debugging
            'no_warnings': False,
            'ignoreerrors': False,  # Don't ignore errors to see full error messages
            'no_color': True,
            'verbose': True,
            'logger': self.logger,
        }
        
        # For YouTube videos, handle authentication
        if context.platform == "youtube":
            cookies_path = self._find_cookies_file()
            
            if cookies_path:
                # Make a local copy of the cookies file in a temp dir to ensure file permissions
                temp_dir = tempfile.mkdtemp(prefix="yt_cookies_")
                temp_cookies = os.path.join(temp_dir, "cookies.txt")
                
                try:
                    # Copy the cookies file to our temp location with correct permissions
                    shutil.copy2(cookies_path, temp_cookies)
                    os.chmod(temp_cookies, 0o644)  # Ensure readable permissions
                    
                    self.logger.info(f"Using temporary cookies file at: {temp_cookies}")
                    ydl_opts['cookiefile'] = temp_cookies
                except Exception as e:
                    self.logger.error(f"Error copying cookies file: {str(e)}")
            else:
                self.logger.warning("No cookies file found, YouTube downloads may fail")
            
            # Check if this is a YouTube Shorts URL
            is_shorts = "/shorts/" in context.url
            if is_shorts:
                self.logger.info("Detected YouTube Shorts URL, using special handling")
                
                # For YouTube Shorts, use simpler format selection
                ydl_opts.update({
                    'format': 'best',  # Use best pre-merged format
                })
            else:
                # For regular YouTube videos
                ydl_opts.update({
                    'format': 'bestvideo+bestaudio/best',
                })
            
            # Add YouTube-specific options that help with handling restrictions
            ydl_opts.update({
                'geo_bypass': True,  # Try to bypass geo-restrictions
                'geo_bypass_country': 'US',
                'extractor_retries': 3,  # Retry extractor on failure
                'fragment_retries': 10,  # Retry fragments on failure
                'skip_unavailable_fragments': False,  # Don't skip unavailable fragments
                'youtube_include_dash_manifest': False,  # Skip DASH manifests to avoid issues
            })
            
            # Only list formats if it's a YouTube Shorts (to debug format issues)
            if is_shorts and cookies_path:
                self._list_formats(context.url, temp_cookies)
        elif context.platform == "tiktok":
            # Handle TikTok cookies
            cookies_path = os.path.join("app", "utils", "cookies_tiktok.txt")
            
            if os.path.exists(cookies_path):
                # Make a local copy of the cookies file in a temp dir to ensure file permissions
                temp_dir = tempfile.mkdtemp(prefix="tiktok_cookies_")
                temp_cookies = os.path.join(temp_dir, "cookies_tiktok.txt")
                
                try:
                    # Copy the cookies file to our temp location with correct permissions
                    shutil.copy2(cookies_path, temp_cookies)
                    os.chmod(temp_cookies, 0o644)  # Ensure readable permissions
                    
                    self.logger.info(f"Using temporary TikTok cookies file at: {temp_cookies}")
                    ydl_opts['cookiefile'] = temp_cookies
                except Exception as e:
                    self.logger.error(f"Error copying TikTok cookies file: {str(e)}")
            else:
                self.logger.warning("No TikTok cookies file found, downloads may fail")
            
            # Add TikTok-specific options
            ydl_opts.update({
                'format': 'best',  # Use best pre-merged format
                'extractor_retries': 3,  # Retry extractor on failure
                'fragment_retries': 10,  # Retry fragments on failure
                'skip_unavailable_fragments': False,  # Don't skip unavailable fragments
            })
        
        # Download the video
        self.logger.info(f"Starting download for {context.platform} video: {context.url}")
        self.logger.info(f"Download options: {ydl_opts}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info and download
                info = ydl.extract_info(context.url, download=True)
                
                if info:
                    # Log the successful extraction
                    self.logger.info(f"Successfully extracted video info: {info.get('title', 'Unknown title')}")
                    
                    # Get the actual filename with extension
                    if 'ext' in info:
                        context.video_path = f"{output_path}.{info['ext']}"
                    else:
                        # Fallback to mp4
                        context.video_path = f"{output_path}.mp4"
                    
                    # Store video info in metadata
                    context.metadata["video_info"] = {
                        "title": info.get('title', ''),
                        "duration": info.get('duration', 0),
                        "format": info.get('format', ''),
                        "format_id": info.get('format_id', ''),
                        "resolution": f"{info.get('width', 0)}x{info.get('height', 0)}"
                    }
                    
                    # Verify the file actually exists
                    if os.path.exists(context.video_path):
                        file_size = os.path.getsize(context.video_path)
                        self.logger.info(f"Successfully downloaded {context.platform} video to: {context.video_path}")
                        self.logger.info(f"File size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
                    else:
                        # Try with a different extension - mp4 is most likely
                        alt_path = f"{output_path}.mp4"
                        if os.path.exists(alt_path):
                            context.video_path = alt_path
                            file_size = os.path.getsize(alt_path)
                            self.logger.info(f"Found video with mp4 extension: {context.video_path}")
                            self.logger.info(f"File size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
                        else:
                            # List all files in the output directory for debugging
                            all_files = os.listdir(output_dir)
                            self.logger.info(f"Files in output directory: {all_files}")
                            
                            # Look for any file with the same base name
                            possible_files = [f for f in all_files if filename in f]
                            if possible_files:
                                # Found a match with a different extension
                                context.video_path = os.path.join(output_dir, possible_files[0])
                                file_size = os.path.getsize(context.video_path)
                                self.logger.info(f"Found video with different extension: {context.video_path}")
                                self.logger.info(f"File size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
                            else:
                                error_msg = f"Downloaded file not found at expected path: {context.video_path}"
                                self.logger.error(error_msg)
                                context.add_error(error_msg)
                else:
                    error_msg = f"No video information found for {context.platform} video: {context.url}"
                    self.logger.error(error_msg)
                    context.add_error(error_msg)
        except Exception as e:
            error_msg = f"Error in step {self.name}: {str(e)}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
        finally:
            # Clean up any temporary directories we created
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary directory: {str(e)}")
        
        return context 