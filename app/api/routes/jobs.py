"""Job status endpoint."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Job, Document, DocumentStatus
from app.schemas import JobStatusResponse, JobProgress, FileStatus

router = APIRouter()


async def get_job_with_documents(job_id: uuid.UUID, db: AsyncSession) -> dict | None:
    """Get job with its documents."""
    result = await db.execute(
        select(Job).where(Job.id == job_id).options(selectinload(Job.documents))
    )
    job = result.scalar_one_or_none()

    if not job:
        return None

    completed = sum(1 for d in job.documents if d.status == DocumentStatus.COMPLETED)
    failed = sum(1 for d in job.documents if d.status == DocumentStatus.FAILED)

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "progress": {
            "total": job.total_files,
            "completed": completed,
            "failed": failed,
        },
        "files": [
            {
                "filename": d.filename,
                "status": d.status.value,
                "error": d.error_message,
            }
            for d in job.documents
        ],
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of a processing job.

    Returns progress information and per-file status.
    """
    result = await get_job_with_documents(job_id, db)

    if not result:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=uuid.UUID(result["job_id"]),
        status=result["status"],
        progress=JobProgress(**result["progress"]),
        files=[FileStatus(**f) for f in result["files"]],
        created_at=datetime.fromisoformat(result["created_at"]),
        updated_at=datetime.fromisoformat(result["updated_at"]),
    )
