"""Google Gemini embedding implementation."""

import logging
from google import genai
from core import config

logger = logging.getLogger("engine")

# Use gemini-embedding-001 and request 768 dimensions for compatibility
EMBEDDING_MODEL = "gemini-embedding-001"

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
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        # Gemini's embed_content naturally supports lists of strings
        print(f"Calling Gemini embeddings for {len(texts)} texts")
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
            config={'output_dimensionality': 768}
        )
        
        if not response.embeddings:
            logger.error("No embeddings returned from Gemini API")
            return []
            
        return [e.values for e in response.embeddings]
    except Exception as e:
        logger.error(f"Failed to get batch embeddings from Gemini: {e}")
        raise
