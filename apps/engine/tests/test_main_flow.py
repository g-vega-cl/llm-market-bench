"""Integration tests for the main execution pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from core.models import DecisionObject
from execution.validation import ValidationResult, ValidationStatus
from main import run_ingest

@pytest.fixture
def mock_dependencies():
    """Setup all mocks required for run_ingest."""
    with patch("main.ingest_newsletters") as mock_ingest, \
         patch("main.get_supabase_client") as mock_get_client, \
         patch("main.upsert_newsletter_snapshot") as mock_upsert, \
         patch("main.analyze_chunks", new_callable=AsyncMock) as mock_analyze, \
         patch("main.process_consensus", new_callable=AsyncMock) as mock_consensus, \
         patch("main.analyze_momentum", new_callable=AsyncMock) as mock_momentum, \
         patch("main.decay_stale_concepts", new_callable=AsyncMock) as mock_decay, \
         patch("main.run_contrarian_analysis", new_callable=AsyncMock) as mock_contrarian, \
         patch("main.validate_decision", new_callable=AsyncMock) as mock_validate, \
         patch("main.Portfolio") as MockPortfolio, \
         patch("main.verify_trading_decision", new_callable=AsyncMock) as mock_verify, \
         patch("main.save_decision") as mock_save:
        
        # Setup defaults
        mock_ingest.return_value = [{"source_id": "test", "content": "test"}]
        mock_consensus.return_value = []
        mock_contrarian.return_value = ([], [])
        mock_verify.return_value = MagicMock(status="APPROVED", verification_reasoning="Verified", confidence_score=100, alternative_ticker=None)
        
        # Mock Portfolio instance
        mock_portfolio_instance = MagicMock()
        MockPortfolio.return_value = mock_portfolio_instance
        
        # Async methods
        mock_portfolio_instance.initialize = AsyncMock()
        mock_portfolio_instance.execute_trade = AsyncMock()
        mock_portfolio_instance.execute_trade.return_value = "trade-uuid-123"
        mock_portfolio_instance.save_metrics = AsyncMock()
        
        # Setup metrics to avoid MagicMock comparison errors in main.py
        mock_portfolio_instance.metrics = MagicMock()
        mock_portfolio_instance.metrics.buying_power = 40000.0
        
        # Sync methods
        mock_portfolio_instance.validate_trade.return_value = MagicMock(passed=True)
        # Also need get_portfolio_summary to be sync? No, used in analyze which is mocked globally.
        # But validate_trade is called in main.py loop.
        
        yield {
            "ingest": mock_ingest,
            "analyze": mock_analyze,
            "validate": mock_validate,
            "portfolio_cls": MockPortfolio,
            "portfolio": mock_portfolio_instance,
            "save": mock_save,
            "verify": mock_verify
        }

@pytest.mark.asyncio
async def test_run_ingest_hold_decision(mock_dependencies):
    """Test that a HOLD decision (no trade) works correctly and passes trade_id=None."""
    md = mock_dependencies
    
    # Setup HOLD decision
    decision = DecisionObject(
        signal="HOLD",
        confidence=50,
        reasoning="Neutral",
        ticker="AAPL",
        source_id="src1",
        model_provider="openai",
        model_name="gpt-4"
    )
    md["analyze"].return_value = ([decision], [], "Mocked context")
    
    # Setup validation to pass
    md["validate"].return_value = ValidationResult(
        status=ValidationStatus.PASSED,
        ticker="AAPL"
    )
    
    await run_ingest()
    
    # Verify save_decision called with trade_id=None
    md["save"].assert_called_once()
    call_args = md["save"].call_args
    # call_args[1] is kwargs
    assert call_args[1].get("trade_id") is None
    assert call_args[1].get("status") == "VALIDATED"

@pytest.mark.asyncio
async def test_run_ingest_buy_decision(mock_dependencies):
    """Test that a BUY decision executes a trade and passes trade_id."""
    md = mock_dependencies
    
    # Setup BUY decision
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Growth",
        ticker="GOOGL",
        source_id="src1",
        price=150.0
    )
    md["analyze"].return_value = ([decision], [], "Mocked context")
    
    # Setup validation
    md["validate"].return_value = ValidationResult(
        status=ValidationStatus.PASSED, 
        market_price=155.0,
        ticker="GOOGL"
    )
    
    await run_ingest()
    
    # Verify portfolio execution
    md["portfolio"].execute_trade.assert_awaited_once()
    
    # Verify save_decision called with trade_id
    md["save"].assert_called_once()
    kwargs = md["save"].call_args[1]
    assert kwargs.get("trade_id") == "trade-uuid-123"
    assert kwargs.get("status") == "EXECUTED"

@pytest.mark.asyncio
async def test_run_ingest_rejected_decision(mock_dependencies):
    """Test a decision rejected by guardrails (should have trade_id=None)."""
    md = mock_dependencies
    
    decision = DecisionObject(
        signal="BUY",
        confidence=90,
        reasoning="Bad idea",
        ticker="PENNY",
        source_id="src1"
    )
    md["analyze"].return_value = ([decision], [], "Mocked context")
    
    # Fail validation
    md["validate"].return_value = ValidationResult(
        status=ValidationStatus.REJECTED_LIQUIDITY,
        reason="Market cap too low",
        ticker="PENNY"
    )
    
    await run_ingest()
    
    # Verify no execution
    md["portfolio"].execute_trade.assert_not_called()
    
    # Verify save_decision
    md["save"].assert_called_once()
    kwargs = md["save"].call_args[1]
    assert kwargs.get("trade_id") is None
    assert kwargs.get("status") == "REJECTED_LIQUIDITY"
