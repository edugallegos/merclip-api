import sqlite3
import json
import logging
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
from app.models.video import ProcessedVideo, VideoStatusEnum

logger = logging.getLogger(__name__)

class VideoManager:
    """Manager class for handling processed videos in the database."""
    
    def __init__(self):
        db_folder = Path("generated_images")
        db_folder.mkdir(exist_ok=True)
        self.db_path = db_folder / "processed_videos.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create processed_videos table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_videos (
            video_id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            platform TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_url TEXT NOT NULL,
            audio_path TEXT,
            audio_url TEXT,
            srt_path TEXT,
            srt_url TEXT,
            collage_path TEXT,
            collage_url TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            language_code TEXT NOT NULL,
            metadata TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Processed videos database initialized")
    
    def _video_from_row(self, row) -> ProcessedVideo:
        """Convert a database row to a ProcessedVideo object"""
        metadata = json.loads(row[15]) if row[15] else {}
        
        return ProcessedVideo(
            video_id=row[0],
            url=row[1],
            platform=row[2],
            file_path=row[3],
            file_url=row[4],
            audio_path=row[5],
            audio_url=row[6],
            srt_path=row[7],
            srt_url=row[8],
            collage_path=row[9],
            collage_url=row[10],
            status=VideoStatusEnum(row[11]),
            created_at=datetime.fromisoformat(row[12]),
            updated_at=datetime.fromisoformat(row[13]),
            language_code=row[14],
            metadata=metadata
        )
    
    def save_video(self, video: ProcessedVideo) -> ProcessedVideo:
        """Save a processed video to the database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Check if video already exists
        cursor.execute("SELECT 1 FROM processed_videos WHERE video_id = ?", (video.video_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing video
            cursor.execute(
                """
                UPDATE processed_videos SET 
                url = ?, platform = ?, file_path = ?, file_url = ?, 
                audio_path = ?, audio_url = ?, srt_path = ?, srt_url = ?,
                collage_path = ?, collage_url = ?, status = ?, updated_at = ?,
                language_code = ?, metadata = ?
                WHERE video_id = ?
                """,
                (
                    video.url, video.platform, video.file_path, video.file_url,
                    video.audio_path, video.audio_url, video.srt_path, video.srt_url,
                    video.collage_path, video.collage_url, video.status.value, 
                    datetime.utcnow().isoformat(), video.language_code, 
                    json.dumps(video.metadata), video.video_id
                )
            )
            logger.info(f"Updated video record for video_id: {video.video_id}")
        else:
            # Insert new video
            cursor.execute(
                """
                INSERT INTO processed_videos VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video.video_id, video.url, video.platform, video.file_path, 
                    video.file_url, video.audio_path, video.audio_url, 
                    video.srt_path, video.srt_url, video.collage_path, 
                    video.collage_url, video.status.value, 
                    video.created_at.isoformat(), 
                    video.updated_at.isoformat(),
                    video.language_code, json.dumps(video.metadata)
                )
            )
            logger.info(f"Created new video record for video_id: {video.video_id}")
        
        conn.commit()
        conn.close()
        
        return video
    
    def get_video(self, video_id: str) -> Optional[ProcessedVideo]:
        """Get a processed video by ID"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM processed_videos WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        return self._video_from_row(row)
    
    def get_videos(self, limit: int = 100, offset: int = 0, status: Optional[str] = None) -> List[ProcessedVideo]:
        """Get a list of processed videos, optionally filtered by status"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM processed_videos WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                (status, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM processed_videos ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                (limit, offset)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._video_from_row(row) for row in rows]
    
    def update_status(self, video_id: str, status: VideoStatusEnum) -> Optional[ProcessedVideo]:
        """Update the status of a processed video"""
        video = self.get_video(video_id)
        if not video:
            return None
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.utcnow()
        
        cursor.execute(
            "UPDATE processed_videos SET status = ?, updated_at = ? WHERE video_id = ?",
            (status.value, now.isoformat(), video_id)
        )
        
        conn.commit()
        conn.close()
        
        video.status = status
        video.updated_at = now
        
        logger.info(f"Updated status to {status.value} for video_id: {video_id}")
        
        return video
    
    def delete_video(self, video_id: str) -> bool:
        """Delete a processed video from the database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM processed_videos WHERE video_id = ?", (video_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"Deleted video record for video_id: {video_id}")
        
        return deleted 