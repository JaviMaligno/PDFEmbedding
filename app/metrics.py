"""Prometheus metrics for observability."""

from prometheus_client import Counter, Histogram, Gauge

# API metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

search_latency_seconds = Histogram(
    "search_latency_seconds",
    "Search request latency in seconds",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0],
)

# Ingestion metrics
jobs_total = Counter(
    "jobs_total",
    "Total jobs by status",
    ["status"],
)

documents_processed_total = Counter(
    "documents_processed_total",
    "Total documents processed by status",
    ["status"],
)

document_processing_duration_seconds = Histogram(
    "document_processing_duration_seconds",
    "Document processing duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

# Queue metrics
celery_queue_length = Gauge(
    "celery_queue_length",
    "Number of tasks in Celery queue",
    ["queue_name"],
)

# External API metrics
openai_requests_total = Counter(
    "openai_requests_total",
    "Total OpenAI API requests",
    ["endpoint", "status"],
)

openai_latency_seconds = Histogram(
    "openai_latency_seconds",
    "OpenAI API request latency in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

llm_ocr_requests_total = Counter(
    "llm_ocr_requests_total",
    "Total LLM OCR requests",
    ["provider", "status"],
)

llm_ocr_latency_seconds = Histogram(
    "llm_ocr_latency_seconds",
    "LLM OCR request latency in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
