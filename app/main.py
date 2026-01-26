"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="PDF Embedding Service",
    description="Ingest PDFs and search with hybrid semantic search",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
