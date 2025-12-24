"""Tests for core.config module."""

import pytest
from unittest.mock import patch

import core.config


def test_constants():
    """Verify that constants are defined correctly."""
    assert isinstance(core.config.NEWSLETTER_SENDERS, list)
    assert len(core.config.NEWSLETTER_SENDERS) > 0
    assert core.config.GMAIL_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert core.config.COMMAND_INGEST == "ingest"
    assert core.config.NO_CONTENT_FOUND == "No content found"


def test_model_defaults():
    """Verify default model names are set."""
    assert core.config.OPENAI_MODEL is not None
    assert core.config.ANTHROPIC_MODEL is not None
    assert core.config.GEMINI_MODEL is not None
    assert core.config.DEEPSEEK_MODEL is not None


def test_env_attributes_exist():
    """Verify environment variable attributes exist on the module."""
    assert hasattr(core.config, "SUPABASE_URL")
    assert hasattr(core.config, "SUPABASE_SERVICE_ROLE_KEY")
    assert hasattr(core.config, "OPENAI_API_KEY")
    assert hasattr(core.config, "ANTHROPIC_API_KEY")
    assert hasattr(core.config, "GEMINI_API_KEY")
    assert hasattr(core.config, "DEEPSEEK_API_KEY")
