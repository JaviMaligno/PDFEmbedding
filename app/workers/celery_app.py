"""Celery application configuration."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "pdf_embedding",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="pdf_processing",
    task_queues={
        "pdf_processing": {"exchange": "pdf_processing", "routing_key": "pdf"},
        "ocr_extraction": {"exchange": "ocr_extraction", "routing_key": "ocr"},
        "embedding_gen": {"exchange": "embedding_gen", "routing_key": "embed"},
    },
    task_routes={
        "app.workers.tasks.process_document": {"queue": "pdf_processing"},
        "app.workers.tasks.run_ocr": {"queue": "ocr_extraction"},
        "app.workers.tasks.generate_embeddings_task": {"queue": "embedding_gen"},
    },
    task_annotations={
        "app.workers.tasks.run_ocr": {"rate_limit": "10/m"},
        "app.workers.tasks.generate_embeddings_task": {"rate_limit": "60/m"},
    },
)
