"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import upload, jobs, search

app = FastAPI(
    title="PDF Embedding Service",
    description="Ingest PDFs and search with hybrid semantic search",
    version="0.1.0",
)

# Include routers
app.include_router(upload.router, tags=["upload"])
app.include_router(jobs.router, tags=["jobs"])
app.include_router(search.router, tags=["search"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
