"""Embedding service tests."""

from unittest.mock import patch, MagicMock
import pytest

from app.services.embedding_service import generate_embeddings, generate_query_embedding


@pytest.mark.asyncio
async def test_generate_embeddings_returns_vectors():
    """Embedding service should return vectors for text chunks."""
    chunks = ["Hello world", "Test text"]

    with patch("app.services.embedding_service.openai_client") as mock_client:
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
        mock_client.embeddings.create.return_value = mock_response

        embeddings = await generate_embeddings(chunks)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1536


@pytest.mark.asyncio
async def test_generate_query_embedding_returns_single_vector():
    """Query embedding should return a single vector."""
    query = "test query"

    with patch("app.services.embedding_service.openai_client") as mock_client:
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response

        embedding = await generate_query_embedding(query)

    assert len(embedding) == 1536
