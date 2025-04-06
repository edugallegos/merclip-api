import os
import json
import shlex
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

from ..models.video import VideoRequest, ElementType, JobStatus

# Configure logger
logger = logging.getLogger(__name__)

class FFmpegService:
    """Service for handling FFmpeg video rendering operations."""
    
    # Constants
    JOB_DIR = "jobs"
    LOGS_DIR = "logs"
    DEFAULT_OUTPUT_FILENAME = "output.mp4"
    DEFAULT_FONT = "Arial"
    DEFAULT_VOLUME = 1.0
    DEFAULT_SCALE = 1.0
    DEFAULT_POSITION = 0
    
    # File paths
    COMMAND_LOG = "command.log"
    STDOUT_LOG = "stdout.log"
    STDERR_LOG = "stderr.log"
    STATUS_JSON = "status.json"
    INPUT_JSON = "input.json"
    
    # Environment configuration
    FFMPEG_THREADS = os.environ.get("FFMPEG_THREADS", "0")  # 0 means auto-detect
    FFMPEG_PRESET = os.environ.get("FFMPEG_PRESET", "medium")  # Encoding preset (ultrafast to veryslow)
    FFMPEG_MAX_MEMORY = os.environ.get("FFMPEG_MAX_MEMORY", "")  # Memory limit
    
    @staticmethod
    def setup_logging(log_level=logging.INFO):
        """Set up logging configuration for the FFmpeg service.
        
        Args:
            log_level: The logging level (default: INFO)
            
        Returns:
            str: Path to the log file
        """
        logs_dir = os.path.join(os.getcwd(), FFmpegService.LOGS_DIR)
        os.makedirs(logs_dir, exist_ok=True)
        
        log_file = os.path.join(logs_dir, "ffmpeg_service.log")
        
        # Create a file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        
        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Get logger for this module and add handlers
        ffmpeg_logger = logging.getLogger(__name__)
        ffmpeg_logger.setLevel(log_level)
        
        # Remove existing handlers to avoid duplicates on reloads
        if ffmpeg_logger.handlers:
            ffmpeg_logger.handlers.clear()
            
        ffmpeg_logger.addHandler(file_handler)
        ffmpeg_logger.addHandler(console_handler)
        
        # Prevent propagation to the root logger to avoid duplicate logs
        ffmpeg_logger.propagate = False
        
        ffmpeg_logger.info(f"FFmpeg Service logging initialized. Log file: {log_file}")
        ffmpeg_logger.info(f"FFmpeg configuration: threads={FFmpegService.FFMPEG_THREADS}, preset={FFmpegService.FFMPEG_PRESET}, memory_limit={FFmpegService.FFMPEG_MAX_MEMORY or 'unlimited'}")
        return log_file

    @staticmethod
    def rgba_to_hex(rgba: str) -> str:
        """Convert rgba color to hex format."""
        rgba = rgba.strip('rgba()')
        r, g, b, a = map(float, rgba.split(','))
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    @classmethod
    def get_job_dir(cls, job_id: str) -> str:
        """Get the job directory path."""
        return os.path.join(os.getcwd(), cls.JOB_DIR, job_id)

    @classmethod
    def get_status_path(cls, job_id: str) -> str:
        """Get the status file path for a job."""
        return os.path.join(cls.get_job_dir(job_id), cls.STATUS_JSON)

    @classmethod
    def get_output_path(cls, job_id: str) -> str:
        """Get the output file path for a job."""
        return os.path.join(cls.get_job_dir(job_id), cls.DEFAULT_OUTPUT_FILENAME)

    @classmethod
    async def render_video(cls, job_id: str, command: List[str]) -> None:
        """Execute FFmpeg command to render video in a background task."""
        try:
            await cls._execute_ffmpeg_command(job_id, command)
            await cls._verify_output_and_update_status(job_id)
        except Exception as e:
            error_msg = str(e)
            cls.update_job_status(job_id, JobStatus.FAILED, error_msg)
            logger.error(f"Exception while rendering video for job {job_id}: {error_msg}")

    @classmethod
    async def _execute_ffmpeg_command(cls, job_id: str, command: List[str]) -> Tuple[str, str]:
        """Execute FFmpeg command and log results."""
        command_str = " ".join(command)
        logger.info(f"Executing FFmpeg command for job {job_id}")
        
        # Log command to file
        debug_log_path = os.path.join(cls.get_job_dir(job_id), cls.COMMAND_LOG)
        with open(debug_log_path, "w") as f:
            f.write(command_str)
        
        # Execute FFmpeg command
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
        stdout_path = os.path.join(cls.get_job_dir(job_id), cls.STDOUT_LOG)
        stderr_path = os.path.join(cls.get_job_dir(job_id), cls.STDERR_LOG)
        
        with open(stdout_path, "w") as f:
            f.write(stdout_text)
        
        with open(stderr_path, "w") as f:
            f.write(stderr_text)
            
        if process.returncode != 0:
            cls.update_job_status(job_id, JobStatus.FAILED, stderr_text)
            logger.error(f"Error rendering video for job {job_id}: {stderr_text}")
            raise RuntimeError(f"FFmpeg command failed with return code {process.returncode}")
            
        return stdout_text, stderr_text

    @classmethod
    async def _verify_output_and_update_status(cls, job_id: str) -> None:
        """Verify the output file exists and update job status."""
        output_path = cls.get_output_path(job_id)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            cls.update_job_status(job_id, JobStatus.COMPLETED)
            logger.info(f"Successfully rendered video for job {job_id}")
        else:
            error_msg = "FFmpeg executed successfully but output file is empty or missing"
            cls.update_job_status(job_id, JobStatus.FAILED, error_msg)
            logger.error(f"Error with output file for job {job_id}: {error_msg}")

    @classmethod
    def generate_command(cls, request: VideoRequest, output_path: str) -> List[str]:
        """Generate FFmpeg command for the video request."""
        cmd = ["ffmpeg", "-y"]  # Base command with overwrite flag
        
        # Add thread limit if specified
        if cls.FFMPEG_THREADS and cls.FFMPEG_THREADS != "0":
            cmd.extend(["-threads", cls.FFMPEG_THREADS])
            
        # Add memory limit if specified
        if cls.FFMPEG_MAX_MEMORY:
            cmd.extend(["-max_memory", cls.FFMPEG_MAX_MEMORY])
        
        # Add background
        cmd.extend(cls._get_background_input(request))
        
        # Process all media elements and collect their configurations
        input_index = 1  # Background is input 0
        video_elements = []
        image_elements = []
        audio_elements = []
        
        # Add media inputs to command and categorize elements
        input_index = cls._collect_media_elements(
            request, cmd, input_index, video_elements, image_elements, audio_elements
        )
        
        # Build filter complex for combining all elements
        filter_complex, last_video = cls._build_filter_complex(
            request, video_elements, image_elements, audio_elements
        )
        
        # Add filter complex to command if needed
        if filter_complex:
            cmd.extend(["-filter_complex", filter_complex])
            cmd.extend(["-map", f"[{last_video}]"])
            
            # Map audio streams if present
            if audio_elements:
                cmd.extend(["-map", "[aout]"])
            elif any(e.type == ElementType.VIDEO and e.audio for e in request.elements):
                cmd.extend(["-map", "1:a?"])
        else:
            # Use simpler vf approach for text-only overlays
            vf_filters = cls._build_simple_text_filters(request)
            if vf_filters:
                cmd.extend(["-vf", ",".join(vf_filters)])
        
        # Add output parameters
        cmd.extend(cls._get_output_parameters(request, audio_elements))
        
        # Add output file
        cmd.append(output_path)
        
        return cmd

    @classmethod
    def _get_background_input(cls, request: VideoRequest) -> List[str]:
        """Generate background input parameters."""
        return [
            "-f", "lavfi",
            "-i", f"color=c={request.output.background_color}:s={request.output.resolution.width}x{request.output.resolution.height}:r={request.output.frame_rate}:d={request.output.duration}"
        ]

    @classmethod
    def _collect_media_elements(
        cls, 
        request: VideoRequest, 
        cmd: List[str], 
        input_index: int,
        video_elements: List[Dict[str, Any]],
        image_elements: List[Dict[str, Any]],
        audio_elements: List[Dict[str, Any]]
    ) -> int:
        """Process input elements and add them to the command."""
        for element in request.elements:
            if element.type == ElementType.VIDEO:
                cmd.extend(["-i", element.source])
                video_elements.append({"index": input_index, "element": element})
                input_index += 1
            elif element.type == ElementType.IMAGE:
                cmd.extend(["-i", element.source])
                image_elements.append({"index": input_index, "element": element})
                input_index += 1
            elif element.type == ElementType.AUDIO:
                cmd.extend(["-i", element.source])
                audio_elements.append({"index": input_index, "element": element})
                input_index += 1
        
        return input_index

    @classmethod
    def _build_filter_complex(
        cls, 
        request: VideoRequest,
        video_elements: List[Dict[str, Any]],
        image_elements: List[Dict[str, Any]],
        audio_elements: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """Build the FFmpeg filter complex for combining all elements."""
        filter_parts = []
        audio_filters = []
        last_video = "0:v"
        overlay_count = 0
        
        # Process video elements
        last_video, overlay_count = cls._process_video_elements(
            video_elements, filter_parts, last_video, overlay_count
        )
        
        # Process image elements
        last_video, overlay_count = cls._process_image_elements(
            image_elements, filter_parts, last_video, overlay_count
        )
        
        # Process text elements
        last_video = cls._process_text_elements(
            request.elements, filter_parts, last_video
        )
        
        # Process audio elements
        if audio_elements:
            audio_filters = cls._process_audio_elements(
                audio_elements, request.output.duration
            )
        
        # Combine all filters
        filter_complex = ""
        if filter_parts or audio_filters:
            filter_complex = "".join(filter_parts + audio_filters).rstrip(";")
        
        return filter_complex, last_video

    @classmethod
    def _process_video_elements(
        cls,
        video_elements: List[Dict[str, Any]],
        filter_parts: List[str],
        last_video: str,
        overlay_count: int
    ) -> Tuple[str, int]:
        """Process video elements and add them to the filter complex."""
        for video_item in video_elements:
            idx = video_item["index"]
            element = video_item["element"]
            
            # Extract parameters
            start_time = element.timeline.start
            duration = element.timeline.duration
            in_point = element.timeline.in_ if hasattr(element.timeline, 'in_') and element.timeline.in_ is not None else 0
            scale = element.transform.scale if hasattr(element.transform, 'scale') and element.transform.scale else cls.DEFAULT_SCALE
            
            # Get position values, defaulting to 0 if not integers
            x_pos = element.transform.position.x if hasattr(element.transform, 'position') and isinstance(element.transform.position.x, int) else cls.DEFAULT_POSITION
            y_pos = element.transform.position.y if hasattr(element.transform, 'position') and isinstance(element.transform.position.y, int) else cls.DEFAULT_POSITION
            
            # Trim and scale the video
            filter_parts.append(
                f"[{idx}:v]trim={in_point}:{in_point+duration},setpts=PTS-STARTPTS,scale=iw*{scale}:ih*{scale}[v{idx}];"
            )
            
            # Add overlay with timing
            filter_parts.append(
                f"[{last_video}][v{idx}]overlay=x={x_pos}:y={y_pos}:enable='between(t,{start_time},{start_time+duration})'[ov{overlay_count}];"
            )
            
            last_video = f"ov{overlay_count}"
            overlay_count += 1
            
        return last_video, overlay_count

    @classmethod
    def _process_image_elements(
        cls,
        image_elements: List[Dict[str, Any]],
        filter_parts: List[str],
        last_video: str,
        overlay_count: int
    ) -> Tuple[str, int]:
        """Process image elements and add them to the filter complex."""
        for image_item in image_elements:
            idx = image_item["index"]
            element = image_item["element"]
            
            # Extract parameters
            start_time = element.timeline.start
            duration = element.timeline.duration
            
            # Default values if not provided
            scale = cls.DEFAULT_SCALE
            x_pos = cls.DEFAULT_POSITION
            y_pos = cls.DEFAULT_POSITION
            
            if hasattr(element, 'transform') and element.transform:
                if hasattr(element.transform, 'scale') and element.transform.scale:
                    scale = element.transform.scale
                    
                if hasattr(element.transform, 'position'):
                    if hasattr(element.transform.position, 'x') and isinstance(element.transform.position.x, int):
                        x_pos = element.transform.position.x
                    if hasattr(element.transform.position, 'y') and isinstance(element.transform.position.y, int):
                        y_pos = element.transform.position.y
            
            # Scale the image
            filter_parts.append(
                f"[{idx}:v]scale=iw*{scale}:ih*{scale}[img{idx}];"
            )
            
            # Add overlay with timing
            filter_parts.append(
                f"[{last_video}][img{idx}]overlay=x={x_pos}:y={y_pos}:enable='between(t,{start_time},{start_time+duration})'[img_ov{overlay_count}];"
            )
            
            last_video = f"img_ov{overlay_count}"
            overlay_count += 1
            
        return last_video, overlay_count

    @classmethod
    def _get_text_position(cls, position_value: Union[str, int]) -> str:
        """Convert position preset to FFmpeg position value."""
        # Simple positions
        if position_value == "center":
            return "(w-text_w)/2"
        elif position_value == "left":
            return "10"
        elif position_value == "right":
            return "w-text_w-10"
        elif position_value == "top":
            return "10"
        elif position_value == "bottom":
            return "h-text_h-10"
        elif position_value == "mid-top":
            return "h/4-text_h/2"
        elif position_value == "mid-bottom":
            return "3*h/4-text_h/2"
        # Combined positions
        elif position_value == "top-left":
            return "10"  # This is for x or y coordinate
        elif position_value == "top-right":
            return "w-text_w-10" if isinstance(position_value, str) and "x" in position_value else "10"
        elif position_value == "bottom-left":
            return "10" if isinstance(position_value, str) and "x" in position_value else "h-text_h-10"
        elif position_value == "bottom-right":
            return "w-text_w-10" if isinstance(position_value, str) and "x" in position_value else "h-text_h-10"
        # For numeric values
        elif isinstance(position_value, int):
            return str(position_value)
        # Default
        return str(cls.DEFAULT_POSITION)

    @classmethod
    def _process_text_elements(
        cls,
        elements: List[Any],
        filter_parts: List[str],
        last_video: str
    ) -> str:
        """Process text elements and add them to the filter complex."""
        for i, element in enumerate(elements):
            if element.type == ElementType.TEXT:
                # Get text positioning
                x_pos = cls._get_text_position(element.transform.position.x)
                y_pos = cls._get_text_position(element.transform.position.y)
                
                # Handle special combined position presets
                if element.transform.position.x in ["top-left", "top-right", "bottom-left", "bottom-right", "mid-top", "mid-bottom"] or \
                   element.transform.position.y in ["top-left", "top-right", "bottom-left", "bottom-right", "mid-top", "mid-bottom"]:
                    if element.transform.position.x == "top-left" or element.transform.position.y == "top-left":
                        x_pos = "10"
                        y_pos = "10"
                    elif element.transform.position.x == "top-right" or element.transform.position.y == "top-right":
                        x_pos = "w-text_w-10"
                        y_pos = "10"
                    elif element.transform.position.x == "bottom-left" or element.transform.position.y == "bottom-left":
                        x_pos = "10"
                        y_pos = "h-text_h-10"
                    elif element.transform.position.x == "bottom-right" or element.transform.position.y == "bottom-right":
                        x_pos = "w-text_w-10"
                        y_pos = "h-text_h-10"
                    elif element.transform.position.x == "mid-top" or element.transform.position.y == "mid-top":
                        x_pos = "(w-text_w)/2"
                        y_pos = "h/4-text_h/2"
                    elif element.transform.position.x == "mid-bottom" or element.transform.position.y == "mid-bottom":
                        x_pos = "(w-text_w)/2"
                        y_pos = "3*h/4-text_h/2"
                
                # Handle background color
                box_param = ""
                if element.style.background_color:
                    box_color = cls.rgba_to_hex(element.style.background_color) if element.style.background_color.startswith('rgba') else element.style.background_color
                    box_param = f":box=1:boxcolor={box_color}:boxborderw=5"
                
                # Get timing
                start_time = element.timeline.start
                duration = element.timeline.duration
                
                # Get font style
                font_family = element.style.font_family if element.style.font_family else cls.DEFAULT_FONT
                font_params = f":fontfile='{font_family}'" if os.path.exists(font_family) else ""
                
                # Add text shadow for better readability
                shadow_params = ":shadowcolor=black:shadowx=2:shadowy=2"
                
                # Add text overlay with timing and enhanced styling
                filter_parts.append(
                    f"[{last_video}]drawtext=text='{element.text}':fontsize={element.style.font_size}:fontcolor={element.style.color}{font_params}{box_param}{shadow_params}:x={x_pos}:y={y_pos}:enable='between(t,{start_time},{start_time+duration})'[txt{i}];"
                )
                
                last_video = f"txt{i}"
                
        return last_video

    @classmethod
    def _process_audio_elements(
        cls,
        audio_elements: List[Dict[str, Any]],
        output_duration: float
    ) -> List[str]:
        """Process audio elements and create audio filters."""
        audio_filters = []
        
        # Process each audio element individually
        for audio_item in audio_elements:
            idx = audio_item["index"]
            element = audio_item["element"]
            
            # Extract parameters
            start_time = element.timeline.start
            duration = element.timeline.duration
            
            # Get audio properties with defaults
            volume = cls.DEFAULT_VOLUME
            fade_in = 0
            fade_out = 0
            
            if hasattr(element, 'volume') and element.volume is not None:
                volume = float(element.volume)
            
            if hasattr(element, 'fade_in') and element.fade_in is not None:
                fade_in = float(element.fade_in)
            
            if hasattr(element, 'fade_out') and element.fade_out is not None:
                fade_out = float(element.fade_out)
            
            # Build audio filter string
            audio_filter = f"[{idx}:a]"
            audio_filter += f"atrim=0:{duration},asetpts=PTS-STARTPTS,"
            audio_filter += f"volume={volume:.1f},"
            
            # Add fade in/out if needed
            if fade_in > 0:
                audio_filter += f"afade=t=in:st=0:d={fade_in},"
            if fade_out > 0:
                audio_filter += f"afade=t=out:st={duration-fade_out}:d={fade_out},"
            
            # Delay audio to match start time
            if start_time > 0:
                audio_filter += f"adelay={int(start_time*1000)}|{int(start_time*1000)},"
            
            # Pad to full duration and set presentation timestamp
            audio_filter += f"apad=whole_dur={output_duration},"
            audio_filter += f"asetpts=PTS-STARTPTS[a{idx}];"
            
            audio_filters.append(audio_filter)
        
        # Merge all audio streams if needed
        if len(audio_elements) > 1:
            audio_inputs = "".join([f"[a{item['index']}]" for item in audio_elements])
            audio_filters.append(
                f"{audio_inputs}amix=inputs={len(audio_elements)}:normalize=0[aout];"
            )
        else:
            # Single audio - just rename
            audio_filters.append(
                f"[a{audio_elements[0]['index']}]acopy[aout];"
            )
            
        return audio_filters

    @classmethod
    def _build_simple_text_filters(cls, request: VideoRequest) -> List[str]:
        """Build simple text filters for text-only overlays."""
        vf_filters = []
        
        for element in request.elements:
            if element.type == ElementType.TEXT:
                x_pos = element.transform.position.x
                if x_pos == "center":
                    x_pos = "(w-text_w)/2"
                
                box_param = ""
                if element.style.background_color:
                    box_color = cls.rgba_to_hex(element.style.background_color) if element.style.background_color.startswith('rgba') else element.style.background_color
                    box_param = f":box=1:boxcolor={box_color}"
                
                vf_filters.append(
                    f"drawtext=text='{element.text}':fontsize={element.style.font_size}:fontcolor={element.style.color}{box_param}:x={x_pos}:y={element.transform.position.y}"
                )
        
        return vf_filters

    @classmethod
    def _get_output_parameters(cls, request: VideoRequest, audio_elements: List[Dict[str, Any]]) -> List[str]:
        """Get output encoding parameters."""
        params = [
            "-t", str(request.output.duration),
            "-c:v", "libx264",
            "-preset", cls.FFMPEG_PRESET,
            "-pix_fmt", "yuv420p"
        ]
        
        # Add audio codec if needed
        if audio_elements or any(e.type == ElementType.VIDEO and e.audio for e in request.elements):
            params.extend(["-c:a", "aac", "-b:a", "128k"])
            
        return params

    @classmethod
    def save_job(cls, request: VideoRequest, job_id: str) -> str:
        """Save the job input to a file and initialize status."""
        # Create jobs directory
        jobs_dir = cls.get_job_dir(job_id)
        os.makedirs(jobs_dir, exist_ok=True)
        
        # Save input.json
        input_path = os.path.join(jobs_dir, cls.INPUT_JSON)
        with open(input_path, "w") as f:
            json.dump(request.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Initialize status.json
        status_path = cls.get_status_path(job_id)
        status = {
            "job_id": job_id,
            "status": JobStatus.PROCESSING,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "error": None,
            "output_url": None
        }
        
        with open(status_path, "w") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Job {job_id} created and saved")
        return input_path

    @classmethod
    def get_job_status(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a job."""
        status_path = cls.get_status_path(job_id)
        if not os.path.exists(status_path):
            logger.warning(f"Status file not found for job {job_id}")
            return None
        
        try:
            with open(status_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading status for job {job_id}: {str(e)}")
            return None

    @classmethod
    def update_job_status(cls, job_id: str, status: JobStatus, error: Optional[str] = None) -> None:
        """Update the status of a job."""
        status_path = cls.get_status_path(job_id)
        if not os.path.exists(status_path):
            logger.warning(f"Status file not found for job {job_id}")
            return
        
        try:
            with open(status_path, "r") as f:
                job_status = json.load(f)
            
            # Update status and related fields
            job_status["status"] = status
            
            if error:
                job_status["error"] = error
                
            if status == JobStatus.COMPLETED:
                job_status["completed_at"] = datetime.utcnow().isoformat()
                job_status["output_url"] = f"/jobs/{job_id}/{cls.DEFAULT_OUTPUT_FILENAME}"
            
            with open(status_path, "w") as f:
                json.dump(job_status, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Updated job {job_id} status to {status}")
        
        except Exception as e:
            logger.error(f"Error updating status for job {job_id}: {str(e)}") 