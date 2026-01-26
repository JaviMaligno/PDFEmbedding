"""PDF processor service tests."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.pdf_processor import extract_text_from_pdf, needs_ocr


def test_needs_ocr_returns_true_for_low_text():
    """Pages with little text should trigger OCR."""
    assert needs_ocr("ab") is True
    assert needs_ocr("a" * 10) is True


def test_needs_ocr_returns_false_for_sufficient_text():
    """Pages with enough text should not trigger OCR."""
    assert needs_ocr("a" * 100) is False


@pytest.mark.asyncio
async def test_extract_text_returns_pages():
    """PDF processor should return text per page."""
    with patch("app.services.pdf_processor.fitz.open") as mock_fitz:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Page 1 content with enough text to pass threshold"
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.__len__ = lambda self: 1
        mock_fitz.return_value.__enter__ = lambda self: mock_doc
        mock_fitz.return_value.__exit__ = lambda *args: None

        result = await extract_text_from_pdf("/fake/path.pdf")

    assert len(result) == 1
    assert "Page 1 content" in result[0]["text"]
