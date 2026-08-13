"""Test log reduction and log level configuration."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from core.models import NewsletterCleaningResponse
from ingest.cleaner import clean_newsletter_content


def test_httpx_logger_is_warning_level():
    """Verify httpx and httpcore loggers are set to WARNING level to suppress HTTP request spam."""
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


@pytest.mark.asyncio
async def test_ad_cleaner_logs_at_debug_not_info(caplog):
    """Verify advertisement cleaner logs start message at DEBUG level, not INFO."""
    caplog.set_level(logging.INFO, logger="engine")

    mock_resp = NewsletterCleaningResponse(
        cleaned_content="Clean text",
        ads_removed_count=1,
        ads_summary=["ad1"],
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with (
        patch("core.llm.clients.get_gemini_client", return_value=mock_client),
        patch("core.llm.clients.close_client", new_callable=AsyncMock),
    ):
        result = await clean_newsletter_content("Some content with ad")
        assert result == "Clean text"

    # Message should NOT appear at INFO level in caplog
    assert "Starting advertisement removal pass..." not in [
        record.message for record in caplog.records if record.levelname == "INFO"
    ]
