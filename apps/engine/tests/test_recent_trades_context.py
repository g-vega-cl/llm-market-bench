import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from execution.portfolio import Portfolio, Position

@pytest.mark.asyncio
async def test_portfolio_summary_time_ago():
    """Test that get_portfolio_summary correctly formats time ago."""
    portfolio = Portfolio(owner_id="test_model")
    portfolio.id = "test-uuid"
    portfolio.positions = {"AAPL": Position(ticker="AAPL", quantity=10, average_cost_basis=150.0)}
    
    # Mock get_recent_trades to return trades with different timestamps
    now = datetime.now(timezone.utc)
    mock_trades = [
        {
            "ticker": "AAPL",
            "signal": "BUY",
            "quantity": 10,
            "price": 150.0,
            "executed_at": (now - timedelta(minutes=30)).isoformat(),
            "reasoning": "Reason 1"
        },
        {
            "ticker": "AAPL",
            "signal": "SELL",
            "quantity": 5,
            "price": 160.0,
            "executed_at": (now - timedelta(hours=5)).isoformat(),
            "reasoning": "Reason 2"
        },
        {
            "ticker": "AAPL",
            "signal": "BUY",
            "quantity": 100,
            "price": 140.0,
            "executed_at": (now - timedelta(days=1)).isoformat(),
            "reasoning": "Reason 3"
        }
    ]
    
    with patch.object(Portfolio, 'get_recent_trades', return_value=mock_trades):
        with patch.object(Portfolio, 'calculate_reg_t_metrics') as mock_metrics:
            from execution.reg_t_validation import RegTMetrics
            mock_metrics.return_value = RegTMetrics(
                total_equity=10000.0,
                initial_margin_req=0.0,
                maintenance_margin_req=0.0,
                available_funds=0.0,
                excess_liquidity=0.0,
                sma=10000.0,
                realized=0.0,
                buying_power=20000.0
            )
            
            summary = await portfolio.get_portfolio_summary({"AAPL": 155.0})
            
            assert "30m ago" in summary
            assert "5h ago" in summary
            assert "1d ago" in summary
            assert "BUY AAPL: 10 @ $150.00" in summary
            assert "SELL AAPL: 5 @ $160.00" in summary

@pytest.mark.asyncio
async def test_semantic_overlap_detection():
    """Test that validate_semantic_overlap detects similar reasonings."""
    from execution.validation import validate_semantic_overlap

    # Mock find_similar_decision to simulate a hit
    mock_similar = {
        "id": "existing-uuid",
        "reasoning": "AI Demand is surging for chips.",
        "ticker": "NVDA"
    }

    with patch("memory.store.find_similar_decision", return_value=mock_similar):
        overlap = await validate_semantic_overlap("NVDA", "AI structural growth is driving chip demand.", model_name="openai")
        assert overlap is not None
        assert "existing-uuid" in overlap

    # Mock find_similar_decision to simulate a miss
    with patch("memory.store.find_similar_decision", return_value=None):
        overlap = await validate_semantic_overlap("AAPL", "New iPhone launch seems promising.", model_name="openai")
        assert overlap is None

@pytest.mark.asyncio
async def test_semantic_overlap_agent_isolation():
    """Test that semantic overlap only applies within the same agent."""
    from execution.validation import validate_semantic_overlap

    # Simulate a trade from 'claude' on NKE
    mock_claude_trade = {
        "id": "claude-nke-uuid",
        "reasoning": "Nike earnings TOMORROW. Stock at 8-year lows.",
        "ticker": "NKE",
        "model_name": "claude"
    }

    # Claude should see overlap with its own trade
    with patch("memory.store.find_similar_decision", return_value=mock_claude_trade) as mock_find:
        overlap = await validate_semantic_overlap("NKE", "Nike earnings coming, stock looks cheap.", model_name="claude")
        # Verify model_name filter was passed
        mock_find.assert_called_once()
        call_kwargs = mock_find.call_args[1]
        assert call_kwargs.get("model_name") == "claude"
        assert overlap is not None
        assert "claude-nke-uuid" in overlap

    # Haiku should NOT see overlap with Claude's trade (different agent)
    with patch("memory.store.find_similar_decision", return_value=None) as mock_find:
        overlap = await validate_semantic_overlap("NKE", "Nike earnings tomorrow, good entry point.", model_name="haiku")
        # Verify model_name filter was passed
        mock_find.assert_called_once()
        call_kwargs = mock_find.call_args[1]
        assert call_kwargs.get("model_name") == "haiku"
        assert overlap is None
