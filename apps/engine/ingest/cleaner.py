"""Module for cleaning newsletter content using LLMs."""

import asyncio
import logging
from core import config
from core.llm import clients, prompts
from core.models import NewsletterCleaningResponse

logger = logging.getLogger("engine")

async def clean_newsletter_content(content: str) -> str:
    """Uses a fast LLM to remove advertisements from the newsletter content.

    Args:
        content: Raw newsletter body text.

    Returns:
        Cleaned newsletter text with advertisements removed.
    """
    if not content or content == config.NO_CONTENT_FOUND:
        return content

    logger.info("Starting advertisement removal pass...")
    
    # We use Gemini Flash for this pass as it's fast and cost-effective for 
    # large batches of text processing like de-advertisement.
    client = clients.get_gemini_client()
    
    try:
        resp_awaitable = client.chat.completions.create(
            model=config.GEMINI_MODEL,
            response_model=NewsletterCleaningResponse,
            messages=[
                {"role": "system", "content": prompts.DE_ADVERTISEMENT_SYSTEM_PROMPT},
                {
                    "role": "user", 
                    "content": prompts.DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE.format(content=content)
                },
            ],
            max_retries=2
        )
        
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            response = await resp_awaitable
        else:
            response = resp_awaitable
        
        if response.ads_removed_count > 0:
            logger.info(f"Successfully cleaned newsletter. Removed {response.ads_removed_count} advertisement blocks.")
        else:
            logger.info("No advertisement blocks detected in the newsletter.")
            
        return response.cleaned_content
        
    except Exception as e:
        logger.error(f"Error during de-advertisement pass: {e}. Falling back to original content.")
        return content
    finally:
        await clients.close_client(client, "gemini")
