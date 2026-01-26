"""Search-related Pydantic schemas."""

import uuid

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request schema for search endpoint."""

    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchResultMetadata(BaseModel):
    """Metadata for a search result."""

    filename: str
    page: int | None


class SearchResult(BaseModel):
    """A single search result."""

    document_id: uuid.UUID
    chunk_id: uuid.UUID
    score: float
    snippet: str
    metadata: SearchResultMetadata


class SearchResponse(BaseModel):
    """Response schema for search endpoint."""

    query: str
    results: list[SearchResult]
    total: int
