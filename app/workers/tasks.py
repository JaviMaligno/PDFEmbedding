"""Celery task definitions for PDF processing pipeline."""

import uuid
from celery import chain
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.database import engine
from app.models import Document, DocumentStatus, Job, JobStatus, Chunk
from app.services.pdf_processor import extract_text_from_pdf, pdf_page_to_image, get_page_count
from app.services.ocr_service import extract_text_with_ocr
from app.services.chunker import chunk_text
from app.services.embedding_service import generate_embeddings


def get_sync_session():
    """Get synchronous database session for Celery tasks."""
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine

    from app.config import settings

    # Convert async URL to sync
    sync_url = settings.database_url.replace("+asyncpg", "")
    sync_engine = create_engine(sync_url)
    SessionLocal = sessionmaker(bind=sync_engine)
    return SessionLocal()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document(self, document_id: str):
    """
    Main task to process a document through the pipeline.

    Chains: extract_text -> run_ocr (if needed) -> chunk -> embed -> finalize
    """
    db = get_sync_session()

    try:
        doc = db.execute(select(Document).where(Document.id == uuid.UUID(document_id))).scalar_one()
        doc.status = DocumentStatus.PROCESSING
        db.commit()

        # Execute pipeline
        pipeline = chain(
            extract_text_task.s(document_id),
            chunk_text_task.s(document_id),
            generate_embeddings_task.s(document_id),
            finalize_document.s(document_id),
        )
        pipeline.apply_async()

    except Exception as exc:
        db.rollback()
        doc = db.execute(select(Document).where(Document.id == uuid.UUID(document_id))).scalar_one()
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def extract_text_task(self, document_id: str):
    """Extract text from PDF pages."""
    import asyncio

    db = get_sync_session()

    try:
        doc = db.execute(select(Document).where(Document.id == uuid.UUID(document_id))).scalar_one()

        # Extract text from PDF
        pages = asyncio.run(extract_text_from_pdf(doc.file_path))
        doc.page_count = len(pages)

        # Run OCR on pages that need it
        for page in pages:
            if page["needs_ocr"]:
                image_bytes = asyncio.run(pdf_page_to_image(doc.file_path, page["page_number"]))
                ocr_text = asyncio.run(extract_text_with_ocr(image_bytes))
                page["text"] = ocr_text

        db.commit()

        # Return extracted text for next step
        return {
            "document_id": document_id,
            "pages": pages,
        }

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True)
def chunk_text_task(self, extraction_result: dict, document_id: str):
    """Chunk extracted text."""
    pages = extraction_result["pages"]

    # Combine all page text
    full_text = "\n\n".join(p["text"] for p in pages if p["text"])

    # Chunk the text
    chunks = chunk_text(full_text)

    # Add page number info (approximate)
    page_boundaries = []
    current_pos = 0
    for page in pages:
        page_boundaries.append((current_pos, current_pos + len(page["text"]), page["page_number"]))
        current_pos += len(page["text"]) + 2  # +2 for \n\n

    return {
        "document_id": document_id,
        "chunks": chunks,
        "page_boundaries": page_boundaries,
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_embeddings_task(self, chunk_result: dict, document_id: str):
    """Generate embeddings for chunks."""
    import asyncio

    chunks = chunk_result["chunks"]
    texts = [c["content"] for c in chunks]

    try:
        embeddings = asyncio.run(generate_embeddings(texts))

        return {
            "document_id": document_id,
            "chunks": chunks,
            "embeddings": embeddings,
        }

    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def finalize_document(self, embedding_result: dict, document_id: str):
    """Save chunks to database and update document status."""
    db = get_sync_session()

    try:
        doc = db.execute(select(Document).where(Document.id == uuid.UUID(document_id))).scalar_one()

        chunks_data = embedding_result["chunks"]
        embeddings = embedding_result["embeddings"]

        # Create chunk records (bulk insert for efficiency)
        chunks = [
            Chunk(
                document_id=doc.id,
                chunk_index=chunk_data["chunk_index"],
                page_number=None,  # TODO: Calculate from page boundaries
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
                embedding=embedding,
            )
            for chunk_data, embedding in zip(chunks_data, embeddings)
        ]
        db.add_all(chunks)

        # Update document status
        doc.status = DocumentStatus.COMPLETED

        # Update job status (single transaction with document update)
        job = db.execute(select(Job).where(Job.id == doc.job_id)).scalar_one()
        job.processed_files += 1

        # Check if all documents are processed (use COUNT instead of fetching all rows)
        completed = db.execute(
            select(func.count()).select_from(Document).where(
                Document.job_id == job.id,
                Document.status == DocumentStatus.COMPLETED
            )
        ).scalar()
        failed = db.execute(
            select(func.count()).select_from(Document).where(
                Document.job_id == job.id,
                Document.status == DocumentStatus.FAILED
            )
        ).scalar()

        if completed + failed == job.total_files:
            if failed == 0:
                job.status = JobStatus.COMPLETED
            elif completed == 0:
                job.status = JobStatus.FAILED
            else:
                job.status = JobStatus.PARTIAL

        db.commit()

        return {"status": "completed", "document_id": document_id}

    except Exception as exc:
        db.rollback()
        doc = db.execute(select(Document).where(Document.id == uuid.UUID(document_id))).scalar_one()
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(exc)
        db.commit()
        raise
    finally:
        db.close()
