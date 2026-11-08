"""Hermetic tests for post-mortem attribution backfill utility."""

from unittest.mock import MagicMock

from scripts.backfill_postmortem_attribution import (
    calibrate_importance_score,
    resolve_model_name_for_trade,
    run_backfill,
)


def test_calibrate_importance_score():
    """Verify calibrated importance scores based on regret and price move severity."""
    # Preserves non-default score
    assert calibrate_importance_score(1.5, False, current_score=8) == 8

    # High regret and severe loss
    assert calibrate_importance_score(-5.5, is_regret=True, current_score=5) == 9
    assert calibrate_importance_score(-2.5, is_regret=True, current_score=5) == 8
    assert calibrate_importance_score(-0.8, is_regret=True, current_score=5) == 7

    # Non-regret large winner
    assert calibrate_importance_score(8.0, is_regret=False, current_score=5) == 8
    assert calibrate_importance_score(3.5, is_regret=False, current_score=5) == 7
    assert calibrate_importance_score(1.5, is_regret=False, current_score=5) == 6
    assert calibrate_importance_score(0.2, is_regret=False, current_score=5) == 5


def test_resolve_model_name_for_trade():
    """Verify model name resolution from portfolio owner_id or decisions."""
    portfolios_by_id = {
        "p-1": {"id": "p-1", "owner_id": "claude-3-5-sonnet"},
        "p-2": {"id": "p-2", "owner_id": "sys-daily-spy"},
    }

    # Trade linked to portfolio
    trade1 = {"id": "t-1", "portfolio_id": "p-1"}
    assert resolve_model_name_for_trade(trade1, portfolios_by_id) == "claude-3-5-sonnet"

    # Trade with embedded decision
    trade2 = {"id": "t-2", "portfolio_id": "unknown-port", "decisions": [{"model_name": "gpt-4o"}]}
    assert resolve_model_name_for_trade(trade2, portfolios_by_id) == "gpt-4o"

    # Trade without known portfolio or decision
    assert resolve_model_name_for_trade({"id": "t-3"}, portfolios_by_id) is None


def test_run_backfill_dry_run_and_apply():
    """Verify run_backfill scans memories, computes updates, and calls update when apply=True."""
    mock_sb = MagicMock()

    memories = [
        {
            "id": "mem-1",
            "content": "5-DAY POST-ANALYSIS (NVDA)...",
            "importance_score": 5,
            "metadata": {"trade_id": "trade-1", "model_name": "Unknown", "price_change_pct": -6.0, "is_regret": True},
        },
        {
            "id": "mem-2",
            "content": "Already fixed memory",
            "importance_score": 9,
            "metadata": {"model_name": "claude-3-5-sonnet"},
        },
    ]

    portfolios = [{"id": "port-1", "owner_id": "gemini-1.5-pro"}]
    trades = [{"id": "trade-1", "portfolio_id": "port-1", "decisions": []}]

    # Mock DB query responses
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = memories
    mock_sb.table.return_value.select.return_value.execute.return_value.data = portfolios
    mock_sb.table.return_value.select.return_value.in_.return_value.execute.return_value.data = trades

    # Dry run
    res_dry = run_backfill(client=mock_sb, apply=False)
    assert res_dry["scanned"] == 2
    assert res_dry["updated"] == 1
    assert res_dry["skipped"] == 1
    assert mock_sb.table.return_value.update.call_count == 0

    # Apply
    res_apply = run_backfill(client=mock_sb, apply=True)
    assert res_apply["updated"] == 1
    assert mock_sb.table.return_value.update.call_count == 1
    call_args = mock_sb.table.return_value.update.call_args[0][0]
    assert call_args["importance_score"] == 9
    assert call_args["metadata"]["model_name"] == "gemini-1.5-pro"
