"""PDF text extraction service."""

import fitz  # PyMuPDF

MIN_TEXT_LENGTH = 50  # Minimum characters to consider page as having text


def needs_ocr(text: str) -> bool:
    """Check if page text is too short and needs OCR."""
    return len(text.strip()) < MIN_TEXT_LENGTH


async def extract_text_from_pdf(file_path: str) -> list[dict]:
    """
    Extract text from PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of dicts with page_number, text, and needs_ocr flag.
    """
    pages = []

    with fitz.open(file_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()

            pages.append(
                {
                    "page_number": page_num,
                    "text": text,
                    "needs_ocr": needs_ocr(text),
                }
            )

    return pages


async def get_page_count(file_path: str) -> int:
    """Get the number of pages in a PDF."""
    with fitz.open(file_path) as doc:
        return len(doc)


async def pdf_page_to_image(file_path: str, page_number: int) -> bytes:
    """
    Convert a PDF page to a PNG image.

    Args:
        file_path: Path to the PDF file.
        page_number: 1-indexed page number.

    Returns:
        PNG image bytes.
    """
    with fitz.open(file_path) as doc:
        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=150)
        return pix.tobytes("png")
