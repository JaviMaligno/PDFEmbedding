"""Chunker service tests."""

from app.services.chunker import chunk_text


def test_chunk_text_splits_into_correct_sizes():
    """Chunker should split text into chunks of specified size."""
    text = "word " * 1000  # About 1000 tokens
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    # First chunk should have chunk_size tokens (approximately)
    assert chunks[0]["token_count"] <= 120  # Allow some margin


def test_chunk_text_preserves_overlap():
    """Chunks should have overlapping content."""
    text = "This is sentence one. This is sentence two. This is sentence three. " * 50
    chunks = chunk_text(text, chunk_size=50, overlap=10)

    # Check that adjacent chunks have some overlap
    if len(chunks) > 1:
        # Last words of chunk 0 should appear in start of chunk 1
        assert len(set(chunks[0]["content"].split()[-5:]) & set(chunks[1]["content"].split()[:10])) > 0


def test_chunk_text_returns_correct_structure():
    """Each chunk should have content, index, and token_count."""
    text = "Sample text for chunking test."
    chunks = chunk_text(text, chunk_size=100, overlap=10)

    assert len(chunks) >= 1
    assert "content" in chunks[0]
    assert "chunk_index" in chunks[0]
    assert "token_count" in chunks[0]
