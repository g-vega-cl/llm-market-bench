"""Tests for ingest.newsletter module."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

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


@pytest.mark.asyncio
async def test_ingest_newsletters_batch_fetching(caplog):
    """Test that Gmail API message fetching calls for multiple emails run safely and complete.

    When 5 newsletters are listed from Gmail, fetching raw messages should serialize access
    to the thread-unsafe Gmail service object via asyncio.Lock, returning 5 valid snapshots.
    """
    import time

    call_times = []

    def execute_with_timing():
        call_times.append(time.monotonic())
        time.sleep(0.01)
        return {
            "id": "msg-123",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Sender <sender@example.com>"},
                    {"name": "Subject", "value": "Daily Test Report"},
                    {"name": "Date", "value": "Wed, 05 Aug 2026 10:00:00 -0400"},
                ],
                "mimeType": "text/plain",
                "body": {"data": "SGVsbG8gV29ybGQ"},
            },
        }

    with (
        patch("ingest.newsletter.get_gmail_service") as mock_get_service,
        patch("ingest.newsletter.clean_newsletter_content", side_effect=lambda c: c),
    ):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_get_req = MagicMock()
        mock_get_req.execute.side_effect = execute_with_timing
        mock_service.users().messages().get.return_value = mock_get_req

        # 5 messages to fetch
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": f"msg-{i}"} for i in range(1, 6)]
        }

        caplog.set_level(logging.INFO)

        snapshots = await ingest_newsletters(newer_than_days=1)

        # Verify all 5 messages resulted in snapshots safely
        assert len(snapshots) == 5, f"Expected 5 snapshots, got {len(snapshots)}"
        assert len(call_times) == 5


@pytest.mark.asyncio
async def test_fetch_raw_message_retry_success():
    """Test that _fetch_raw_message retries on transient exceptions and succeeds."""
    from ingest.newsletter import _fetch_raw_message

    mock_service = MagicMock()
    mock_get = mock_service.users().messages().get()

    # Fail twice with SSL / socket errors, succeed on 3rd attempt
    mock_get.execute.side_effect = [
        Exception("IncompleteRead(0 bytes read)"),
        Exception("EOF occurred in violation of protocol"),
        {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "Test <test@example.com>"},
                    {"name": "Date", "value": "Thu, 06 Aug 2026 12:00:00 +0000"},
                ],
                "parts": [{"mimeType": "text/plain", "body": {"data": "SGVsbG8="}}],
            }
        },
    ]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        snapshot, sender = await _fetch_raw_message(mock_service, {"id": "msg-123"})

    assert snapshot is not None
    assert snapshot.subject == "Test Subject"
    assert sender == "Test <test@example.com>"
    assert mock_get.execute.call_count == 3


@pytest.mark.asyncio
async def test_ingest_newsletters_thread_safety():
    """Test that concurrent raw message fetching serializes execution to prevent thread collisions on thread-unsafe Gmail service objects."""
    import time

    class NonThreadSafeServiceMock:
        def __init__(self):
            self.in_call = False
            self.collision_detected = False

        def execute(self):
            if self.in_call:
                self.collision_detected = True
                raise RuntimeError("Thread collision detected on thread-unsafe service object!")
            self.in_call = True
            time.sleep(0.01)
            self.in_call = False
            return {
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Test Subject"},
                        {"name": "From", "value": "Test <test@example.com>"},
                        {"name": "Date", "value": "Thu, 06 Aug 2026 12:00:00 +0000"},
                    ],
                    "mimeType": "text/plain",
                    "body": {"data": "SGVsbG8="},
                }
            }

    service_mock = NonThreadSafeServiceMock()
    mock_service = MagicMock()
    mock_service.users().messages().get.return_value = service_mock
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": f"msg-{i}"} for i in range(1, 6)]
    }

    with (
        patch("ingest.newsletter.get_gmail_service", return_value=mock_service),
        patch("ingest.newsletter.clean_newsletter_content", side_effect=lambda c: c),
    ):
        snapshots = await ingest_newsletters(newer_than_days=1)
        assert len(snapshots) == 5
        assert not service_mock.collision_detected


def test_newsletter_senders_config():
    """Test that mandatory financial senders are included in NEWSLETTER_SENDERS."""
    from core.config import NEWSLETTER_SENDERS

    required_senders = [
        "newsletter@investingmail.com",
        "email@stratechery.com",
        "puck@puck.news",
    ]
    for sender in required_senders:
        assert sender in NEWSLETTER_SENDERS, f"Expected {sender} in NEWSLETTER_SENDERS"


def test_parse_json_secret():
    """Test safe parsing of JSON secrets with unescaped control characters and wrapping quotes."""
    from ingest.newsletter import _parse_json_secret

    # Standard valid JSON
    valid_json = '{"client_id": "123", "client_secret": "abc"}'
    assert _parse_json_secret(valid_json, "TEST") == {"client_id": "123", "client_secret": "abc"}

    # Unescaped control character (newline inside string literal)
    json_with_control_chars = '{"token": "line1\nline2", "refresh_token": "ref\ttok"}'
    parsed = _parse_json_secret(json_with_control_chars, "TEST")
    assert parsed == {"token": "line1\nline2", "refresh_token": "ref\ttok"}

    # Single-quote wrapped JSON string
    wrapped_json = '\'{"installed": {"client_id": "cid", "client_secret": "csec"}}\''
    assert _parse_json_secret(wrapped_json, "TEST") == {"installed": {"client_id": "cid", "client_secret": "csec"}}

    # Invalid / empty strings
    assert _parse_json_secret("", "TEST") is None
    assert _parse_json_secret(None, "TEST") is None
    assert _parse_json_secret("not a json {", "TEST") is None


def test_get_gmail_service_resilient_parsing():
    """Test get_gmail_service handles unescaped control characters and flat credentials."""
    from ingest.newsletter import get_gmail_service

    raw_creds = (
        '{\n  "installed": {\n    "client_id": "test-client-id",\n    "client_secret": "test-client-secret"\n  }\n}'
    )
    raw_token = '{"token": "token-with\nnewline", "refresh_token": "refresh-123", "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]}'

    with (
        patch("ingest.newsletter.GMAIL_CREDENTIALS_JSON", raw_creds),
        patch("ingest.newsletter.GMAIL_TOKEN_JSON", raw_token),
        patch("ingest.newsletter.build") as mock_build,
    ):
        mock_build.return_value = MagicMock()
        service = get_gmail_service()
        assert service is not None
        mock_build.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_newsletters_query_retry_on_502():
    """Test that ingest_newsletters retries when service.users().messages().list() returns 502 Bad Gateway."""
    from googleapiclient.errors import HttpError

    mock_resp = MagicMock()
    mock_resp.status = 502
    mock_resp.reason = "Bad Gateway"
    http_err_502 = HttpError(resp=mock_resp, content=b"Bad Gateway")

    mock_service = MagicMock()
    mock_list = mock_service.users().messages().list()
    # First attempt raises 502, second attempt succeeds
    mock_list.execute.side_effect = [
        http_err_502,
        {"messages": [{"id": "msg-123"}]},
    ]

    with (
        patch("ingest.newsletter.get_gmail_service", return_value=mock_service),
        patch("ingest.newsletter._fetch_raw_message") as mock_fetch,
        patch("ingest.newsletter.clean_newsletter_content", side_effect=lambda c: c),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_fetch.return_value = (
            NewsletterSnapshot(
                source_id="id1",
                chunk_hash="hash1",
                sender="crew@morningbrew.com",
                date="2026-08-26T12:00:00",
                subject="Daily Brew",
                content="Sample content",
                ingested_at="2026-08-26T12:00:00",
            ),
            "crew@morningbrew.com",
        )

        snapshots = await ingest_newsletters(newer_than_days=1)
        assert len(snapshots) == 1
        assert snapshots[0]["source_id"] == "id1"
        assert mock_list.execute.call_count == 2
        mock_sleep.assert_called_once()
