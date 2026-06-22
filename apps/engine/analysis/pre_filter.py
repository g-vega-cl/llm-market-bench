"""Task for pre-filtering and summarizing newsletters using DeepSeek Flash."""

import logging

from pydantic import BaseModel, Field

from core.config import DEEPSEEK_FLASH_MODEL
from core.llm import clients

logger = logging.getLogger("engine")


class NewsletterTriageItem(BaseModel):
    """Structured triage details for a single newsletter."""

    source_id: str = Field(description="The source_id of the newsletter snapshot")
    summary: str = Field(description="A concise 1-2 sentence summary of key tickers, companies, topics, and catalysts.")


class NewsletterTriageResponse(BaseModel):
    """Aggregated triage response for a batch of newsletters."""

    summaries: list[NewsletterTriageItem]


async def summarize_newsletters(chunks: list[dict]) -> dict[str, str]:
    """Generates concise 1-2 sentence summaries for a batch of newsletters.

    Args:
        chunks: List of newsletter chunk dictionaries containing 'source_id',
            'content', 'sender', 'subject'.

    Returns:
        A dictionary mapping source_id to its concise summary string.
        Returns an empty dict if the LLM call fails.
    """
    if not chunks:
        return {}

    logger.info(f"Pre-filtering {len(chunks)} newsletters using {DEEPSEEK_FLASH_MODEL}...")

    # Format the input text for the pre-filter model
    newsletter_batch_str = ""
    for chunk in chunks:
        newsletter_batch_str += (
            f"\n---\n"
            f"Source ID: {chunk['source_id']}\n"
            f"Sender: {chunk.get('sender', 'Unknown')}\n"
            f"Subject: {chunk.get('subject', 'No Subject')}\n"
            f"Content: {chunk.get('content', '')[:3000]}\n"  # Truncate content slightly to fit context limits safely
            f"---\n"
        )

    system_prompt = (
        "You are an expert financial research assistant. Your task is to review a batch of raw ingested financial newsletters "
        "and produce a concise 1-2 sentence summary of the key tickers, companies, macroeconomic events, and potential catalysts "
        "mentioned in each newsletter.\n\n"
        "Be extremely objective and factual. Strip out all marketing fluff, advertisements, affiliate links, and generic commentary. "
        "Focus only on material market-moving signals. Provide the exact source_id associated with each summary."
    )

    user_prompt = f"Here is the batch of newsletters to summarize:\n{newsletter_batch_str}"

    client = clients.get_deepseek_client()

    try:
        resp = await client.chat.completions.create(
            model=DEEPSEEK_FLASH_MODEL,
            response_model=NewsletterTriageResponse,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_retries=2,
        )

        summary_map = {}
        for item in resp.summaries:
            summary_map[item.source_id] = item.summary

        logger.info(f"Successfully generated summaries for {len(summary_map)} newsletters.")
        return summary_map

    except Exception:
        logger.exception("Pre-filtering newsletters failed. Falling back to empty summary map.")
        return {}
    finally:
        await clients.close_client(client, "deepseek")
