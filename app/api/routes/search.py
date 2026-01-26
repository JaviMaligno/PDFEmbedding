"""Search endpoint for semantic queries."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SearchRequest, SearchResponse, SearchResult, SearchResultMetadata
from app.services.search_service import hybrid_search

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search documents using hybrid semantic search.

    Combines BM25 keyword matching with vector similarity.
    """
    results = await hybrid_search(
        query=request.query,
        db=db,
        limit=request.limit,
        threshold=request.threshold,
    )

    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                document_id=uuid.UUID(r["document_id"]),
                chunk_id=uuid.UUID(r["chunk_id"]),
                score=r["score"],
                snippet=r["snippet"],
                metadata=SearchResultMetadata(**r["metadata"]),
            )
            for r in results
        ],
        total=len(results),
    )
