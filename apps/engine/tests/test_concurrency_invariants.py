from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import DecisionObject
from execution.validation import ValidationResult, ValidationStatus
from main import _stage_decision_processing


@pytest.fixture
def mock_deps():
    with (
        patch("main.ingest_newsletters") as mock_ingest,
        patch("main.get_supabase_client"),
        patch("main.bulk_upsert_newsletter_snapshots"),
        patch("main.upsert_newsletter_snapshot"),
        patch("main.analyze_chunks", new_callable=AsyncMock) as mock_analyze,
        patch("main.process_consensus", new_callable=AsyncMock) as mock_consensus,
        patch("main.analyze_momentum", new_callable=AsyncMock),
        patch("main.decay_stale_concepts", new_callable=AsyncMock),
        patch("main.run_contrarian_analysis", new_callable=AsyncMock) as mock_contrarian,
        patch("main.validate_decision", new_callable=AsyncMock) as mock_validate,
        patch("main.validate_semantic_overlap", new_callable=AsyncMock) as mock_overlap,
        patch("main.Portfolio") as MockPortfolio,
        patch("execution.market_data.MarketDataManager") as MockMDM,
        patch("main.verify_trading_decision", new_callable=AsyncMock) as mock_verify,
        patch("main.save_decision") as mock_save,
    ):
        # Setup defaults
        mock_ingest.return_value = []
        mock_consensus.return_value = []
        mock_contrarian.return_value = ([], [])
        mock_overlap.return_value = None
        mock_validate.side_effect = lambda t: ValidationResult(
            status=ValidationStatus.PASSED, market_price=100.0, ticker=t
        )
        mock_verify.return_value = MagicMock(
            status="APPROVED", verification_reasoning="Verified", confidence_score=100, alternative_ticker=None
        )

        # Mock MDM
        mock_mdm_instance = MockMDM.return_value
        mock_mdm_instance.get_quote = AsyncMock()
        mock_mdm_instance.get_quote.side_effect = lambda t, **kwargs: MagicMock(price=100.0, exists=True)
        mock_mdm_instance.get_quotes = AsyncMock()
        mock_mdm_instance.get_quotes.side_effect = lambda tickers, **kwargs: {
            t: MagicMock(price=100.0) for t in tickers
        }

        yield {
            "Portfolio": MockPortfolio,
            "validate": mock_validate,
            "save": mock_save,
            "MDM": MockMDM,
            "mdm_instance": mock_mdm_instance,
            "analyze": mock_analyze,
            "overlap": mock_overlap,
            "verify": mock_verify,
        }


@pytest.mark.asyncio
async def test_conviction_priority_double_buy(mock_deps):
    """
    Scenario: 2 BUY decisions from same provider.
    First trade uses most available cash.
    Expected: First is EXECUTED, second is REJECTED_MARGIN.
    """
    md = mock_deps

    # Decisions (First has original_index=0)
    d1 = DecisionObject(
        signal="BUY",
        ticker="H_CONV",
        confidence=80,
        reasoning="R1",
        source_id="s1",
        model_name="agent-a",
        original_index=0,
    )
    d2 = DecisionObject(
        signal="BUY",
        ticker="L_CONV",
        confidence=80,
        reasoning="R2",
        source_id="s2",
        model_name="agent-a",
        original_index=1,
    )

    state = {"bp": 1500.0}
    from execution.reg_t_validation import RegTMetrics
    from execution.reg_t_validation import ValidationResult as ComplianceResult

    def get_metrics():
        return RegTMetrics(
            total_equity=10000,
            initial_margin_req=0,
            maintenance_margin_req=0,
            available_funds=state["bp"] / 4,
            excess_liquidity=state["bp"] / 4,
            sma=10000,
            realized=10000,
            buying_power=state["bp"],
        )

    portfolio = MagicMock()
    md["Portfolio"].return_value = portfolio
    portfolio.initialize = AsyncMock()
    portfolio.get_portfolio_summary = AsyncMock(return_value="Summary")
    portfolio.execute_trade = AsyncMock(return_value="uuid")
    portfolio.positions = {}

    async def side_effect_init():
        portfolio.metrics = get_metrics()

    portfolio.initialize.side_effect = side_effect_init

    def side_effect_validate(ticker, qty, price, signal, **kwargs):
        if get_metrics().buying_power < (qty * price):
            return ComplianceResult(passed=False, reason="Insufficient Buying Power")
        return ComplianceResult(passed=True)

    portfolio.validate_trade.side_effect = side_effect_validate

    async def side_effect_execute(ticker, qty, price, signal, **kwargs):
        state["bp"] -= 2000.0  # Force next to fail
        return "uuid"

    portfolio.execute_trade.side_effect = side_effect_execute

    await _stage_decision_processing([d2, d1], [], [], "", "", MagicMock())  # Input shuffled, sort should fix

    # Verify results (Status check)
    # Decisions are sorted by original_index, so d1 executes first
    save_calls = md["save"].call_args_list
    final_statuses = {
        c.args[1].ticker: c.kwargs.get("status")
        for c in save_calls
        if c.kwargs.get("status") not in ["VALIDATED", "PASSED"]
    }

    assert final_statuses["H_CONV"] == "EXECUTED"
    assert final_statuses["L_CONV"] == "REJECTED_MARGIN"


@pytest.mark.asyncio
async def test_order_stability_shuffled_tickers(mock_deps):
    """
    Scenario: Same decision list, shuffled tickers but identical original order.
    Expected: Identical results every time.
    """
    md = mock_deps

    d1 = DecisionObject(
        signal="BUY", ticker="A", confidence=80, reasoning="R1", source_id="s1", model_name="agent-1", original_index=0
    )
    d2 = DecisionObject(
        signal="BUY", ticker="B", confidence=80, reasoning="R2", source_id="s2", model_name="agent-1", original_index=1
    )
    d3 = DecisionObject(
        signal="BUY", ticker="C", confidence=80, reasoning="R3", source_id="s3", model_name="agent-1", original_index=2
    )

    all_runs_sequence = []

    for _ in range(5):
        md["save"].reset_mock()
        state = {"bp": 1500.0}  # Can only afford one
        execution_order = []

        portfolio = MagicMock()
        md["Portfolio"].return_value = portfolio
        portfolio.initialize = AsyncMock()
        portfolio.get_portfolio_summary = AsyncMock(return_value="Summary")
        portfolio.execute_trade = AsyncMock(return_value="uuid")

        async def side_effect_init():
            from execution.reg_t_validation import RegTMetrics

            portfolio.metrics = RegTMetrics(
                total_equity=10000,
                initial_margin_req=0,
                maintenance_margin_req=0,
                available_funds=state["bp"] / 4,
                excess_liquidity=state["bp"] / 4,
                sma=10000,
                realized=10000,
                buying_power=state["bp"],
            )

        portfolio.initialize.side_effect = side_effect_init

        async def side_effect_exec(ticker, *args, **kwargs):
            execution_order.append(ticker)
            state["bp"] -= 2000.0
            return "uuid"

        portfolio.execute_trade.side_effect = side_effect_exec

        from execution.reg_t_validation import ValidationResult as ComplianceResult

        portfolio.validate_trade.side_effect = lambda *args, **kwargs: ComplianceResult(passed=state["bp"] >= 1000.0)

        # Shuffle and process
        import random

        shuffled = [d1, d2, d3]
        random.shuffle(shuffled)
        await _stage_decision_processing(shuffled, [], [], "", "", MagicMock())
        all_runs_sequence.append(execution_order)

    # All 5 runs should have identical sequence: ['A']
    for seq in all_runs_sequence:
        assert seq == ["A"]


@pytest.mark.asyncio
async def test_concurrent_buy_sell_same_ticker(mock_deps):
    """
    Scenario: BUY AAPL + SELL AAPL same agent in one batch.
    """
    md = mock_deps
    d_buy = DecisionObject(
        signal="BUY",
        ticker="AAPL",
        confidence=80,
        reasoning="Add",
        source_id="s1",
        model_name="agent-1",
        original_index=0,
    )
    d_sell = DecisionObject(
        signal="SELL",
        ticker="AAPL",
        confidence=80,
        reasoning="Trim",
        source_id="s2",
        model_name="agent-1",
        sell_tool_called=True,
        quantity=5,
        original_index=1,
    )

    state = {"positions": {}}
    execution_order = []
    portfolio = MagicMock()
    md["Portfolio"].return_value = portfolio
    portfolio.initialize = AsyncMock()
    portfolio.get_portfolio_summary = AsyncMock(return_value="Summary")
    portfolio.metrics = MagicMock(buying_power=10000.0, total_equity=10000.0)

    async def side_effect_init():
        portfolio.positions = {t: MagicMock(quantity=q) for t, q in state["positions"].items()}

    portfolio.initialize.side_effect = side_effect_init

    async def side_effect_exec(ticker, qty, price, signal, **kwargs):
        execution_order.append(signal)
        if signal == "BUY":
            state["positions"][ticker] = state["positions"].get(ticker, 0) + qty
        else:
            state["positions"][ticker] = state["positions"].get(ticker, 0) - qty
        return "uuid"

    portfolio.execute_trade.side_effect = side_effect_exec
    from execution.reg_t_validation import ValidationResult as ComplianceResult

    portfolio.validate_trade.return_value = ComplianceResult(passed=True)

    await _stage_decision_processing([d_sell, d_buy], [], [], "", "", MagicMock())
    assert execution_order == ["BUY", "SELL"]


@pytest.mark.asyncio
async def test_parallel_provider_isolation(mock_deps):
    """Verify no holdings bleed across providers during parallel processing."""
    md = mock_deps
    d1 = DecisionObject(
        signal="BUY",
        ticker="AAPL",
        confidence=80,
        reasoning="R1",
        source_id="s1",
        model_name="agent-1",
        original_index=0,
    )
    d2 = DecisionObject(
        signal="BUY",
        ticker="GOOGL",
        confidence=80,
        reasoning="R2",
        source_id="s2",
        model_name="agent-2",
        original_index=0,
    )

    portfolios = {}

    def portfolio_factory(owner_id):
        p = MagicMock()
        p.owner_id = owner_id
        p.initialize = AsyncMock()
        p.get_portfolio_summary = AsyncMock(return_value=f"Summary for {owner_id}")
        p.execute_trade = AsyncMock(return_value="uuid")
        p.positions = {}
        p.metrics = MagicMock(buying_power=10000.0, total_equity=10000.0)
        from execution.reg_t_validation import ValidationResult as ComplianceResult

        p.validate_trade.return_value = ComplianceResult(passed=True)
        portfolios[owner_id] = p
        return p

    md["Portfolio"].side_effect = portfolio_factory
    await _stage_decision_processing([d1, d2], [], [], "", "", MagicMock())
    assert "agent-1" in portfolios
    assert "agent-2" in portfolios
    assert portfolios["agent-1"] != portfolios["agent-2"]
