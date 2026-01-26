"""Health check endpoint tests."""


def test_health_check_returns_healthy(client):
    """Health endpoint should return healthy status."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
