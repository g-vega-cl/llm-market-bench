import pytest
from unittest.mock import MagicMock, patch
from apps.engine.trading.rejections import persist_rejection
from apps.engine.core.models import DecisionObject

def test_persist_rejection_calls_save_decision():
    """Ensures persist_rejection correctly formats and saves the rejection."""
    mock_sb = MagicMock()
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Test",
        ticker="AAPL",
        source_id="news-1",
        model_provider="test",
        model_name="test"
    )

    with patch("apps.engine.trading.rejections.save_decision") as mock_save:
        persist_rejection(mock_sb, decision, "Insufficient funds", status="REJECTED_MARGIN")

        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        assert kwargs["status"] == "REJECTED_MARGIN"
        assert kwargs["metadata"]["rejection_reason"] == "Insufficient funds"
        assert kwargs["decision"].ticker == "AAPL"
