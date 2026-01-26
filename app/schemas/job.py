"""Job-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.job import JobStatus


class JobCreate(BaseModel):
    """Schema for creating a job (internal use)."""

    total_files: int


class FileStatus(BaseModel):
    """Status of a single file in a job."""

    filename: str
    status: str
    error: str | None = None


class JobProgress(BaseModel):
    """Progress information for a job."""

    total: int
    completed: int
    failed: int


class JobStatusResponse(BaseModel):
    """Response schema for job status endpoint."""

    job_id: uuid.UUID
    status: JobStatus
    progress: JobProgress
    files: list[FileStatus]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """Response schema for upload endpoint."""

    job_id: uuid.UUID
    file_count: int
    status: JobStatus
