from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum
import logging
from datetime import datetime

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
        self.jobs: Dict[str, JobStatus] = {}
    
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
        self.jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Get a job status by ID"""
        return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, result: FrameResult) -> Optional[JobStatus]:
        """Update a job with a new frame result"""
        job = self.jobs.get(job_id)
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
        
        return job
    
    def set_job_error(self, job_id: str, error: str) -> Optional[JobStatus]:
        """Set a job to failed state with an error message"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        job.status = JobStatusEnum.FAILED
        job.error = error
        job.updated_at = datetime.utcnow()
        
        return job
    
    def update_job_status(self, job_id: str, status: str) -> Optional[JobStatus]:
        """Update a job's status"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        job.status = JobStatusEnum(status)
        job.updated_at = datetime.utcnow()
        if status == JobStatusEnum.COMPLETED:
            job.completed_frames = job.total_frames
        
        return job 