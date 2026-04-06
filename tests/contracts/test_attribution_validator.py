import pytest
from unittest.mock import MagicMock, patch
from apps.engine.core.audit.attribution_validator import validate_trade_attribution, AttributionAuditResult

@pytest.fixture
def mock_repo():
    with patch("apps.engine.core.audit.attribution_validator.audit_repo") as mock:
        yield mock

def test_validate_trade_attribution_success(mock_repo):
    """Tests the full success path of the attribution validator."""
    # Mock Repository layer instead of DB
    mock_repo.fetch_trade_by_id.return_value = {"id": "trade-123", "ticker": "AAPL", "decision_id": "dec-456"}
    mock_repo.fetch_decision_by_id.return_value = {"id": "dec-456", "source_id": "news-789", "ticker": "AAPL"}
    mock_repo.fetch_news_by_source_id.return_value = {"id": "news-row-123"}
    mock_repo.fetch_reasoning_logs_for_ticker_source.return_value = [{"id": "log-abc", "task_type": "VERIFICATION"}]
    mock_repo.fetch_lessons_for_trade.return_value = [{"id": "lesson-xyz"}]

    result = validate_trade_attribution("trade-123")

    assert result.is_valid is True
    assert "trade_record" in result.lineage_found
    assert "decision_record" in result.lineage_found
    assert "news_source" in result.lineage_found
    assert "reasoning_log" in result.lineage_found
    assert "post_trade_lesson" in result.lineage_found
    assert not result.missing_elements

def test_validate_trade_attribution_missing_decision(mock_repo):
    """Tests failure when decision link is missing."""
    mock_repo.fetch_trade_by_id.return_value = {"id": "trade-123", "ticker": "AAPL", "decision_id": None}
    mock_repo.fetch_lessons_for_trade.return_value = []

    result = validate_trade_attribution("trade-123")
    assert result.is_valid is False
    assert "decision_link" in result.missing_elements
    assert any("orphaned_trade" in r for r in result.failure_reasons)
