from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum
import logging
from datetime import datetime
import sqlite3
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class JobStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class FrameResult(BaseModel):
    id: str
    success: bool
    frames_path: Optional[str] = None
    error: Optional[str] = None

class JobStatus(BaseModel):
    job_id: str
    request_id: str
    status: JobStatusEnum
    total_frames: int
    completed_frames: int
    results: List[FrameResult]
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None

class JobStatusManager:
    def __init__(self):
        db_folder = Path("generated_images")
        db_folder.mkdir(exist_ok=True)
        self.db_path = db_folder / "job_status.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create jobs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            status TEXT NOT NULL,
            total_frames INTEGER NOT NULL,
            completed_frames INTEGER NOT NULL,
            results TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            error TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _job_from_row(self, row) -> JobStatus:
        """Convert a database row to a JobStatus object"""
        results_data = json.loads(row[5])
        results = [FrameResult(**r) for r in results_data]
        
        return JobStatus(
            job_id=row[0],
            request_id=row[1],
            status=JobStatusEnum(row[2]),
            total_frames=row[3],
            completed_frames=row[4],
            results=results,
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            error=row[8]
        )
    
    def create_job(self, job_id: str, request_id: str, total_frames: int) -> JobStatus:
        """Create a new job status entry"""
        job = JobStatus(
            job_id=job_id,
            request_id=request_id,
            status=JobStatusEnum.PENDING,
            total_frames=total_frames,
            completed_frames=0,
            results=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job.job_id,
                job.request_id,
                job.status.value,
                job.total_frames,
                job.completed_frames,
                json.dumps([r.model_dump() for r in job.results]),
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
                job.error
            )
        )
        
        conn.commit()
        conn.close()
        
        return job
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Get a job status by ID"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        return self._job_from_row(row)
    
    def update_job(self, job_id: str, result: FrameResult) -> Optional[JobStatus]:
        """Update a job with a new frame result"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        job.results.append(result)
        job.completed_frames += 1
        job.updated_at = datetime.utcnow()
        
        if job.completed_frames == job.total_frames:
            # Check if all frames were successful
            if all(r.success for r in job.results):
                job.status = JobStatusEnum.COMPLETED
            else:
                job.status = JobStatusEnum.FAILED
                job.error = "Some frames failed to generate"
        else:
            job.status = JobStatusEnum.PROCESSING
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE jobs SET status = ?, completed_frames = ?, results = ?, updated_at = ?, error = ? WHERE job_id = ?",
            (
                job.status.value,
                job.completed_frames,
                json.dumps([r.model_dump() for r in job.results]),
                job.updated_at.isoformat(),
                job.error,
                job.job_id
            )
        )
        
        conn.commit()
        conn.close()
        
        return job
    
    def set_job_error(self, job_id: str, error: str) -> Optional[JobStatus]:
        """Set a job to failed state with an error message"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        job.status = JobStatusEnum.FAILED
        job.error = error
        job.updated_at = datetime.utcnow()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE job_id = ?",
            (
                job.status.value,
                job.error,
                job.updated_at.isoformat(),
                job.job_id
            )
        )
        
        conn.commit()
        conn.close()
        
        return job
    
    def update_job_status(self, job_id: str, status: str) -> Optional[JobStatus]:
        """Update a job's status"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        job.status = JobStatusEnum(status)
        job.updated_at = datetime.utcnow()
        if status == JobStatusEnum.COMPLETED:
            job.completed_frames = job.total_frames
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE jobs SET status = ?, completed_frames = ?, updated_at = ? WHERE job_id = ?",
            (
                job.status.value,
                job.completed_frames,
                job.updated_at.isoformat(),
                job.job_id
            )
        )
        
        conn.commit()
        conn.close()
        
        return job 