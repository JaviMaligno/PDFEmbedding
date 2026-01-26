"""Search endpoint for semantic queries."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SearchRequest, SearchResponse, SearchResult, SearchResultMetadata

router = APIRouter()


async def execute_search(query: str, limit: int, threshold: float, db: AsyncSession) -> dict:
    """
    Execute hybrid search (BM25 + vector).

    This is a placeholder that will be implemented in the search service.
    """
    # TODO: Implement actual search in services/search_service.py
    return {
        "query": query,
        "results": [],
        "total": 0,
    }


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search documents using hybrid semantic search.

    Combines BM25 keyword matching with vector similarity.
    """
    result = await execute_search(request.query, request.limit, request.threshold, db)

    return SearchResponse(
        query=result["query"],
        results=[
            SearchResult(
                document_id=uuid.UUID(r["document_id"]),
                chunk_id=uuid.UUID(r["chunk_id"]),
                score=r["score"],
                snippet=r["snippet"],
                metadata=SearchResultMetadata(**r["metadata"]),
            )
            for r in result["results"]
        ],
        total=result["total"],
    )
