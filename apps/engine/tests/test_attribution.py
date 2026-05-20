"""Tests for the decision attribution service."""

from unittest.mock import MagicMock, patch

import pytest

from attribution.service import save_decision
from core.config import GEMINI_MODEL
from core.models import DecisionObject


@pytest.fixture(autouse=True)
def mock_get_embedding():
    """Mock get_embedding to avoid API calls."""
    with patch("attribution.service.get_embedding") as mock:
        mock.return_value = [0.1] * 768
        yield mock


@pytest.fixture
def mock_supabase():
    """Fixture for a mocked Supabase client."""
    client = MagicMock()
    # Mock the table().upsert().execute() chain (changed from insert to upsert)
    table_mock = MagicMock()
    upsert_mock = MagicMock()
    execute_mock = MagicMock()

    client.table.return_value = table_mock
    table_mock.upsert.return_value = upsert_mock
    upsert_mock.execute.return_value = execute_mock

    execute_mock.data = [{"id": "test-id"}]

    # Mock update().eq().execute() chain as well
    update_mock = MagicMock()
    eq_mock = MagicMock()

    client.table.return_value.update.return_value = update_mock
    update_mock.eq.return_value = eq_mock
    eq_mock.execute.return_value = execute_mock

    # This allows `args` to capture correctly.
    client.table.return_value.update = MagicMock(return_value=update_mock)

    return client


def test_save_decision_success(mock_supabase):
    """Test successful decision saving."""
    decision = DecisionObject(
        signal="BUY",
        confidence=85,
        reasoning="Strong earnings growth",
        ticker="AAPL",
        source_id="news_123",
        model_provider="openai",
        model_name="gpt-4o",
    )

    result = save_decision(mock_supabase, decision)

    assert result == {"id": "test-id"}
    mock_supabase.table.assert_called_once_with("decisions")
    mock_supabase.table().upsert.assert_called_once()

    # Check payload
    args, kwargs = mock_supabase.table().upsert.call_args
    payload = args[0]
    assert payload["ticker"] == "AAPL"
    assert payload["model_provider"] == "openai"
    assert payload["source_id"] == "news_123"
    assert "trade_id" in payload  # Check key exists
    assert payload["trade_id"] is None
    # Check on_conflict is set for idempotency
    assert kwargs.get("on_conflict") == "source_id,ticker,signal,model_provider,model_name"


def test_save_decision_with_trade_id(mock_supabase):
    """Test saving decision with a linked trade ID."""
    decision = DecisionObject(
        signal="BUY",
        confidence=90,
        reasoning="Momentum",
        ticker="NVDA",
        source_id="news_789",
        model_provider="gemini",
        model_name=GEMINI_MODEL,
    )

    trade_id = "550e8400-e29b-41d4-a716-446655440000"
    save_decision(mock_supabase, decision, trade_id=trade_id)

    args, kwargs = mock_supabase.table().upsert.call_args
    payload = args[0]

    assert payload["ticker"] == "NVDA"
    assert payload["trade_id"] == trade_id


def test_save_decision_error(mock_supabase):
    """Test error handling when saving fails."""
    mock_supabase.table().upsert().execute.side_effect = Exception("DB Error")

    decision = DecisionObject(
        signal="SELL", confidence=50, reasoning="Market volatility", ticker="TSLA", source_id="news_456"
    )

    with pytest.raises(Exception, match="DB Error"):
        save_decision(mock_supabase, decision)


def test_save_decision_with_decision_id(mock_supabase):
    """Test saving decision with a specific decision_id uses update instead of upsert."""
    decision = DecisionObject(
        signal="BUY",
        confidence=90,
        reasoning="Momentum",
        ticker="NVDA",
        source_id="news_789",
        model_provider="gemini",
        model_name=GEMINI_MODEL,
    )

    decision_id = "11111111-2222-3333-4444-555555555555"
    save_decision(mock_supabase, decision, decision_id=decision_id)

    mock_supabase.table.assert_called_with("decisions")
    mock_supabase.table().update.assert_called_once()
    mock_supabase.table().upsert.assert_not_called()
    mock_supabase.table().update().eq.assert_called_once_with("id", decision_id)


def test_save_decision_raises_on_empty_response(mock_supabase):
    """Test that RuntimeError is raised when upsert returns empty data."""
    mock_supabase.table().upsert().execute.return_value.data = []

    decision = DecisionObject(
        signal="BUY",
        confidence=85,
        reasoning="Empty response test",
        ticker="MSFT",
        source_id="news_empty",
        model_provider="openai",
        model_name="gpt-4o",
    )

    with pytest.raises(RuntimeError, match="no data returned"):
        save_decision(mock_supabase, decision)
