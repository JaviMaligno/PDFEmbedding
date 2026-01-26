"""FastAPI application entry point."""

import time
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.api.routes import upload, jobs, search
from app.metrics import http_requests_total, http_request_duration_seconds

app = FastAPI(
    title="PDF Embedding Service",
    description="Ingest PDFs and search with hybrid semantic search",
    version="0.1.0",
)

# Include routers
app.include_router(upload.router, tags=["upload"])
app.include_router(jobs.router, tags=["jobs"])
app.include_router(search.router, tags=["search"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to track request metrics."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = response.status_code

    http_requests_total.labels(endpoint=endpoint, method=method, status=status).inc()
    http_request_duration_seconds.labels(endpoint=endpoint).observe(duration)

    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
