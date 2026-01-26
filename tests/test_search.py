"""Search endpoint tests."""

from unittest.mock import patch, AsyncMock


def test_search_returns_results(client):
    """Search endpoint should return ranked results."""
    with patch("app.api.routes.search.hybrid_search", new_callable=AsyncMock) as mock:
        mock.return_value = [
            {
                "document_id": "12345678-1234-1234-1234-123456789abc",
                "chunk_id": "87654321-4321-4321-4321-cba987654321",
                "score": 0.89,
                "snippet": "...force majeure clauses shall apply...",
                "metadata": {"filename": "contract.pdf", "page": 12},
            }
        ]

        response = client.post("/search", json={"query": "force majeure", "limit": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "force majeure"
    assert len(data["results"]) == 1
    assert data["results"][0]["score"] == 0.89


def test_search_validates_query(client):
    """Search endpoint should reject empty queries."""
    response = client.post("/search", json={"query": "", "limit": 10})

    assert response.status_code == 422  # Validation error
