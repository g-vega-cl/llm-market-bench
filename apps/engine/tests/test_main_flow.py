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
         patch("main._stage_dust_cleanup", new_callable=AsyncMock) as mock_dust, \
         patch("main.analyze_chunks", new_callable=AsyncMock) as mock_analyze, \
         patch("main.process_consensus", new_callable=AsyncMock) as mock_consensus, \
         patch("main.analyze_momentum", new_callable=AsyncMock) as mock_momentum, \
         patch("main.decay_stale_concepts", new_callable=AsyncMock) as mock_decay, \
         patch("main.analyze_market_feeling", new_callable=AsyncMock) as mock_market_feeling, \
         patch("main.run_contrarian_analysis", new_callable=AsyncMock) as mock_contrarian, \
         patch("main.validate_decision", new_callable=AsyncMock) as mock_validate, \
         patch("main.validate_semantic_overlap", new_callable=AsyncMock) as mock_overlap, \
         patch("main.Portfolio") as MockPortfolio, \
         patch("execution.market_data.MarketDataManager") as MockMDM, \
         patch("core.utils.MarketDataManager") as MockMDMUtils, \
         patch("main.verify_trading_decision", new_callable=AsyncMock) as mock_verify, \
         patch("main.save_decision") as mock_save:
        
        # Setup defaults
        mock_ingest.return_value = [{"source_id": "test", "content": "test"}]
        mock_consensus.return_value = []
        mock_consensus.return_value = []
        mock_contrarian.return_value = ([], [])
        mock_market_feeling.return_value = None
        mock_overlap.return_value = None
        mock_validate.return_value = ValidationResult(
            status=ValidationStatus.PASSED,
            market_price=150.0,
            ticker="DEFAULT"
        )
        mock_verify.return_value = MagicMock(status="APPROVED", verification_reasoning="Verified", confidence_score=100, alternative_ticker=None)
        
        # Mock MarketDataManager
        mock_mdm_instance = MockMDM.return_value
        mock_mdm_instance.get_quote = AsyncMock()
        mock_mdm_instance.get_quote.side_effect = lambda t, **kwargs: MagicMock(price=150.0) if t == "GOOGL" else MagicMock(price=100.0)
        mock_mdm_instance.get_quotes = AsyncMock()
        mock_mdm_instance.get_quotes.side_effect = lambda tickers, **kwargs: {t: (MagicMock(price=150.0) if t == "GOOGL" else MagicMock(price=100.0)) for t in tickers}
        mock_mdm_instance.is_market_open = AsyncMock(return_value=True)
        
        # Mock MarketDataManager for core.utils (used by is_market_open_with_logging)
        mock_mdm_utils_instance = MagicMock()
        MockMDMUtils.return_value = mock_mdm_utils_instance
        mock_mdm_utils_instance.is_market_open = AsyncMock(return_value=True)
        
        # Mock Portfolio instance
        mock_portfolio_instance = MagicMock()
        MockPortfolio.return_value = mock_portfolio_instance
        
        # Async methods
        mock_portfolio_instance.initialize = AsyncMock()
        mock_portfolio_instance.execute_trade = AsyncMock()
        mock_portfolio_instance.execute_trade.return_value = "trade-uuid-123"
        mock_portfolio_instance.save_metrics = AsyncMock()
        mock_portfolio_instance.get_portfolio_summary = AsyncMock(return_value="Mocked Port Summary")
        
        # Setup metrics to avoid MagicMock comparison errors in main.py
        from execution.reg_t_validation import RegTMetrics
        mock_portfolio_instance.metrics = RegTMetrics(
            total_equity=50000.0,
            initial_margin_req=0.0,
            maintenance_margin_req=0.0,
            available_funds=0.0,
            excess_liquidity=0.0,
            sma=50000.0,
            realized=50000.0,
            buying_power=40000.0
        )
        
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
            "verify": mock_verify,
            "dust_cleanup": mock_dust,
            "market_feeling": mock_market_feeling,
            "db": mock_get_client
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
    md["analyze"].return_value = ([decision], [], "Mocked context", "")
    
    # Setup validation to pass
    md["validate"].return_value = ValidationResult(
        status=ValidationStatus.PASSED,
        ticker="AAPL"
    )
    
    await run_ingest(force=True)
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
    md["analyze"].return_value = ([decision], [], "Mocked context", "")

    # Setup validation
    md["validate"].return_value = ValidationResult(
        status=ValidationStatus.PASSED,
        market_price=155.0,
        ticker="GOOGL"
    )

    await run_ingest(force=True)
    # Verify portfolio execution
    md["portfolio"].execute_trade.assert_awaited_once()

    # Verify save_decision called twice: first VALIDATED, then EXECUTED
    assert md["save"].call_count == 2
    
    # First call: VALIDATED status (to get decision_id)
    first_call_kwargs = md["save"].call_args_list[0][1]
    assert first_call_kwargs.get("status") == "VALIDATED"
    
    # Second call: EXECUTED status with trade_id
    second_call_kwargs = md["save"].call_args_list[1][1]
    assert second_call_kwargs.get("trade_id") == "trade-uuid-123"
    assert second_call_kwargs.get("status") == "EXECUTED"

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
    md["analyze"].return_value = ([decision], [], "Mocked context", "")
    
    # Fail validation
    md["validate"].return_value = ValidationResult(
        status=ValidationStatus.REJECTED_LIQUIDITY,
        reason="Market cap too low",
        ticker="PENNY"
    )
    
    await run_ingest(force=True)
    # Verify no execution
    md["portfolio"].execute_trade.assert_not_called()
    
    # Verify save_decision
    md["save"].assert_called_once()
    kwargs = md["save"].call_args[1]
    assert kwargs.get("trade_id") is None
    assert kwargs.get("status") == "REJECTED_LIQUIDITY"

@pytest.mark.asyncio
async def test_run_ingest_sell_tool_enforcement(mock_dependencies):
    """Test that a SELL decision without tool usage is rejected with REJECTED_TOOL_USAGE."""
    md = mock_dependencies
    
    # 1. Decision without tool call
    decision = DecisionObject(
        signal="SELL",
        confidence=90,
        reasoning="Selling because I want to",
        ticker="AAPL",
        source_id="src1",
        sell_tool_called=False
    )
    md["analyze"].return_value = ([decision], [], "Mocked context", "")
    
    # Mock possession check
    md["portfolio"].positions = {"AAPL": MagicMock()}
    
    await run_ingest(force=True)
    # Verify rejection
    md["portfolio"].execute_trade.assert_not_called()
    md["save"].assert_called_once()
    kwargs = md["save"].call_args[1]
    assert kwargs.get("status") == "REJECTED_TOOL_USAGE"

@pytest.mark.asyncio
async def test_run_ingest_sell_with_tool(mock_dependencies):
    """Test that a SELL decision with tool usage passes the guardrail."""
    md = mock_dependencies
    
    # 2. Decision with tool call
    decision = DecisionObject(
        signal="SELL",
        confidence=90,
        reasoning="Selling 50% as per tool calculation",
        ticker="AAPL",
        source_id="src1",
        sell_tool_called=True,
        quantity=5
    )
    md["analyze"].return_value = ([decision], [], "Mocked context", "")
    
    # Mock validation and possession
    md["validate"].return_value = ValidationResult(
        status=ValidationStatus.PASSED,
        market_price=100.0,
        ticker="AAPL"
    )
    md["portfolio"].positions = {"AAPL": MagicMock(quantity=10)}
    
    await run_ingest(force=True)
    # Verify execution with correct quantity
    md["portfolio"].execute_trade.assert_awaited_once()
    args, kwargs = md["portfolio"].execute_trade.call_args
    # AAPL, 5, price, SELL
    assert args[0] == "AAPL"
    assert args[1] == 5
    assert args[3] == "SELL"


@pytest.mark.asyncio
async def test_run_ingest_calls_dust_cleanup_first(mock_dependencies):
    """Verify that dust cleanup runs BEFORE analysis to ensure a clean portfolio."""
    md = mock_dependencies
    
    # Return empty to skip analysis
    md["analyze"].return_value = ([], [], "", "")
    
    await run_ingest(force=True)
    
    # Verify dust cleanup was called
    md["dust_cleanup"].assert_called_once()
    # Verify DB client was accessed (called multiple times during full pipeline)
    md["db"].assert_called()
