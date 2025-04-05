import os
import json
import shlex
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models.video import VideoRequest, ElementType, JobStatus

class FFmpegService:
    @staticmethod
    def rgba_to_hex(rgba: str) -> str:
        """Convert rgba color to hex format."""
        # Extract values from rgba(r,g,b,a)
        rgba = rgba.strip('rgba()')
        r, g, b, a = map(float, rgba.split(','))
        # Convert to hex
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    @staticmethod
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

    @staticmethod
    def generate_command(request: VideoRequest, output_path: str) -> List[str]:
        """Generate a reliable FFmpeg command that supports video overlays and text."""
        # Base command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
        ]
        
        # Add background as the first input
        cmd.extend([
            "-f", "lavfi",
            "-i", f"color=c={request.output.background_color}:s={request.output.resolution.width}x{request.output.resolution.height}:r={request.output.frame_rate}:d={request.output.duration}"
        ])
        
        # Add video, image, and audio inputs
        input_index = 1  # Background is input 0
        video_elements = []
        image_elements = []
        audio_elements = []
        
        for i, element in enumerate(request.elements):
            if element.type == ElementType.VIDEO:
                cmd.extend(["-i", element.source])
                video_elements.append({
                    "index": input_index,
                    "element": element
                })
                input_index += 1
            elif element.type == ElementType.IMAGE:
                cmd.extend(["-i", element.source])
                image_elements.append({
                    "index": input_index,
                    "element": element
                })
                input_index += 1
            elif element.type == ElementType.AUDIO:
                cmd.extend(["-i", element.source])
                audio_elements.append({
                    "index": input_index,
                    "element": element
                })
                input_index += 1
        
        # Build filter complex
        filter_parts = []
        
        # Process video elements first
        last_video = "0:v"
        overlay_count = 0
        
        # Process video elements
        for video_item in video_elements:
            idx = video_item["index"]
            element = video_item["element"]
            
            # Extract parameters
            start_time = element.timeline.start
            duration = element.timeline.duration
            in_point = element.timeline.in_ if element.timeline.in_ is not None else 0
            scale = element.transform.scale if element.transform.scale else 1.0
            x_pos = element.transform.position.x if isinstance(element.transform.position.x, int) else 0
            y_pos = element.transform.position.y if isinstance(element.transform.position.y, int) else 0
            
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
        
        # Process image elements
        for image_item in image_elements:
            idx = image_item["index"]
            element = image_item["element"]
            
            # Extract parameters
            start_time = element.timeline.start
            duration = element.timeline.duration
            
            # Default values if not provided
            scale = element.transform.scale if hasattr(element, 'transform') and element.transform and element.transform.scale else 1.0
            x_pos = element.transform.position.x if hasattr(element, 'transform') and element.transform and element.transform.position and isinstance(element.transform.position.x, int) else 0
            y_pos = element.transform.position.y if hasattr(element, 'transform') and element.transform and element.transform.position and isinstance(element.transform.position.y, int) else 0
            
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
        
        # Process text elements
        for i, element in enumerate(request.elements):
            if element.type == ElementType.TEXT:
                # Get text positioning
                x_pos = element.transform.position.x
                if x_pos == "center":
                    x_pos = "(w-text_w)/2"
                
                # Handle background color
                if element.style.background_color:
                    if element.style.background_color.startswith('rgba'):
                        box_color = FFmpegService.rgba_to_hex(element.style.background_color)
                    else:
                        box_color = element.style.background_color
                    box_param = f":box=1:boxcolor={box_color}"
                else:
                    box_param = ""
                
                # Get timing
                start_time = element.timeline.start
                duration = element.timeline.duration
                
                # Add text overlay with timing
                filter_parts.append(
                    f"[{last_video}]drawtext=text='{element.text}':fontsize={element.style.font_size}:fontcolor={element.style.color}{box_param}:x={x_pos}:y={element.transform.position.y}:enable='between(t,{start_time},{start_time+duration})'[txt{i}];"
                )
                
                last_video = f"txt{i}"
        
        # Process audio elements
        audio_filters = []
        
        if audio_elements:
            # Process each audio element individually
            for audio_item in audio_elements:
                idx = audio_item["index"]
                element = audio_item["element"]
                
                # Extract parameters
                start_time = element.timeline.start
                duration = element.timeline.duration
                volume = getattr(element, 'volume', 1.0)
                fade_in = getattr(element, 'fade_in', 0)
                fade_out = getattr(element, 'fade_out', 0)
                
                # Build audio filter
                audio_filter = f"[{idx}:a]"
                
                # Add volume adjustment if needed
                if volume != 1.0:
                    audio_filter += f"volume={volume},"
                
                # Add fade in/out
                if fade_in > 0:
                    audio_filter += f"afade=t=in:st=0:d={fade_in},"
                if fade_out > 0:
                    audio_filter += f"afade=t=out:st={duration-fade_out}:d={fade_out},"
                
                # Trim to specified duration
                audio_filter += f"atrim=0:{duration},asetpts=PTS-STARTPTS"
                
                # Add silence padding for start time if needed
                if start_time > 0:
                    audio_filter += f",adelay={int(start_time*1000)}|{int(start_time*1000)}"
                
                # Add output label
                audio_filter += f"[a{idx}];"
                
                audio_filters.append(audio_filter)
            
            # Add amix filter if needed
            if len(audio_elements) > 1:
                audio_inputs = "".join([f"[a{item['index']}]" for item in audio_elements])
                audio_filters.append(
                    f"{audio_inputs}amix=inputs={len(audio_elements)}:dropout_transition=0[aout];"
                )
            else:
                # Single audio - just rename
                audio_filters.append(
                    f"[a{audio_elements[0]['index']}]asetpts=PTS-STARTPTS[aout];"
                )
        
        # If we have any filters, add the filter_complex
        if filter_parts or audio_filters:
            # Combine all filters with proper semicolon separation
            filter_complex = "".join(filter_parts + audio_filters).rstrip(";")
            
            cmd.extend(["-filter_complex", filter_complex])
            cmd.extend(["-map", f"[{last_video}]"])
            
            # Map audio streams
            if audio_elements:
                cmd.extend(["-map", "[aout]"])
            elif any(e.type == ElementType.VIDEO and e.audio for e in request.elements):
                cmd.extend(["-map", "1:a?"])
        else:
            # If we only have text overlays, use simpler vf approach
            vf_filters = []
            for element in request.elements:
                if element.type == ElementType.TEXT:
                    x_pos = element.transform.position.x
                    if x_pos == "center":
                        x_pos = "(w-text_w)/2"
                    
                    if element.style.background_color:
                        if element.style.background_color.startswith('rgba'):
                            box_color = FFmpegService.rgba_to_hex(element.style.background_color)
                        else:
                            box_color = element.style.background_color
                        box_param = f":box=1:boxcolor={box_color}"
                    else:
                        box_param = ""
                    
                    vf_filters.append(
                        f"drawtext=text='{element.text}':fontsize={element.style.font_size}:fontcolor={element.style.color}{box_param}:x={x_pos}:y={element.transform.position.y}"
                    )
            
            if vf_filters:
                cmd.extend(["-vf", ",".join(vf_filters)])
        
        # Add output parameters
        cmd.extend([
            "-t", str(request.output.duration),
            "-c:v", "libx264",
            "-preset", "medium",
            "-pix_fmt", "yuv420p"
        ])
        
        # Add audio codec if needed
        if audio_filters or any(e.type == ElementType.VIDEO and e.audio for e in request.elements):
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        
        # Add output file
        cmd.append(output_path)
        
        return cmd

    @staticmethod
    def get_job_dir(job_id: str) -> str:
        """Get the job directory path."""
        return os.path.join(os.getcwd(), "jobs", job_id)

    @staticmethod
    def get_status_path(job_id: str) -> str:
        """Get the status file path for a job."""
        return os.path.join(FFmpegService.get_job_dir(job_id), "status.json")

    @staticmethod
    def get_output_path(job_id: str) -> str:
        """Get the output file path for a job."""
        return os.path.join(FFmpegService.get_job_dir(job_id), "output.mp4")

    @staticmethod
    def save_job(request: VideoRequest, job_id: str) -> str:
        """Save the job input to a file."""
        # Create jobs directory if it doesn't exist
        jobs_dir = FFmpegService.get_job_dir(job_id)
        os.makedirs(jobs_dir, exist_ok=True)
        
        # Save input.json
        input_path = os.path.join(jobs_dir, "input.json")
        with open(input_path, "w") as f:
            json.dump(request.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Initialize status.json
        status_path = FFmpegService.get_status_path(job_id)
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
        
        return input_path

    @staticmethod
    def get_job_status(job_id: str) -> Dict[str, Any]:
        """Get the status of a job."""
        status_path = FFmpegService.get_status_path(job_id)
        if not os.path.exists(status_path):
            return None
        
        with open(status_path, "r") as f:
            return json.load(f)

    @staticmethod
    def update_job_status(job_id: str, status: JobStatus, error: Optional[str] = None):
        """Update the status of a job."""
        status_path = FFmpegService.get_status_path(job_id)
        if not os.path.exists(status_path):
            return
        
        with open(status_path, "r") as f:
            job_status = json.load(f)
        
        job_status["status"] = status
        if error:
            job_status["error"] = error
        if status == JobStatus.COMPLETED:
            job_status["completed_at"] = datetime.utcnow().isoformat()
            job_status["output_url"] = f"/jobs/{job_id}/output.mp4"
        
        with open(status_path, "w") as f:
            json.dump(job_status, f, indent=2, ensure_ascii=False) 