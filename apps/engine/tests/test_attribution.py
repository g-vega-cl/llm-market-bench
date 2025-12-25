"""Tests for the decision attribution service."""

from unittest.mock import MagicMock
import pytest
from core.models import DecisionObject
from attribution.service import save_decision


@pytest.fixture
def mock_supabase():
    """Fixture for a mocked Supabase client."""
    client = MagicMock()
    # Mock the table().insert().execute() chain
    table_mock = MagicMock()
    insert_mock = MagicMock()
    execute_mock = MagicMock()
    
    client.table.return_value = table_mock
    table_mock.insert.return_value = insert_mock
    insert_mock.execute.return_value = execute_mock
    
    execute_mock.data = [{"id": "test-id"}]
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
        model_name="gpt-4o"
    )
    
    result = save_decision(mock_supabase, decision)
    
    assert result == {"id": "test-id"}
    mock_supabase.table.assert_called_once_with("decisions")
    mock_supabase.table().insert.assert_called_once()
    
    # Check payload
    args, _ = mock_supabase.table().insert.call_args
    payload = args[0]
    assert payload["ticker"] == "AAPL"
    assert payload["model_provider"] == "openai"
    assert payload["source_id"] == "news_123"


def test_save_decision_error(mock_supabase):
    """Test error handling when saving fails."""
    mock_supabase.table().insert().execute.side_effect = Exception("DB Error")
    
    decision = DecisionObject(
        signal="SELL",
        confidence=50,
        reasoning="Market volatility",
        ticker="TSLA",
        source_id="news_456"
    )
    
    with pytest.raises(Exception, match="DB Error"):
        save_decision(mock_supabase, decision)
