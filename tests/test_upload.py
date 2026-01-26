"""Upload endpoint tests."""

import io
from unittest.mock import patch, AsyncMock


def test_upload_single_pdf_returns_job_id(client):
    """Upload endpoint should accept PDF and return job_id."""
    pdf_content = b"%PDF-1.4 fake pdf content"
    files = {"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}

    with patch("app.api.routes.upload.process_upload", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "job_id": "12345678-1234-1234-1234-123456789abc",
            "file_count": 1,
            "status": "pending",
        }

        response = client.post("/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["file_count"] == 1
    assert data["status"] == "pending"


def test_upload_rejects_non_pdf(client):
    """Upload endpoint should reject non-PDF files."""
    files = {"files": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}

    response = client.post("/upload", files=files)

    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()
