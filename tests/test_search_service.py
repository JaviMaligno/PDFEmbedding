"""Search service tests."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.search_service import hybrid_search, reciprocal_rank_fusion


def test_reciprocal_rank_fusion_combines_rankings():
    """RRF should combine two ranked lists."""
    vector_results = [
        {"chunk_id": "a", "score": 0.9},
        {"chunk_id": "b", "score": 0.8},
        {"chunk_id": "c", "score": 0.7},
    ]
    bm25_results = [
        {"chunk_id": "b", "score": 5.0},
        {"chunk_id": "a", "score": 4.0},
        {"chunk_id": "d", "score": 3.0},
    ]

    combined = reciprocal_rank_fusion(vector_results, bm25_results, k=60)

    # Both 'a' and 'b' should be at the top since they appear in both lists
    chunk_ids = [r["chunk_id"] for r in combined[:2]]
    assert "a" in chunk_ids
    assert "b" in chunk_ids


@pytest.mark.asyncio
async def test_hybrid_search_returns_results():
    """Hybrid search should return combined results."""
    with patch("app.services.search_service.generate_query_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536

        with patch("app.services.search_service._vector_search", new_callable=AsyncMock) as mock_vector:
            mock_vector.return_value = [
                {
                    "chunk_id": "a",
                    "document_id": "doc-123",
                    "content": "Test content",
                    "page_number": 1,
                    "filename": "test.pdf",
                    "score": 0.9,
                }
            ]

            with patch("app.services.search_service._bm25_search", new_callable=AsyncMock) as mock_bm25:
                mock_bm25.return_value = [
                    {
                        "chunk_id": "a",
                        "document_id": "doc-123",
                        "content": "Test content",
                        "page_number": 1,
                        "filename": "test.pdf",
                        "score": 5.0,
                    }
                ]

                # Mock database session
                mock_db = AsyncMock()

                results = await hybrid_search("test query", mock_db, limit=10)

    assert len(results) >= 1
    assert results[0]["chunk_id"] == "a"
    assert results[0]["document_id"] == "doc-123"
    assert "snippet" in results[0]
    assert "metadata" in results[0]
