"""Google Gemini embedding implementation."""

import logging

from google import genai

from core import config
from core.config import GEMINI_EMBEDDING_MODEL

logger = logging.getLogger("engine")

_client = None


def get_client():
    """Returns a cached Gemini client instance."""
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment.")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def get_embedding(text: str) -> list[float]:
    """Generates a vector embedding for the given text using Gemini.

    Args:
        text: The text to embed.

    Returns:
        A list of floats representing the embedding.
    """
    if not text:
        return []

    results = get_embeddings_batch([text])
    return results[0] if results else []


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generates multiple embeddings in a single Gemini API call.

    Args:
        texts: A list of text strings to embed.

    Returns:
        A list of embedding vectors (list of floats).
    """
    if not texts:
        return []

    try:
        client = get_client()
        # Gemini's embed_content naturally supports lists of strings
        logger.info(f"Calling Gemini embeddings for {len(texts)} texts")
        response = client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL, contents=texts, config={"output_dimensionality": 768}
        )

        if not response.embeddings:
            logger.error("No embeddings returned from Gemini API")
            return []

        return [e.values for e in response.embeddings]
    except Exception as e:
        logger.error(f"Failed to get batch embeddings from Gemini: {e}")
        # Return empty instead of raising to allow pipeline to continue with other steps if possible,
        # though add_memory will fail gracefully.
        return []
