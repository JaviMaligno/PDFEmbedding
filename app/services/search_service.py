"""Hybrid search service combining BM25 and vector search."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import generate_query_embedding


def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """
    Combine vector and BM25 results using Reciprocal Rank Fusion.

    Args:
        vector_results: Results from vector similarity search.
        bm25_results: Results from BM25 full-text search.
        k: Ranking constant (default 60).

    Returns:
        Combined and re-ranked results.
    """
    scores = {}

    # Score from vector search
    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, {"score": 0, "data": result})
        scores[chunk_id]["score"] += 1 / (k + rank)

    # Score from BM25 search
    for rank, result in enumerate(bm25_results, start=1):
        chunk_id = result["chunk_id"]
        if chunk_id not in scores:
            scores[chunk_id] = {"score": 0, "data": result}
        scores[chunk_id]["score"] += 1 / (k + rank)

    # Sort by combined score
    sorted_results = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)

    return [
        {**item[1]["data"], "rrf_score": item[1]["score"]}
        for item in sorted_results
    ]


async def _vector_search(
    query_embedding: list[float],
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    """Execute vector similarity search using pgvector."""
    query = text(
        """
        SELECT
            c.id as chunk_id,
            c.document_id,
            c.content,
            c.page_number,
            d.filename,
            1 - (c.embedding <=> :embedding::vector) as score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> :embedding::vector
        LIMIT :limit
        """
    )

    result = await db.execute(
        query,
        {"embedding": str(query_embedding), "limit": limit},
    )

    rows = result.fetchall()

    return [
        {
            "chunk_id": str(row.chunk_id),
            "document_id": str(row.document_id),
            "content": row.content,
            "page_number": row.page_number,
            "filename": row.filename,
            "score": row.score,
        }
        for row in rows
    ]


async def _bm25_search(
    query: str,
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    """Execute BM25 full-text search using PostgreSQL."""
    query_sql = text(
        """
        SELECT
            c.id as chunk_id,
            c.document_id,
            c.content,
            c.page_number,
            d.filename,
            ts_rank_cd(to_tsvector('english', c.content), plainto_tsquery('english', :query)) as score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', :query)
        ORDER BY score DESC
        LIMIT :limit
        """
    )

    result = await db.execute(query_sql, {"query": query, "limit": limit})
    rows = result.fetchall()

    return [
        {
            "chunk_id": str(row.chunk_id),
            "document_id": str(row.document_id),
            "content": row.content,
            "page_number": row.page_number,
            "filename": row.filename,
            "score": row.score,
        }
        for row in rows
    ]


async def hybrid_search(
    query: str,
    db: AsyncSession,
    limit: int = 10,
    threshold: float = 0.0,
) -> list[dict]:
    """
    Execute hybrid search combining vector and BM25 search.

    Args:
        query: Search query string.
        db: Database session.
        limit: Maximum results to return.
        threshold: Minimum score threshold.

    Returns:
        List of search results with snippets and metadata.
    """
    # Generate query embedding
    query_embedding = await generate_query_embedding(query)

    # Execute both searches in parallel
    vector_results = await _vector_search(query_embedding, db, limit=50)
    bm25_results = await _bm25_search(query, db, limit=50)

    # Combine with RRF
    combined = reciprocal_rank_fusion(vector_results, bm25_results)

    # Filter by threshold and limit
    results = [r for r in combined if r["rrf_score"] >= threshold][:limit]

    # Format for response
    return [
        {
            "document_id": r["document_id"],
            "chunk_id": r["chunk_id"],
            "score": r["rrf_score"],
            "snippet": r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"],
            "metadata": {
                "filename": r["filename"],
                "page": r["page_number"],
            },
        }
        for r in results
    ]
