"""Module for cleaning newsletter content using LLMs."""

import asyncio
import logging

from core import config
from core.llm import clients
from core.llm.prompt_factory import PromptFactory
from core.models import NewsletterCleaningResponse

logger = logging.getLogger("engine")


class CleanedNewsletterText(str):
    """String subclass representing cleaned newsletter text with audit metadata."""

    is_pure_ad: bool
    ads_removed_count: int
    ads_summary: list[str]

    def __new__(
        cls,
        content: str,
        is_pure_ad: bool = False,
        ads_removed_count: int = 0,
        ads_summary: list[str] | None = None,
    ):
        obj = super().__new__(cls, content)
        obj.is_pure_ad = is_pure_ad
        obj.ads_removed_count = ads_removed_count
        obj.ads_summary = ads_summary if ads_summary is not None else []
        return obj


async def clean_newsletter_content(content: str) -> str:
    """Uses a fast LLM to remove advertisements and fluff from newsletter content.

    Args:
        content: Raw newsletter body text.

    Returns:
        Cleaned newsletter text (CleanedNewsletterText) with advertisements removed.
    """
    if not content or content == config.NO_CONTENT_FOUND:
        return content

    logger.debug("Starting advertisement removal pass...")

    # We use Gemini Flash for this pass as it is fast and cost-effective for
    # large batches of text processing like de-advertisement.
    client = clients.get_gemini_client()

    try:
        messages = PromptFactory.build_de_advertisement_messages(provider="gemini", content=content)

        resp_awaitable = client.chat.completions.create(
            model=config.GEMINI_MODEL, response_model=NewsletterCleaningResponse, messages=messages, max_retries=2
        )

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            response = await resp_awaitable
        else:
            response = resp_awaitable

        # Handle pure advertisement emails
        if response.is_pure_ad:
            logger.info(
                "Identified newsletter as pure advertisement (%d blocks removed).",
                response.ads_removed_count,
            )
            return CleanedNewsletterText(
                "",
                is_pure_ad=True,
                ads_removed_count=response.ads_removed_count,
                ads_summary=response.ads_summary,
            )

        # Guard against catastrophic over-stripping
        if len(content.strip()) >= 200 and len(response.cleaned_content.strip()) < 50 and not response.is_pure_ad:
            logger.warning(
                "Catastrophic over-stripping detected (%d chars down to %d chars without is_pure_ad flag). Falling back to original content.",
                len(content),
                len(response.cleaned_content),
            )
            return CleanedNewsletterText(content, is_pure_ad=False, ads_removed_count=0, ads_summary=[])

        if response.ads_removed_count > 0:
            logger.info("Successfully cleaned newsletter. Removed %d advertisement blocks.", response.ads_removed_count)
        else:
            logger.info("No advertisement blocks detected in the newsletter.")

        return CleanedNewsletterText(
            response.cleaned_content,
            is_pure_ad=False,
            ads_removed_count=response.ads_removed_count,
            ads_summary=response.ads_summary,
        )

    except Exception as e:
        logger.exception("Error during de-advertisement pass: %s. Falling back to original content.", e)
        return CleanedNewsletterText(content, is_pure_ad=False, ads_removed_count=0, ads_summary=[])
    finally:
        await clients.close_client(client, "gemini")
