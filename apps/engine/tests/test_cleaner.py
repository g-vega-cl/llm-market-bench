"""Tests for the newsletter de-advertisement cleaner module."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from core import config
from core.models import NewsletterCleaningResponse
from ingest.cleaner import CleanedNewsletterText, clean_newsletter_content


def test_cleaned_newsletter_text_string_subclass():
    """Verify CleanedNewsletterText behaves as a string while providing audit metadata."""
    cleaned = CleanedNewsletterText(
        "Cleaned text here",
        is_pure_ad=False,
        ads_removed_count=2,
        ads_summary=["Ad block 1", "Ad block 2"],
    )
    assert isinstance(cleaned, str)
    assert cleaned == "Cleaned text here"
    assert cleaned.strip() == "Cleaned text here"
    assert cleaned.is_pure_ad is False
    assert cleaned.ads_removed_count == 2
    assert cleaned.ads_summary == ["Ad block 1", "Ad block 2"]


def test_newsletter_cleaning_response_schema():
    """Verify NewsletterCleaningResponse includes ads_summary and is_pure_ad fields."""
    resp = NewsletterCleaningResponse(
        cleaned_content="Market surged today.",
        ads_removed_count=1,
        ads_summary=["Brokerage referral link"],
        is_pure_ad=False,
    )
    assert resp.cleaned_content == "Market surged today."
    assert resp.ads_removed_count == 1
    assert resp.ads_summary == ["Brokerage referral link"]
    assert resp.is_pure_ad is False


@pytest.mark.asyncio
async def test_clean_newsletter_empty_and_no_content():
    """Verify empty content or NO_CONTENT_FOUND is returned unchanged without LLM calls."""
    with patch("core.llm.clients.get_gemini_client") as mock_client:
        res_empty = await clean_newsletter_content("")
        assert res_empty == ""

        res_none = await clean_newsletter_content(None)
        assert res_none is None

        res_placeholder = await clean_newsletter_content("NO_CONTENT_FOUND")
        assert res_placeholder == "NO_CONTENT_FOUND"

        res_config_placeholder = await clean_newsletter_content(config.NO_CONTENT_FOUND)
        assert res_config_placeholder == config.NO_CONTENT_FOUND

        mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_clean_newsletter_happy_path_with_ad_removal():
    """Verify normal ad stripping returns CleanedNewsletterText with populated audit metadata."""
    mock_resp = NewsletterCleaningResponse(
        cleaned_content="US GDP expanded by 2.8% in Q3. Apple reports earnings.",
        ads_removed_count=2,
        ads_summary=["RAD Intel sponsored pitch", "Coffee mug referral program"],
        is_pure_ad=False,
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with (
        patch("core.llm.clients.get_gemini_client", return_value=mock_client),
        patch("core.llm.clients.close_client", new_callable=AsyncMock) as mock_close,
    ):
        result = await clean_newsletter_content(
            "US GDP expanded by 2.8% in Q3. Sponsor: RAD Intel buy now. Apple reports earnings. Refer friends for a mug."
        )

        assert isinstance(result, CleanedNewsletterText)
        assert result == "US GDP expanded by 2.8% in Q3. Apple reports earnings."
        assert result.ads_removed_count == 2
        assert result.ads_summary == ["RAD Intel sponsored pitch", "Coffee mug referral program"]
        assert result.is_pure_ad is False
        mock_close.assert_awaited_once_with(mock_client, "gemini")


@pytest.mark.asyncio
async def test_clean_newsletter_pure_ad_classification():
    """Verify pure marketing emails return is_pure_ad=True and empty cleaned text."""
    mock_resp = NewsletterCleaningResponse(
        cleaned_content="",
        ads_removed_count=1,
        ads_summary=["100% deposit bonus promotional pitch"],
        is_pure_ad=True,
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with (
        patch("core.llm.clients.get_gemini_client", return_value=mock_client),
        patch("core.llm.clients.close_client", new_callable=AsyncMock),
    ):
        result = await clean_newsletter_content("Get up to $500 bonus when you deposit today! Claim now.")

        assert isinstance(result, CleanedNewsletterText)
        assert result.is_pure_ad is True
        assert result == ""
        assert result.ads_summary == ["100% deposit bonus promotional pitch"]


@pytest.mark.asyncio
async def test_clean_newsletter_catastrophic_overstripping_fallback(caplog):
    """Verify that if LLM strips a long newsletter down to < 50 chars without is_pure_ad, it falls back."""
    long_content = (
        "Headline: Federal Reserve signals policy pause.\n"
        "Economic indicators show persistent labor strength while manufacturing contracts slightly.\n"
        "Treasury yields held steady with the 10-year benchmark at 4.25%.\n"
        "Corporate credit spreads remain near historical tights as investment grade issuance increases."
    )
    assert len(long_content) >= 200

    mock_resp = NewsletterCleaningResponse(
        cleaned_content="Short text.",
        ads_removed_count=3,
        ads_summary=["Stripped too much"],
        is_pure_ad=False,
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with (
        caplog.at_level(logging.WARNING, logger="engine"),
        patch("core.llm.clients.get_gemini_client", return_value=mock_client),
        patch("core.llm.clients.close_client", new_callable=AsyncMock),
    ):
        result = await clean_newsletter_content(long_content)

        # Should fall back to the original long content to prevent data loss
        assert result == long_content
        assert any("over-stripping detected" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_clean_newsletter_exception_observability(caplog):
    """Verify exception handler logs with traceback via logger.exception and returns original text."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("Gemini API connection error"))

    with (
        caplog.at_level(logging.ERROR, logger="engine"),
        patch("core.llm.clients.get_gemini_client", return_value=mock_client),
        patch("core.llm.clients.close_client", new_callable=AsyncMock),
    ):
        result = await clean_newsletter_content("Market news to clean")

        assert result == "Market news to clean"
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1
        # logger.exception records have exc_info attached
        assert error_records[0].exc_info is not None
