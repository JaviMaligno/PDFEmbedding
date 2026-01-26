"""OCR service tests."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.ocr_service import extract_text_with_ocr


@pytest.mark.asyncio
async def test_extract_text_with_gemini():
    """OCR service should extract text using Gemini."""
    image_bytes = b"fake png data"

    with patch("app.services.ocr_service.settings") as mock_settings:
        mock_settings.ocr_provider = "gemini"
        mock_settings.gemini_api_key = "fake-key"

        with patch("app.services.ocr_service.genai") as mock_genai:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Extracted text from image"
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            result = await extract_text_with_ocr(image_bytes)

    assert result == "Extracted text from image"
