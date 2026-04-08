import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from core.models import DecisionObject
from execution.validation import ValidationResult, ValidationStatus
from main import _stage_decision_processing, run_ingest

@pytest.fixture
def mock_deps():
    with patch("main.ingest_newsletters") as mock_ingest, \
         patch("main.get_supabase_client") as mock_get_client, \
         patch("main.upsert_newsletter_snapshot") as mock_upsert, \
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
        mock_ingest.return_value = []
        mock_consensus.return_value = []
        mock_contrarian.return_value = ([], [])
        mock_overlap.return_value = None
        mock_validate.side_effect = lambda t, p: ValidationResult(
            status=ValidationStatus.PASSED,
            market_price=100.0,
            ticker=t
        )
        mock_verify.return_value = MagicMock(status="APPROVED", verification_reasoning="Verified", confidence_score=100, alternative_ticker=None)

        # Mock MDM
        mock_mdm_instance = MockMDM.return_value
        mock_mdm_instance.get_quote = AsyncMock()
        mock_mdm_instance.get_quote.side_effect = lambda t, **kwargs: MagicMock(price=100.0, exists=True)
        mock_mdm_instance.get_quotes = AsyncMock()
        mock_mdm_instance.get_quotes.side_effect = lambda tickers, **kwargs: {t: MagicMock(price=100.0) for t in tickers}

        yield {
            "Portfolio": MockPortfolio,
            "validate": mock_validate,
            "save": mock_save,
            "MDM": MockMDM,
            "mdm_instance": mock_mdm_instance,
            "analyze": mock_analyze,
            "overlap": mock_overlap,
            "verify": mock_verify
        }

@pytest.mark.asyncio
async def test_concurrent_buy_double_spend_prevention(mock_deps):
    """
    Scenario: 2 BUY decisions for same provider.
    Combined cost exceeds Buying Power.
    Expected: One EXECUTED, one REJECTED_MARGIN.
    """
    md = mock_deps

    # Decisions
    d1 = DecisionObject(signal="BUY", ticker="TICK1", confidence=80, reasoning="R1", source_id="s1", model_name="agent-a", price=1000.0)
    d2 = DecisionObject(signal="BUY", ticker="TICK2", confidence=80, reasoning="R2", source_id="s2", model_name="agent-a", price=1000.0)

    # Shared state for mock portfolio
    state = {
        "buying_power": 1500.0,
        "total_equity": 10000.0
    }

    from execution.reg_t_validation import RegTMetrics, ValidationResult as ComplianceResult

    def get_metrics():
        return RegTMetrics(
            total_equity=state["total_equity"],
            initial_margin_req=0, maintenance_margin_req=0,
            available_funds=state["buying_power"]/4,
            excess_liquidity=state["buying_power"]/4,
            sma=10000.0, realized=10000.0,
            buying_power=state["buying_power"]
        )

    # Mock Portfolio
    portfolio = MagicMock()
    md["Portfolio"].return_value = portfolio
    portfolio.initialize = AsyncMock()
    portfolio.get_portfolio_summary = AsyncMock(return_value="Summary")
    portfolio.execute_trade = AsyncMock()
    portfolio.positions = {}

    async def side_effect_init():
        portfolio.metrics = get_metrics()
    portfolio.initialize.side_effect = side_effect_init

    def side_effect_validate(ticker, qty, price, signal, **kwargs):
        current_metrics = get_metrics()
        if current_metrics.buying_power < (qty * price):
            return ComplianceResult(passed=False, reason="Insufficient Buying Power")
        return ComplianceResult(passed=True)

    portfolio.validate_trade.side_effect = side_effect_validate

    async def side_effect_execute(ticker, qty, price, signal, **kwargs):
        state["buying_power"] -= (qty * price) * 0.57 * 4 # BP reduction
        return "trade-uuid"
    portfolio.execute_trade.side_effect = side_effect_execute

    await _stage_decision_processing([d1, d2], [], [], "", "", MagicMock())

    statuses = [call.kwargs.get("status") for call in md["save"].call_args_list if call.kwargs.get("status") not in ["VALIDATED", "PASSED"]]
    assert "EXECUTED" in statuses
    assert "REJECTED_MARGIN" in statuses

@pytest.mark.asyncio
async def test_replay_determinism(mock_deps):
    """
    Run same batch of concurrent decisions 5 times.
    Verify identical counts of execution/rejection.
    """
    md = mock_deps

    d1 = DecisionObject(signal="BUY", ticker="T1", confidence=80, reasoning="R1", source_id="s1", model_name="agent-1", price=1000.0)
    d2 = DecisionObject(signal="BUY", ticker="T2", confidence=80, reasoning="R2", source_id="s2", model_name="agent-1", price=1000.0)
    d3 = DecisionObject(signal="BUY", ticker="T3", confidence=80, reasoning="R3", source_id="s3", model_name="agent-2", price=1000.0)
    d4 = DecisionObject(signal="BUY", ticker="T4", confidence=80, reasoning="R4", source_id="s4", model_name="agent-2", price=1000.0)

    results_history = []

    for _ in range(5):
        md["save"].reset_mock()
        states = {
            "agent-1": {"bp": 1500.0},
            "agent-2": {"bp": 1500.0}
        }

        def portfolio_factory(owner_id):
            p = MagicMock()
            p.owner_id = owner_id
            p.initialize = AsyncMock()
            p.get_portfolio_summary = AsyncMock(return_value="Summary")
            p.execute_trade = AsyncMock(return_value="uuid")
            p.positions = {}

            from execution.reg_t_validation import RegTMetrics, ValidationResult as ComplianceResult

            async def side_effect_init():
                p.metrics = RegTMetrics(total_equity=10000, initial_margin_req=0, maintenance_margin_req=0,
                                       available_funds=states[owner_id]["bp"]/4, excess_liquidity=states[owner_id]["bp"]/4,
                                       sma=10000, realized=10000, buying_power=states[owner_id]["bp"])
            p.initialize.side_effect = side_effect_init

            def side_effect_validate(ticker, qty, price, signal, **kwargs):
                if states[owner_id]["bp"] < (qty * price):
                    return ComplianceResult(passed=False, reason="Too expensive")
                return ComplianceResult(passed=True)
            p.validate_trade.side_effect = side_effect_validate

            async def side_effect_exec(ticker, qty, price, signal, **kwargs):
                states[owner_id]["bp"] -= 2000.0 # Force next to fail
                return "uuid"
            p.execute_trade.side_effect = side_effect_exec
            return p

        md["Portfolio"].side_effect = portfolio_factory
        await _stage_decision_processing([d1, d2, d3, d4], [], [], "", "", MagicMock())

        statuses = sorted([call.kwargs.get("status") for call in md["save"].call_args_list if call.kwargs.get("status") not in ["VALIDATED", "PASSED"]])
        results_history.append(statuses)

    first_run = results_history[0]
    for run in results_history[1:]:
        assert run == first_run

    assert results_history[0].count("EXECUTED") == 2
    assert results_history[0].count("REJECTED_MARGIN") == 2

@pytest.mark.asyncio
async def test_stable_execution_order(mock_deps):
    """
    Verify that decisions are executed in deterministic order regardless of verifier completion time.
    """
    md = mock_deps

    # Setup 3 decisions
    # Sorting is by (model_name, ticker)
    d1 = DecisionObject(signal="BUY", ticker="A", confidence=80, reasoning="R1", source_id="s1", model_name="agent-1", price=100.0)
    d2 = DecisionObject(signal="BUY", ticker="B", confidence=80, reasoning="R2", source_id="s2", model_name="agent-1", price=100.0)
    d3 = DecisionObject(signal="BUY", ticker="C", confidence=80, reasoning="R3", source_id="s3", model_name="agent-1", price=100.0)

    # Mock verifier to finish in reverse order
    delays = {"A": 0.1, "B": 0.05, "C": 0.01}
    async def side_effect_verify(decision, **kwargs):
        await asyncio.sleep(delays.get(decision.ticker, 0))
        return MagicMock(status="APPROVED", verification_reasoning="OK", confidence_score=100)

    md["verify"].side_effect = side_effect_verify

    # Track execution order
    execution_sequence = []

    portfolio = MagicMock()
    md["Portfolio"].return_value = portfolio
    portfolio.initialize = AsyncMock()
    portfolio.get_portfolio_summary = AsyncMock(return_value="Summary")
    portfolio.metrics = MagicMock(buying_power=10000.0, total_equity=10000.0)

    async def side_effect_exec(ticker, *args, **kwargs):
        execution_sequence.append(ticker)
        return "uuid"
    portfolio.execute_trade.side_effect = side_effect_exec

    # Mock validate_trade
    from execution.reg_t_validation import ValidationResult as ComplianceResult
    portfolio.validate_trade.return_value = ComplianceResult(passed=True)

    await _stage_decision_processing([d3, d2, d1], [], [], "", "", MagicMock())

    assert execution_sequence == ["A", "B", "C"]
