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
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_videos'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create processed_videos table with all fields
            logger.info("Creating processed_videos table")
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
                ai_review TEXT,
                metadata TEXT NOT NULL
            )
            ''')
        else:
            # Table exists, check columns
            logger.info("Processed videos table already exists, checking columns")
            
            # Get table info
            cursor.execute("PRAGMA table_info(processed_videos)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            # Check if ai_review column exists
            if "ai_review" not in columns:
                logger.info("Adding ai_review column to processed_videos table")
                cursor.execute("ALTER TABLE processed_videos ADD COLUMN ai_review TEXT")
            
            # Check metadata column
            if "metadata" not in columns:
                logger.info("Adding metadata column to processed_videos table")
                cursor.execute("ALTER TABLE processed_videos ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'")
            else:
                # Check if metadata can be NULL
                metadata_row = columns["metadata"]
                is_not_null = metadata_row[3] == 1
                
                if not is_not_null:
                    # SQLite doesn't allow modifying constraints, so we need to recreate the table
                    logger.warning("Metadata column allows NULL, updating schema")
                    try:
                        # Start a transaction
                        cursor.execute("BEGIN TRANSACTION")
                        
                        # 1. Create a backup table with correct schema
                        cursor.execute('''
                        CREATE TABLE processed_videos_new (
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
                            ai_review TEXT,
                            metadata TEXT NOT NULL DEFAULT '{}'
                        )
                        ''')
                        
                        # 2. Copy data, ensuring metadata has a value
                        cursor.execute('''
                        INSERT INTO processed_videos_new 
                        SELECT 
                            video_id, url, platform, file_path, file_url, 
                            audio_path, audio_url, srt_path, srt_url, 
                            collage_path, collage_url, status, created_at, 
                            updated_at, language_code, ai_review, 
                            COALESCE(metadata, '{}') as metadata
                        FROM processed_videos
                        ''')
                        
                        # 3. Drop the old table
                        cursor.execute("DROP TABLE processed_videos")
                        
                        # 4. Rename the new table
                        cursor.execute("ALTER TABLE processed_videos_new RENAME TO processed_videos")
                        
                        # Commit transaction
                        conn.commit()
                        logger.info("Successfully updated processed_videos table schema for metadata column")
                    except Exception as e:
                        # Rollback in case of error
                        conn.rollback()
                        logger.error(f"Error updating table schema: {str(e)}")
        
        conn.commit()
        conn.close()
        logger.info("Processed videos database initialized")
    
    def _video_from_row(self, row) -> ProcessedVideo:
        """Convert a database row to a ProcessedVideo object"""
        # First get the column information to ensure correct mapping
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA table_info(processed_videos)")
            columns = {row[1]: idx for idx, row in enumerate(cursor.fetchall())}
            logger.debug(f"Column mapping: {columns}")
            
            # Get values by column name rather than assuming positions
            video_id = row[columns.get("video_id", 0)]
            url = row[columns.get("url", 1)]
            platform = row[columns.get("platform", 2)]
            file_path = row[columns.get("file_path", 3)]
            file_url = row[columns.get("file_url", 4)]
            audio_path = row[columns.get("audio_path", 5)]
            audio_url = row[columns.get("audio_url", 6)]
            srt_path = row[columns.get("srt_path", 7)]
            srt_url = row[columns.get("srt_url", 8)]
            collage_path = row[columns.get("collage_path", 9)]
            collage_url = row[columns.get("collage_url", 10)]
            status = row[columns.get("status", 11)]
            created_at = row[columns.get("created_at", 12)]
            updated_at = row[columns.get("updated_at", 13)]
            language_code = row[columns.get("language_code", 14)]
            ai_review = row[columns.get("ai_review", 15)]
            metadata_json = row[columns.get("metadata", 16)]
            
            logger.debug(f"Row data for video_id {video_id}:")
            logger.debug(f"  ai_review: {ai_review}")
            logger.debug(f"  metadata_json: {metadata_json}")
            
            # Parse metadata with proper error handling
            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
                logger.debug(f"Parsed metadata: {metadata}")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing metadata JSON for video_id {video_id}: {str(e)}")
                logger.error(f"Invalid metadata value: '{metadata_json}'")
                # Use empty dict as fallback
                metadata = {}
                
            # Create the ProcessedVideo object with explicitly mapped fields
            video = ProcessedVideo(
                video_id=video_id,
                url=url,
                platform=platform,
                file_path=file_path,
                file_url=file_url,
                audio_path=audio_path,
                audio_url=audio_url,
                srt_path=srt_path,
                srt_url=srt_url,
                collage_path=collage_path,
                collage_url=collage_url,
                status=VideoStatusEnum(status),
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at),
                language_code=language_code,
                ai_review=ai_review,
                metadata=metadata
            )
            logger.debug(f"Successfully converted database row to ProcessedVideo: {video.video_id}")
            return video
            
        except Exception as e:
            logger.error(f"Error in _video_from_row: {str(e)}")
            raise
        finally:
            conn.close()
    
    def save_video(self, video: ProcessedVideo) -> ProcessedVideo:
        """Save a processed video to the database"""
        logger.info(f"Saving video to database: {video.video_id}")
        logger.debug(f"Video metadata before saving: {repr(video.metadata)}")
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Ensure metadata is never NULL by using an empty dict if it's None
        if video.metadata is None:
            logger.warning(f"Video {video.video_id} had NULL metadata, replacing with empty dict")
            video.metadata = {}
        
        # Convert metadata to JSON string or use empty JSON object if anything fails
        try:
            if isinstance(video.metadata, dict):
                metadata_json = json.dumps(video.metadata)
                logger.debug(f"Converted metadata dict to JSON: {metadata_json}")
            else:
                logger.warning(f"Video {video.video_id} metadata is not a dict, forcing empty dict")
                metadata_json = "{}"
        except Exception as e:
            logger.error(f"Error converting metadata to JSON for video {video.video_id}: {str(e)}")
            logger.error(f"Problematic metadata: {repr(video.metadata)}")
            # Fallback to empty dict if metadata can't be serialized
            metadata_json = "{}"
        
        # Safety check - ensure metadata_json is never NULL 
        if not metadata_json:
            logger.warning(f"Empty metadata_json for video {video.video_id}, using empty JSON object")
            metadata_json = "{}"
            
        logger.info(f"Final metadata_json: '{metadata_json}'")
        
        # Check if video already exists
        cursor.execute("SELECT 1 FROM processed_videos WHERE video_id = :video_id", 
                      {"video_id": video.video_id})
        exists = cursor.fetchone()
        
        try:
            if exists:
                # Update existing video with named parameters
                logger.debug(f"Updating existing video record: {video.video_id}")
                update_query = """
                UPDATE processed_videos SET 
                url = :url, 
                platform = :platform, 
                file_path = :file_path, 
                file_url = :file_url, 
                audio_path = :audio_path,
                audio_url = :audio_url, 
                srt_path = :srt_path, 
                srt_url = :srt_url,
                collage_path = :collage_path, 
                collage_url = :collage_url, 
                status = :status, 
                updated_at = :updated_at,
                language_code = :language_code, 
                ai_review = :ai_review, 
                metadata = :metadata
                WHERE video_id = :video_id
                """
                
                update_params = {
                    "url": video.url,
                    "platform": video.platform,
                    "file_path": video.file_path,
                    "file_url": video.file_url,
                    "audio_path": video.audio_path,
                    "audio_url": video.audio_url,
                    "srt_path": video.srt_path,
                    "srt_url": video.srt_url,
                    "collage_path": video.collage_path,
                    "collage_url": video.collage_url,
                    "status": video.status.value,
                    "updated_at": datetime.utcnow().isoformat(),
                    "language_code": video.language_code,
                    "ai_review": video.ai_review,
                    "metadata": metadata_json,
                    "video_id": video.video_id
                }
                
                logger.debug(f"SQL update parameters: {update_params}")
                
                cursor.execute(update_query, update_params)
                logger.info(f"Updated video record for video_id: {video.video_id}")
            else:
                # Insert new video with named parameters
                logger.debug(f"Inserting new video record: {video.video_id}")
                
                # Get column names directly from the table schema
                cursor.execute("PRAGMA table_info(processed_videos)")
                columns = [row[1] for row in cursor.fetchall()]
                logger.debug(f"Table columns in order: {columns}")
                
                # Build the INSERT statement with named parameters
                placeholders = [f":{col}" for col in columns]
                insert_query = f"""
                INSERT INTO processed_videos ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                """
                
                # Create parameter dictionary matching column names
                insert_params = {
                    "video_id": video.video_id,
                    "url": video.url,
                    "platform": video.platform,
                    "file_path": video.file_path,
                    "file_url": video.file_url,
                    "audio_path": video.audio_path,
                    "audio_url": video.audio_url,
                    "srt_path": video.srt_path,
                    "srt_url": video.srt_url,
                    "collage_path": video.collage_path,
                    "collage_url": video.collage_url,
                    "status": video.status.value,
                    "created_at": video.created_at.isoformat(),
                    "updated_at": video.updated_at.isoformat(),
                    "language_code": video.language_code,
                    "ai_review": video.ai_review,
                    "metadata": metadata_json
                }
                
                logger.debug(f"SQL insert parameters: {insert_params}")
                
                try:
                    cursor.execute(insert_query, insert_params)
                    logger.info(f"Created new video record for video_id: {video.video_id}")
                except sqlite3.Error as insert_err:
                    logger.error(f"Insert error: {str(insert_err)}")
                    logger.error(f"SQL query: {insert_query}")
                    logger.error(f"Column order in table: {columns}")
                    raise
        except sqlite3.Error as e:
            conn.close()
            logger.error(f"SQLite error while saving video {video.video_id}: {str(e)}")
            logger.error(f"SQL Statement parameters: video_id={video.video_id}, metadata={metadata_json}")
            raise
        
        conn.commit()
        conn.close()
        
        return video
    
    def get_video(self, video_id: str) -> Optional[ProcessedVideo]:
        """Get a processed video by ID"""
        logger.debug(f"Retrieving video with ID: {video_id}")
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM processed_videos WHERE video_id = ?", (video_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"No video found with ID: {video_id}")
                return None
            
            logger.debug(f"Found video with ID: {video_id}")
            return self._video_from_row(row)
        except sqlite3.Error as e:
            logger.error(f"SQLite error retrieving video {video_id}: {str(e)}")
            raise
        finally:
            conn.close()
    
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
    
    def update_ai_review(self, video_id: str, ai_review: str) -> Optional[ProcessedVideo]:
        """Update the AI review of a processed video"""
        logger.info(f"Updating AI review for video_id: {video_id}")
        logger.debug(f"AI review content length: {len(ai_review) if ai_review else 0}")
        
        video = self.get_video(video_id)
        if not video:
            logger.warning(f"Cannot update AI review: video not found with ID: {video_id}")
            return None
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.utcnow()
        
        try:
            cursor.execute(
                "UPDATE processed_videos SET ai_review = ?, updated_at = ? WHERE video_id = ?",
                (ai_review, now.isoformat(), video_id)
            )
            
            conn.commit()
            
            # Check if the update was successful
            if cursor.rowcount == 0:
                logger.warning(f"AI review update affected 0 rows for video_id: {video_id}")
            else:
                logger.info(f"AI review updated successfully for video_id: {video_id}, rows affected: {cursor.rowcount}")
        except sqlite3.Error as e:
            logger.error(f"SQLite error updating AI review for video {video_id}: {str(e)}")
            raise
        finally:
            conn.close()
        
        video.ai_review = ai_review
        video.updated_at = now
        
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