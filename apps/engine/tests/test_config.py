"""Tests for core.config module."""

import core.config


def test_constants():
    """Verify that constants are defined correctly."""
    assert isinstance(core.config.NEWSLETTER_SENDERS, list)
    assert len(core.config.NEWSLETTER_SENDERS) > 0
    required_senders = [
        "thebearcave@substack.com",
        "ideabrunch@substack.com",
        "william@puck.new",
        "hello@snacks.robinhood.com",
        "netinterest@substack.com",
        "calculatedrisk@substack.com",
        "closer@axios.com",
        "macro@axios.com",
    ]
    for sender in required_senders:
        assert sender in core.config.NEWSLETTER_SENDERS
    assert core.config.GMAIL_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert core.config.COMMAND_INGEST == "ingest"
    assert core.config.COMMAND_WEEKEND_INGEST == "weekend-ingest"
    assert core.config.NO_CONTENT_FOUND == "No content found"


def test_model_defaults():
    """Verify default model names are set."""
    assert core.config.OPENAI_MODEL == "gpt-5.6-luna"
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


def test_minimax_model_is_m3():
    """Verify that MINIMAX_MODEL is updated to MiniMax-M3."""
    assert core.config.MINIMAX_MODEL == "MiniMax-M3"
