import pytest
from unittest.mock import MagicMock, patch
from apps.engine.core.audit.attribution_validator import validate_trade_attribution, AttributionAuditResult

@pytest.fixture
def mock_supabase():
    with patch("apps.engine.core.audit.attribution_validator.get_supabase_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client

def test_validate_trade_attribution_success(mock_supabase):
    """Tests the full success path of the attribution validator."""
    # 1. Mock Trade
    # For simplicity in testing the logic, we mock the final .execute() call for each step
    # We need to be careful with the order of calls.

    mock_execute = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute = mock_execute
    mock_supabase.table.return_value.select.return_value.filter.return_value.filter.return_value.execute = mock_execute
    mock_supabase.table.return_value.select.return_value.eq.return_value.filter.return_value.execute = mock_execute

    mock_execute.side_effect = [
        # Trade res
        MagicMock(data=[{"id": "trade-123", "ticker": "AAPL", "decision_id": "dec-456"}]),
        # Decision res
        MagicMock(data=[{"id": "dec-456", "source_id": "news-789", "ticker": "AAPL"}]),
        # News source res
        MagicMock(data=[{"id": "news-row-123"}]),
        # Reasoning logs res
        MagicMock(data=[{"id": "log-abc", "task_type": "VERIFICATION"}]),
        # Lesson res
        MagicMock(data=[{"id": "lesson-xyz"}])
    ]

    result = validate_trade_attribution("trade-123")

    assert result.is_valid is True
    assert "trade_record" in result.lineage_found
    assert "decision_record" in result.lineage_found
    assert "news_source" in result.lineage_found
    assert "reasoning_log" in result.lineage_found
    assert "post_trade_lesson" in result.lineage_found
    assert not result.missing_elements

def test_validate_trade_attribution_missing_decision(mock_supabase):
    """Tests failure when decision link is missing."""
    mock_execute = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute = mock_execute
    mock_supabase.table.return_value.select.return_value.eq.return_value.filter.return_value.execute = mock_execute

    mock_execute.side_effect = [
        # Trade res
        MagicMock(data=[{"id": "trade-123", "ticker": "AAPL", "decision_id": None}]),
        # Lesson res
        MagicMock(data=[])
    ]

    result = validate_trade_attribution("trade-123")
    assert result.is_valid is False
    assert "decision_link" in result.missing_elements
    assert any("orphaned_trade" in r for r in result.failure_reasons)
