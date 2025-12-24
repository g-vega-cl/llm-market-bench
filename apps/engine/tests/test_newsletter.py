"""Tests for ingest.newsletter module."""

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
