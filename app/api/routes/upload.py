"""Upload endpoint for PDF ingestion."""

import hashlib
import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Job, JobStatus, Document, DocumentStatus
from app.schemas import UploadResponse

router = APIRouter()


async def process_upload(
    files: list[UploadFile],
    db: AsyncSession,
) -> dict:
    """Process uploaded files and create job."""
    # Create job
    job = Job(total_files=len(files), status=JobStatus.PENDING)
    db.add(job)
    await db.flush()

    # Process each file
    for file in files:
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Save file to storage
        file_path = os.path.join(settings.pdf_storage_path, f"{uuid.uuid4()}_{file.filename}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)

        # Create document record
        document = Document(
            job_id=job.id,
            filename=file.filename,
            file_path=file_path,
            file_hash=file_hash,
            status=DocumentStatus.PENDING,
        )
        db.add(document)

    await db.commit()
    await db.refresh(job)

    # TODO: Enqueue Celery task here

    return {
        "job_id": str(job.id),
        "file_count": len(files),
        "status": job.status.value,
    }


@router.post("/upload", response_model=UploadResponse)
async def upload_pdfs(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload one or more PDF files for processing.

    Returns a job_id to track processing status.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate all files are PDFs
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are accepted. Got: {file.filename}",
            )
        if file.content_type and file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type for {file.filename}. Expected application/pdf",
            )

    result = await process_upload(files, db)

    return UploadResponse(
        job_id=uuid.UUID(result["job_id"]),
        file_count=result["file_count"],
        status=JobStatus(result["status"]),
    )
