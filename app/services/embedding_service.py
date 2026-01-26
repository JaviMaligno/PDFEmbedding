"""Embedding generation service using OpenAI."""

from openai import OpenAI

from app.config import settings

openai_client = OpenAI(api_key=settings.openai_api_key)


async def generate_embeddings(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.
        batch_size: Number of texts per API call.

    Returns:
        List of embedding vectors.
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        response = openai_client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )

        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def generate_query_embedding(query: str) -> list[float]:
    """
    Generate embedding for a search query.

    Args:
        query: The search query text.

    Returns:
        Embedding vector for the query.
    """
    response = openai_client.embeddings.create(
        model=settings.embedding_model,
        input=query,
    )

    return response.data[0].embedding
