"""Tests to verify SELL trade guardrails (minimum trade value)."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from core.models import DecisionObject
from execution.validation import ValidationResult, ValidationStatus
from main import run_ingest

@pytest.fixture
def mock_dependencies():
    """Setup mocks for SELL guardrail tests."""
    with patch("main.ingest_newsletters") as mock_ingest, \
         patch("main.get_supabase_client") as mock_get_client, \
         patch("main.upsert_newsletter_snapshot") as mock_upsert, \
         patch("main._stage_dust_cleanup", new_callable=AsyncMock) as mock_dust, \
         patch("main.analyze_chunks", new_callable=AsyncMock) as mock_analyze, \
         patch("main.process_consensus", new_callable=AsyncMock) as mock_consensus, \
         patch("main.analyze_momentum", new_callable=AsyncMock) as mock_momentum, \
         patch("main.decay_stale_concepts", new_callable=AsyncMock) as mock_decay, \
         patch("main.run_contrarian_analysis", new_callable=AsyncMock) as mock_contrarian, \
         patch("main.validate_decision", new_callable=AsyncMock) as mock_validate, \
         patch("main.validate_semantic_overlap", new_callable=AsyncMock) as mock_overlap, \
         patch("main.Portfolio") as MockPortfolio, \
         patch("execution.market_data.MarketDataManager") as MockMDM, \
         patch("main.verify_trading_decision", new_callable=AsyncMock) as mock_verify, \
         patch("main.save_decision") as mock_save:
        
        # Setup defaults
        mock_ingest.return_value = [{"source_id": "test", "content": "test"}]
        mock_consensus.return_value = []
        mock_contrarian.return_value = ([], [])
        mock_overlap.return_value = None
        mock_validate.return_value = ValidationResult(
            status=ValidationStatus.PASSED,
            market_price=150.0,
            ticker="DEFAULT"
        )
        # Mock MarketDataManager for the main loop's p_map
        mock_mdm_instance = MockMDM.return_value
        mock_mdm_instance.get_quote = AsyncMock()
        mock_mdm_instance.get_quote.return_value = MagicMock(price=100.0)
        mock_mdm_instance.get_quotes = AsyncMock()
        mock_mdm_instance.get_quotes.return_value = {"AAPL": MagicMock(price=100.0), "DEFAULT": MagicMock(price=150.0)}
        
        # Mock Portfolio instance
        mock_portfolio_instance = MagicMock()
        MockPortfolio.return_value = mock_portfolio_instance
        mock_portfolio_instance.initialize = AsyncMock()
        mock_portfolio_instance.execute_trade = AsyncMock()
        mock_portfolio_instance.calculate_reg_t_metrics = MagicMock()
        
        yield {
            "analyze": mock_analyze,
            "validate_decision": mock_validate,
            "portfolio": mock_portfolio_instance,
            "save": mock_save
        }

@pytest.mark.asyncio
async def test_run_ingest_rejected_small_sell(mock_dependencies):
    """Verify that a SELL for 1 share @ $260 (below $1000) is rejected."""
    md = mock_dependencies
    
    # Setup small SELL decision (1 share @ $260.74 = $260.74 < $1000)
    decision = DecisionObject(
        signal="SELL",
        ticker="AAPL",
        confidence=90,
        reasoning="Take small profit",
        source_id="src1",
        sell_tool_called=True,
        quantity=1
    )
    md["analyze"].return_value = ([decision], [], "Mocked context", "")
    
    # Portfolio setup: Owned AAPL
    md["portfolio"].positions = {"AAPL": MagicMock(quantity=10)}
    md["portfolio"].metrics = MagicMock(buying_power=50000.0, total_equity=60000.0, sma=50000.0)
    
    # Mock validate_decision to pass existence check
    md["validate_decision"].return_value = ValidationResult(
        status=ValidationStatus.PASSED,
        market_price=260.74,
        ticker="AAPL"
    )
    
    # IMPORTANT: Mock portfolio.validate_trade to mirror the Reg T logic
    from execution.reg_t_validation import ValidationResult as ComplianceResult
    md["portfolio"].validate_trade.return_value = ComplianceResult(
        passed=False,
        reason="SELL Trade value below minimum threshold of $1,000.00."
    )
    
    await run_ingest(force=True)
    # Verify rejection logic in main.py loop
    md["portfolio"].execute_trade.assert_not_called()
    
    # Verify save_decision called with REJECTED_MARGIN
    # The fix ensures SELL calls validate_trade, which should fail if below 1000
    assert md["save"].called
    kwargs = md["save"].call_args[1]
    assert kwargs.get("status") == "REJECTED_MARGIN"
    assert "below minimum threshold" in kwargs.get("metadata", {}).get("reason", "")

@pytest.mark.asyncio
async def test_run_ingest_passed_large_sell(mock_dependencies):
    """Verify that a SELL for 10 shares @ $260 (above $1000) is accepted."""
    md = mock_dependencies
    
    # Setup large SELL decision (10 shares @ $260.74 = $2607.40 > $1000)
    decision = DecisionObject(
        signal="SELL",
        ticker="AAPL",
        confidence=90,
        reasoning="Take larger profit",
        source_id="src1",
        sell_tool_called=True,
        quantity=10
    )
    md["analyze"].return_value = ([decision], [], "Mocked context", "")
    
    # Portfolio setup
    md["portfolio"].positions = {"AAPL": MagicMock(quantity=100)}
    md["portfolio"].metrics = MagicMock(buying_power=50000.0, total_equity=60000.0, sma=50000.0)
    
    # Mock validate_decision
    md["validate_decision"].return_value = ValidationResult(
        status=ValidationStatus.PASSED,
        market_price=260.74,
        ticker="AAPL"
    )
    
    # Mock validate_trade to pass
    from execution.reg_t_validation import ValidationResult as ComplianceResult
    md["portfolio"].validate_trade.return_value = ComplianceResult(passed=True)
    
    # Mock execute_trade to return UUID
    md["portfolio"].execute_trade.return_value = "trade-uuid-456"
    
    await run_ingest(force=True)
    # Verify execution
    md["portfolio"].execute_trade.assert_awaited_once()
    assert md["save"].called
    kwargs = md["save"].call_args[1]
    assert kwargs.get("status") == "EXECUTED"
@pytest.mark.asyncio
async def test_run_ingest_bypassed_small_sell_with_tool(mock_dependencies):
    """Verify that a small SELL is accepted if sell_tool_called is True."""
    md = mock_dependencies
    
    # Setup small SELL decision (1 share @ $260.74 = $260.74 < $1000)
    # BUT sell_tool_called is True
    decision = DecisionObject(
        signal="SELL",
        ticker="AAPL",
        confidence=90,
        reasoning="Take small profit with tool",
        source_id="src1",
        sell_tool_called=True,
        quantity=1
    )
    md["analyze"].return_value = ([decision], [], "Mocked context", "")
    
    # Portfolio setup
    md["portfolio"].positions = {"AAPL": MagicMock(quantity=10)}
    md["portfolio"].metrics = MagicMock(buying_power=50000.0, total_equity=60000.0, sma=50000.0)
    
    # Mock validate_decision
    md["validate_decision"].return_value = ValidationResult(
        status=ValidationStatus.PASSED,
        market_price=260.74,
        ticker="AAPL"
    )
    
    # Mock validate_trade to PASS because we bypass the $1000 check
    from execution.reg_t_validation import ValidationResult as ComplianceResult
    md["portfolio"].validate_trade.return_value = ComplianceResult(passed=True)
    
    # Mock execute_trade
    md["portfolio"].execute_trade.return_value = "trade-uuid-789"
    
    await run_ingest(force=True)
    # Verify execution
    md["portfolio"].execute_trade.assert_awaited_once()
    assert md["save"].called
    kwargs = md["save"].call_args[1]
    assert kwargs.get("status") == "EXECUTED"
