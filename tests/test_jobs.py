"""Job status endpoint tests."""

from unittest.mock import patch, AsyncMock
import uuid


def test_get_job_status_returns_progress(client):
    """Job status endpoint should return job progress."""
    job_id = str(uuid.uuid4())

    with patch("app.api.routes.jobs.get_job_with_documents", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "job_id": job_id,
            "status": "processing",
            "progress": {"total": 3, "completed": 1, "failed": 0},
            "files": [
                {"filename": "doc1.pdf", "status": "completed", "error": None},
                {"filename": "doc2.pdf", "status": "processing", "error": None},
                {"filename": "doc3.pdf", "status": "pending", "error": None},
            ],
            "created_at": "2026-01-26T10:00:00Z",
            "updated_at": "2026-01-26T10:01:00Z",
        }

        response = client.get(f"/jobs/{job_id}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "processing"
    assert data["progress"]["total"] == 3


def test_get_job_status_not_found(client):
    """Job status endpoint should return 404 for unknown job."""
    job_id = str(uuid.uuid4())

    with patch("app.api.routes.jobs.get_job_with_documents", new_callable=AsyncMock) as mock:
        mock.return_value = None

        response = client.get(f"/jobs/{job_id}/status")

    assert response.status_code == 404
