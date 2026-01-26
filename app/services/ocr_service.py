"""OCR service using Gemini or DeepSeek Vision APIs."""

import base64
import httpx
import google.generativeai as genai

from app.config import settings

OCR_PROMPT = """Extract all text from this image.
Return only the extracted text, preserving the original formatting and structure.
If there are tables, preserve them in a readable format.
If there is no text, return an empty string."""


async def extract_text_with_ocr(image_bytes: bytes) -> str:
    """
    Extract text from image using configured OCR provider.

    Args:
        image_bytes: PNG image bytes.

    Returns:
        Extracted text string.
    """
    if settings.ocr_provider == "gemini":
        return await _extract_with_gemini(image_bytes)
    elif settings.ocr_provider == "deepseek":
        return await _extract_with_deepseek(image_bytes)
    else:
        raise ValueError(f"Unknown OCR provider: {settings.ocr_provider}")


async def _extract_with_gemini(image_bytes: bytes) -> str:
    """Extract text using Google Gemini Vision."""
    genai.configure(api_key=settings.gemini_api_key)

    model = genai.GenerativeModel("gemini-1.5-flash")

    # Prepare image for Gemini
    image_data = {
        "mime_type": "image/png",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    response = model.generate_content([OCR_PROMPT, image_data])

    return response.text


async def _extract_with_deepseek(image_bytes: bytes) -> str:
    """Extract text using DeepSeek Vision API."""
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-vision",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": OCR_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
            },
            timeout=60.0,
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]
