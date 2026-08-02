"""Test verifying that single trade executions do NOT auto-persist to memories table.

Single-ticker execution reasoning (e.g. buying $WRLD) is trade-level noise,
not a macro market cycle thesis. Macro thematic flow theses belong to ingested
analyst notes, consensus synthesis, and macro seeding.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_decision(catalyst_type="UNCROWDED_TRADE", signal="BUY", model_provider="gemini"):
    """Build a minimal DecisionObject-like mock."""
    d = MagicMock()
    d.ticker = "WRLD"
    d.signal = signal
    d.catalyst_type = catalyst_type
    d.reasoning = "EM exposure uncrowded — frontier markets underowned."
    d.model_name = "gemini-flash"
    d.model_provider = model_provider
    d.confidence = 75
    d.allocation_percentage = 20
    d.quantity = None
    d.injected_market_price = 45.0
    d.sell_tool_called = False
    d.strategy_reasoning = "Uncrowded rotation thesis"
    d.is_priced_in_reasoning = "Not priced in"
    d.profit_potential_reasoning = "12-month target"
    d.advance_planning_notes = None
    d.original_index = 0
    return d


@pytest.mark.asyncio
async def test_process_single_decision_does_not_persist_single_trade_as_macro_memory():
    """Trade execution must NOT pollute macro memories table with single-ticker trade notes."""
    from main import _process_single_decision

    d = _make_decision(catalyst_type="UNCROWDED_TRADE", signal="BUY")

    fake_semaphore = AsyncMock()
    fake_semaphore.__aenter__ = AsyncMock(return_value=None)
    fake_semaphore.__aexit__ = AsyncMock(return_value=None)

    fake_lock = AsyncMock()
    fake_lock.__aenter__ = AsyncMock(return_value=None)
    fake_lock.__aexit__ = AsyncMock(return_value=None)

    portfolio_locks = {d.model_name: fake_lock}
    counters = {"lock": AsyncMock(), "rejected": 0, "saved": 0}
    counters["lock"].__aenter__ = AsyncMock(return_value=None)
    counters["lock"].__aexit__ = AsyncMock(return_value=None)

    mock_sb = MagicMock()

    fake_validation = MagicMock()
    from execution.validation import ValidationStatus

    fake_validation.status = ValidationStatus.PASSED
    fake_validation.market_price = 45.0

    fake_portfolio = AsyncMock()
    fake_portfolio.positions = {}
    fake_portfolio.metrics = MagicMock(buying_power=10000, total_equity=20000)
    fake_portfolio.get_portfolio_summary = AsyncMock(return_value="portfolio summary")
    fake_portfolio.execute_trade = AsyncMock(return_value="trade-123")
    fake_portfolio.validate_trade = MagicMock(return_value=MagicMock(passed=True))
    fake_portfolio.calculate_reg_t_metrics = MagicMock()
    fake_portfolio.save_metrics = AsyncMock()

    fake_verification = MagicMock()
    fake_verification.status = "APPROVED"
    fake_verification.verification_reasoning = "Looks good"
    fake_verification.confidence_score = 80
    fake_verification.alternative_ticker = None
    fake_verification.adjusted_quantity = None

    with (
        patch("main.validate_decision", return_value=fake_validation),
        patch("main.Portfolio", return_value=fake_portfolio),
        patch("main.save_decision", return_value={"id": "decision-abc"}),
        patch("main.verify_trading_decision", return_value=fake_verification),
        patch("main.validate_semantic_overlap", return_value=None),
        patch("execution.market_data.MarketDataManager") as mock_mdm_cls,
        patch("execution.alpaca_broker.AlpacaBroker"),
        patch("main.asyncio") as mock_asyncio,
        patch("memory.store.add_memory") as mock_add_memory,
    ):
        mock_asyncio.create_task = MagicMock()
        mdm = AsyncMock()
        mdm.get_quotes = AsyncMock(return_value={"WRLD": MagicMock(price=45.0, exists=True)})
        mdm.get_quote = AsyncMock(return_value=MagicMock(price=45.0, exists=True))
        mock_mdm_cls.return_value = mdm

        await _process_single_decision(
            d=d,
            contrarian_decisions=[],
            aggregated_context="",
            uncrowded_context="",
            sb_client=mock_sb,
            semaphore=fake_semaphore,
            portfolio_locks=portfolio_locks,
            counters=counters,
        )

    # Confirm add_memory was NOT called during trade execution
    mock_add_memory.assert_not_called()
