"""Tests for ingest.newsletter module."""

from unittest.mock import MagicMock, patch

import pytest

from ingest.newsletter import (
    clean_text,
    decode_base64_url,
    generate_chunk_hash,
    generate_source_id,
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
    with patch("ingest.newsletter.get_gmail_service") as mock_get_service, patch(
        "ingest.newsletter._process_message"
    ) as mock_process:

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock message list
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        }

        # Mock snapshots
        from ingest.newsletter import NewsletterSnapshot

        mock_process.side_effect = [
            (NewsletterSnapshot(
                "id1", "hash1", "sender@a.com", "at", "sub", "content", "at"
            ), "sender@a.com"),
            (NewsletterSnapshot(
                "id2", "hash2", "sender@a.com", "at", "sub", "content", "at"
            ), "sender@a.com"),
            (NewsletterSnapshot(
                "id3", "hash3", "sender@b.com", "at", "sub", "content", "at"
            ), "sender@b.com"),
        ]

        import logging

        from ingest.newsletter import ingest_newsletters

        caplog.set_level(logging.INFO)

        await ingest_newsletters(newer_than_days=1)

        # Check logs
        assert "Found 3 messages. Starting processing..." in caplog.text
        assert (
            "Successfully ingested 3 newsletters: 2 from sender@a.com, 1 from sender@b.com"
            in caplog.text
        )

@pytest.mark.asyncio
async def test_ingest_newsletters_fragility_fix(caplog):
    """Test the refined 'Semantic Fragility' logic doesn't warn about missing senders."""
    with patch("ingest.newsletter.get_gmail_service") as mock_get_service, \
         patch("ingest.newsletter._process_message") as mock_process:

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Scenario: Only 'sender@a.com' is found in Gmail (NOT 'sender@b.com')
        # Even if 'sender@b.com' is in NEWSLETTER_SENDERS, we should NOT get a warning.
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "1"}]
        }
        
        from ingest.newsletter import NewsletterSnapshot
        mock_process.return_value = (
            NewsletterSnapshot("id1", "hash1", "sender@a.com", "at", "sub", "content", "at"),
            "sender@a.com"
        )

        import logging

        from ingest.newsletter import ingest_newsletters
        caplog.set_level(logging.WARNING)

        await ingest_newsletters(newer_than_days=1)

        # There should be NO warning about sender@b.com
        assert "SEMANTIC FRAGILITY ALERT" not in caplog.text

@pytest.mark.asyncio
async def test_ingest_newsletters_fragility_trigger(caplog):
    """Test the refined 'Semantic Fragility' logic DOES warn when a found message fails to parse."""
    with patch("ingest.newsletter.get_gmail_service") as mock_get_service, \
         patch("ingest.newsletter._process_message") as mock_process:

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Scenario: 'sender@a.com' is found, but processing FAILS (snapshot is None)
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "1"}]
        }
        
        # Returns sender name but NO snapshot (e.g., parsing exception internally)
        mock_process.return_value = (None, "sender@a.com")

        import logging

        from ingest.newsletter import ingest_newsletters
        caplog.set_level(logging.WARNING)

        await ingest_newsletters(newer_than_days=1)

        # There SHOULD be a warning about sender@a.com
        assert "SEMANTIC FRAGILITY ALERT: Found message(s) from 'sender@a.com'" in caplog.text
