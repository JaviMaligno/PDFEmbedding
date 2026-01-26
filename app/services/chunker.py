"""Text chunking service."""

import tiktoken

from app.config import settings


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken."""
    encoder = tiktoken.get_encoding(model)
    return len(encoder.encode(text))


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> list[dict]:
    """
    Split text into overlapping chunks.

    Args:
        text: The text to chunk.
        chunk_size: Maximum tokens per chunk (default from settings).
        overlap: Token overlap between chunks (default from settings).

    Returns:
        List of chunk dictionaries with content, chunk_index, and token_count.
    """
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap

    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(text)

    if len(tokens) <= chunk_size:
        return [
            {
                "content": text,
                "chunk_index": 0,
                "token_count": len(tokens),
            }
        ]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_content = encoder.decode(chunk_tokens)

        chunks.append(
            {
                "content": chunk_content,
                "chunk_index": chunk_index,
                "token_count": len(chunk_tokens),
            }
        )

        # Move start forward, accounting for overlap
        start = end - overlap if end < len(tokens) else end
        chunk_index += 1

    return chunks
