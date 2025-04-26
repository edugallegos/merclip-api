import os
import subprocess
import glob
import shutil
from typing import Optional
from app.services.video_pipeline.steps.base_step import BaseStep
from app.services.video_pipeline.context import VideoContext

class CreateCollageStep(BaseStep):
    """Step to create a collage of video frames."""
    
    def __init__(self, output_dir: str = "generated_images/videos/collages", enabled: bool = True):
        super().__init__("create_collage", enabled)
        self.collages_dir = output_dir
        os.makedirs(self.collages_dir, exist_ok=True)
    
    def _extract_scene_frames(self, video_path: str, frames_dir: str, threshold: float = 0.4) -> None:
        """Extract frames at scene changes.
        
        Args:
            video_path: Path to video file
            frames_dir: Directory to save frames
            threshold: Scene change detection threshold (0-1)
        """
        self.logger.info(f"Extracting scene frames from {video_path} with threshold {threshold}")
        extract_cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"select='gt(scene,{threshold})',scale=320:180",
            '-vsync', 'vfr',
            f'{frames_dir}/frame_%03d.jpg'
        ]
        subprocess.run(
            extract_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True
        )
    
    def _extract_evenly_spaced_frames(self, video_path: str, frames_dir: str, interval_seconds: int = 2) -> None:
        """Extract frames at regular intervals.
        
        Args:
            video_path: Path to video file
            frames_dir: Directory to save frames
            interval_seconds: Interval between frames in seconds
        """
        self.logger.info(f"Extracting evenly spaced frames from {video_path} every {interval_seconds} seconds")
        extract_cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"fps=1/{interval_seconds},scale=320:180",
            '-vsync', 'vfr',
            f'{frames_dir}/frame_%03d.jpg'
        ]
        subprocess.run(
            extract_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True
        )
    
    def _create_collage(self, frames_dir: str, output_path: str, max_frames: int) -> None:
        """Create a collage from the extracted frames.
        
        Args:
            frames_dir: Directory containing frames
            output_path: Path to save the collage
            max_frames: Maximum number of frames to include
        """
        all_frames = sorted(glob.glob(os.path.join(frames_dir, '*.jpg')))
        selected_frames = all_frames[:max_frames]
        
        # Safety: Remove extra frames if needed
        for extra_frame in all_frames[max_frames:]:
            os.remove(extra_frame)
        
        self.logger.info(f"Creating collage with {len(selected_frames)} frames")
        
        tile_cols = 3 if len(selected_frames) > 4 else 2
        tile_rows = (len(selected_frames) + tile_cols - 1) // tile_cols
        
        collage_cmd = [
            'ffmpeg', '-pattern_type', 'glob', '-i', f'{frames_dir}/*.jpg',
            '-filter_complex', f'tile={tile_cols}x{tile_rows}',
            output_path
        ]
        subprocess.run(
            collage_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True
        )
        
        self.logger.info(f"Collage saved to {output_path}")
    
    def process(self, context: VideoContext) -> VideoContext:
        """Process the video context to create a collage.
        
        Args:
            context: The video context containing video_path
            
        Returns:
            The updated video context with collage_path set
        """
        # Skip if video_path is missing or doesn't exist
        if not context.video_path or not os.path.exists(context.video_path):
            self.logger.error("Missing or nonexistent video_path, cannot create collage")
            context.add_error("Missing or nonexistent video_path")
            return context
        
        try:
            # Create a unique output path for the collage
            video_basename = os.path.basename(context.video_path).split('.')[0]
            frames_dir = os.path.join(self.collages_dir, f"{video_basename}_frames")
            collage_path = os.path.join(self.collages_dir, f"{video_basename}_collage.jpg")
            
            # Clean frames directory
            if os.path.exists(frames_dir):
                shutil.rmtree(frames_dir)
            os.makedirs(frames_dir, exist_ok=True)
            
            max_frames = 6  # Maximum number of frames in the collage
            
            # Step 1: Try scene detection first
            try:
                self.logger.info("Attempting scene-based frame extraction")
                self._extract_scene_frames(context.video_path, frames_dir)
                
                # Step 2: Check how many frames were captured
                all_frames = glob.glob(os.path.join(frames_dir, '*.jpg'))
                self.logger.info(f"Scene frames found: {len(all_frames)}")
                
                # Step 3: If not enough, fallback to evenly spaced
                if len(all_frames) < 4:
                    self.logger.info("Not enough scene changes detected, falling back to evenly spaced frames")
                    shutil.rmtree(frames_dir)
                    os.makedirs(frames_dir, exist_ok=True)
                    self._extract_evenly_spaced_frames(context.video_path, frames_dir)
            except Exception as e:
                self.logger.warning(f"Scene detection failed: {str(e)}, falling back to evenly spaced frames")
                shutil.rmtree(frames_dir)
                os.makedirs(frames_dir, exist_ok=True)
                self._extract_evenly_spaced_frames(context.video_path, frames_dir)
            
            # Step 4: Create collage
            self._create_collage(frames_dir, collage_path, max_frames)
            
            # Step 5: Clean up frames directory
            shutil.rmtree(frames_dir)
            
            # Store the collage path in the context
            context.collage_path = collage_path
            self.logger.info(f"Successfully created collage at: {collage_path}")
            self.logger.info(f"Context collage_path is now set to: {context.collage_path}")
            
            # Verify file existence
            if os.path.exists(collage_path):
                self.logger.info(f"Verified: Collage file exists at {collage_path}")
            else:
                self.logger.error(f"Error: Collage file does not exist at {collage_path}")
            
            return context
            
        except Exception as e:
            error_msg = f"Error creating collage: {str(e)}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
            
            # Clean up any temporary files
            if 'frames_dir' in locals() and os.path.exists(frames_dir):
                shutil.rmtree(frames_dir)
            
            return context 