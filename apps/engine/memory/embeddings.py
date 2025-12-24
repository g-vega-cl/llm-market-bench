"""Google Gemini embedding implementation."""

import logging
from google import genai
from core import config

logger = logging.getLogger("engine")

# Use text-embedding-004 which has 768 dimensions
EMBEDDING_MODEL = "text-embedding-004"

def get_embedding(text: str) -> list[float]:
    """Generates a vector embedding for the given text using Gemini.

    Args:
        text: The text to embed.

    Returns:
        A list of floats representing the embedding.
    """
    if not text:
        return []

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )
        
        if not response.embeddings:
            logger.error("No embeddings returned from Gemini API")
            return []
            
        return response.embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to get embedding from Gemini: {e}")
        raise
