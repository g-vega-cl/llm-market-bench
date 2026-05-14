"""Tests for ingest.newsletter module."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from ingest.newsletter import (
    NewsletterSnapshot,
    clean_text,
    decode_base64_url,
    generate_chunk_hash,
    generate_source_id,
    ingest_newsletters,
)


def test_clean_text():
    """Test ASCII enforcement and whitespace normalization."""
    # Test ASCII enforcement
    input_text = "Hello \u2013 World! \u2713"
    # Non-ASCII characters are stripped
    expected = "Hello  World!"
    assert clean_text(input_text) == expected

    # Test whitespace normalization
    input_text = "  Line 1  \n\n  Line 2  \n"
    expected = "Line 1\nLine 2"
    assert clean_text(input_text) == expected


def test_generate_source_id():
    """Test deterministic source ID generation."""
    date = "2023-10-01T12:00:00"
    sender = "Test Sender <test@example.com>"
    subject = "Daily Market Report"

    source_id = generate_source_id(date, sender, subject)

    assert source_id.startswith("news_test_example_com_")
    assert len(source_id) == len("news_test_example_com_") + 8

    # Test determinism
    assert generate_source_id(date, sender, subject) == source_id


def test_generate_chunk_hash():
    """Test SHA-256 content hashing."""
    content = "Sample newsletter content."
    h = generate_chunk_hash(content)

    assert len(h) == 64  # SHA-256 length in hex
    # Test determinism
    assert generate_chunk_hash(content) == h
    # Test change detection
    assert generate_chunk_hash(content + " ") != h


def test_decode_base64_url():
    """Test base64url decoding."""
    # "Hello World" in base64url is "SGVsbG8gV29ybGQ"
    encoded = "SGVsbG8gV29ybGQ"
    assert decode_base64_url(encoded) == "Hello World"

    # "subjects?" -> base64url with '/' replaced by '_'
    encoded = "c3ViamVjdHM_"
    assert decode_base64_url(encoded) == "subjects?"


@pytest.mark.asyncio
async def test_ingest_newsletters_summary(caplog):
    """Test the summary logging in ingest_newsletters."""
    with (
        patch("ingest.newsletter.get_gmail_service") as mock_get_service,
        patch("ingest.newsletter._fetch_raw_message") as mock_process,
        patch("ingest.newsletter.clean_newsletter_content") as mock_clean,
    ):
        mock_clean.side_effect = lambda content: content  # pass-through

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock message list
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        }

        # Mock snapshots

        mock_process.side_effect = [
            (NewsletterSnapshot("id1", "hash1", "sender@a.com", "at", "sub", "content", "at"), "sender@a.com"),
            (NewsletterSnapshot("id2", "hash2", "sender@a.com", "at", "sub", "content", "at"), "sender@a.com"),
            (NewsletterSnapshot("id3", "hash3", "sender@b.com", "at", "sub", "content", "at"), "sender@b.com"),
        ]

        caplog.set_level(logging.INFO)

        await ingest_newsletters(newer_than_days=1)

        # Check logs
        assert "Found 3 messages. Starting processing..." in caplog.text
        assert "Successfully ingested 3 newsletters: 2 from sender@a.com, 1 from sender@b.com" in caplog.text


@pytest.mark.asyncio
async def test_ingest_newsletters_fragility_fix(caplog):
    """Test the refined 'Semantic Fragility' logic doesn't warn about missing senders."""
    with (
        patch("ingest.newsletter.get_gmail_service") as mock_get_service,
        patch("ingest.newsletter._fetch_raw_message") as mock_process,
        patch("ingest.newsletter.clean_newsletter_content") as mock_clean,
    ):
        mock_clean.side_effect = lambda content: content  # pass-through

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Scenario: Only 'sender@a.com' is found in Gmail (NOT 'sender@b.com')
        # Even if 'sender@b.com' is in NEWSLETTER_SENDERS, we should NOT get a warning.
        mock_service.users().messages().list().execute.return_value = {"messages": [{"id": "1"}]}

        mock_process.return_value = (
            NewsletterSnapshot("id1", "hash1", "sender@a.com", "at", "sub", "content", "at"),
            "sender@a.com",
        )

        caplog.set_level(logging.WARNING)

        await ingest_newsletters(newer_than_days=1)

        # There should be NO warning about sender@b.com
        assert "SEMANTIC FRAGILITY ALERT" not in caplog.text


@pytest.mark.asyncio
async def test_ingest_newsletters_fragility_trigger(caplog):
    """Test the refined 'Semantic Fragility' logic DOES warn when a found message fails to parse."""
    with (
        patch("ingest.newsletter.get_gmail_service") as mock_get_service,
        patch("ingest.newsletter._fetch_raw_message") as mock_process,
    ):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Scenario: 'sender@a.com' is found, but processing FAILS (snapshot is None)
        mock_service.users().messages().list().execute.return_value = {"messages": [{"id": "1"}]}

        # Returns sender name but NO snapshot (e.g., parsing exception internally)
        mock_process.return_value = (None, "sender@a.com")

        caplog.set_level(logging.WARNING)

        await ingest_newsletters(newer_than_days=1)

        # There SHOULD be a warning about sender@a.com
        assert "SEMANTIC FRAGILITY ALERT: Found message(s) from 'sender@a.com'" in caplog.text


@pytest.mark.asyncio
async def test_ingest_newsletters_parallel_cleaning(caplog):
    """Test that cleaning calls for multiple newsletters run concurrently, not sequentially.

    When 5 newsletters all need ad removal, the calls should fire in parallel
    (total time ~ max individual delay) rather than sequentially (sum of delays).
    """
    import asyncio
    import time

    call_times = []

    async def slow_clean_with_timing(content):
        call_times.append(time.monotonic())
        await asyncio.sleep(0.1)
        return content

    with (
        patch("ingest.newsletter.get_gmail_service") as mock_get_service,
        patch("ingest.newsletter.clean_newsletter_content", side_effect=slow_clean_with_timing),
        patch("ingest.newsletter._fetch_raw_message") as mock_fetch,
    ):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # 5 messages to clean
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": str(i)} for i in range(1, 6)]
        }

        # _fetch_raw_message returns uncanned snapshots
        mock_fetch.side_effect = [
            (
                NewsletterSnapshot(f"id{i}", f"hash{i}", f"sender{i}@test.com", "date", "sub", f"body {i}", "date"),
                f"sender{i}@test.com",
            )
            for i in range(1, 6)
        ]

        caplog.set_level(logging.INFO)

        start = time.monotonic()
        await ingest_newsletters(newer_than_days=1)
        elapsed = time.monotonic() - start

        # If parallel: ~0.1s (max single delay). If sequential: > 0.5s (5 × 0.1s).
        assert elapsed < 0.3, f"Cleaning took {elapsed:.2f}s — appears to be sequential (expected < 0.3s for parallel)"

        # All 5 cleaning calls should have started within 50ms of each other (concurrent)
        if len(call_times) >= 2:
            spread = max(call_times) - min(call_times)
            assert spread < 0.05, f"Cleaning call start spread was {spread:.3f}s — not concurrent (expected < 0.05s)"

        # Verify all 5 were cleaned
        assert len(call_times) == 5, f"Expected 5 cleaning calls, got {len(call_times)}"
