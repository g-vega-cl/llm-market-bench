"""Unit tests for the decomposed CLI parser and subcommand routers."""

import argparse
from unittest.mock import AsyncMock, patch

import pytest

from cli.audit import handle_audit, handle_audit_alpaca, handle_audit_portfolios, handle_cleanup
from cli.autoresearch import (
    handle_autoresearch,
    handle_backtest_daily_autoresearch,
    handle_bootstrap_autoresearch,
    handle_daily_autoresearch,
)
from cli.ingest import (
    handle_calendar,
    handle_cause_and_effect,
    handle_government,
    handle_ingest,
    handle_lin_renko,
    handle_post_analysis,
    handle_weekend_ingest,
)
from cli.parser import build_parser
from cli.predictions import (
    handle_daily_postmortem,
    handle_daily_predictor,
    handle_evaluate_daily_predictions,
    handle_gainers_postmortem,
    handle_generate_newsletter,
    handle_historical_analog,
    handle_seed_daily_predictor,
)
from cli.router import dispatch, run_cli
from cli.trading import (
    handle_daily_trade,
    handle_frontier_tech,
    handle_future_forces,
    handle_sector_trade,
)


def test_parser_defaults_and_choices():
    """Verify parser registers expected arguments with correct defaults."""
    parser = build_parser()
    args = parser.parse_args(["ingest"])
    assert args.command == "ingest"
    assert args.force is False
    assert args.dry_run is False
    assert args.ticker == "SPY"
    assert args.model == "MiniMax-M3"
    assert args.days == 7


def test_parser_custom_flags():
    """Verify parser correctly reads custom CLI flags."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "gainers-postmortem",
            "--timeframe",
            "weekly",
            "--limit",
            "5",
            "--no-save-memory",
        ]
    )
    assert args.command == "gainers-postmortem"
    assert args.timeframe == "weekly"
    assert args.limit == 5
    assert args.no_save_memory is True


def test_dispatch_unknown_command_raises():
    """Verify dispatch raises ValueError for unrecognized commands."""
    args = argparse.Namespace(command="unknown-cmd")
    with pytest.raises(ValueError, match="Unknown command: unknown-cmd"):
        dispatch(args)


def test_handle_ingest_dispatches():
    """Verify handle_ingest invokes run_ingest with arguments."""
    with patch("cli.ingest.run_ingest", new_callable=AsyncMock) as mock_ingest:
        args = argparse.Namespace(force=True, dry_run=True)
        handle_ingest(args)
        mock_ingest.assert_awaited_once_with(force=True, dry_run=True)


def test_handle_weekend_ingest_dispatches():
    """Verify handle_weekend_ingest invokes run_weekend_ingest."""
    with patch("cli.ingest.run_weekend_ingest", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace()
        handle_weekend_ingest(args)
        mock_run.assert_awaited_once()


def test_handle_post_analysis_dispatches():
    """Verify handle_post_analysis invokes run_post_analysis."""
    with patch("cli.ingest.run_post_analysis", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace()
        handle_post_analysis(args)
        mock_run.assert_awaited_once()


def test_handle_government_dispatches():
    """Verify handle_government invokes run_government_pipeline."""
    with patch("cli.ingest.run_government_pipeline", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace()
        handle_government(args)
        mock_run.assert_awaited_once()


def test_handle_calendar_dispatches():
    """Verify handle_calendar invokes run_calendar_pipeline and catalyst radar."""
    with (
        patch("cli.ingest.run_calendar_pipeline", new_callable=AsyncMock) as mock_cal,
        patch("analysis.catalyst_radar.compute_and_store_catalyst_radar") as mock_radar,
    ):
        args = argparse.Namespace()
        handle_calendar(args)
        mock_cal.assert_awaited_once()
        mock_radar.assert_called_once()


def test_handle_cause_and_effect_dispatches():
    """Verify handle_cause_and_effect invokes run_cause_and_effect."""
    with patch("cli.ingest.run_cause_and_effect", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace()
        handle_cause_and_effect(args)
        mock_run.assert_awaited_once()


def test_handle_lin_renko_dispatches():
    """Verify handle_lin_renko invokes run_lin_renko_flow."""
    with patch("cli.ingest.run_lin_renko_flow", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace()
        handle_lin_renko(args)
        mock_run.assert_awaited_once()


def test_handle_daily_predictor_dispatches():
    """Verify handle_daily_predictor invokes run_daily_prediction."""
    with patch("tasks.daily_predictor.run_daily_prediction", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(ticker="QQQ", force=True)
        handle_daily_predictor(args)
        mock_run.assert_awaited_once_with(ticker="QQQ", force=True)


def test_handle_evaluate_daily_predictions_dispatches():
    """Verify handle_evaluate_daily_predictions invokes evaluate_daily_predictions."""
    with patch("tasks.evaluate_daily_predictions.evaluate_daily_predictions", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(target_date="2026-09-01", force=True)
        handle_evaluate_daily_predictions(args)
        mock_run.assert_awaited_once_with(target_date="2026-09-01", force_recalc=True)


def test_handle_seed_daily_predictor_dispatches():
    """Verify handle_seed_daily_predictor invokes seed_daily_predictor_prompt."""
    with patch("tasks.daily_predictor.seed_daily_predictor_prompt", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace()
        handle_seed_daily_predictor(args)
        mock_run.assert_awaited_once()


def test_handle_daily_postmortem_dispatches():
    """Verify handle_daily_postmortem invokes run_daily_postmortem."""
    with patch("analysis.daily_postmortem.run_daily_postmortem", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(target_date="2026-09-24", force=True)
        handle_daily_postmortem(args)
        mock_run.assert_awaited_once_with(target_date="2026-09-24", force=True)


def test_handle_gainers_postmortem_dispatches():
    """Verify handle_gainers_postmortem invokes run_gainers_postmortem."""
    with patch("analysis.gainers_postmortem.run_gainers_postmortem", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(timeframe="weekly", limit=2, no_save_memory=True)
        handle_gainers_postmortem(args)
        mock_run.assert_awaited_once_with(timeframe="weekly", limit=2, save_memory=False)


def test_handle_historical_analog_dispatches():
    """Verify handle_historical_analog invokes research_historical_market_analog."""
    with (
        patch(
            "analysis.historical_analogs.research_historical_market_analog",
            new_callable=AsyncMock,
            return_value="Analog Report",
        ) as mock_run,
        patch("builtins.print") as mock_print,
    ):
        args = argparse.Namespace(situation="Inflation shock", assets="TLT,GLD", horizon="1m")
        handle_historical_analog(args)
        mock_run.assert_awaited_once_with(
            situation="Inflation shock",
            focus_assets=["TLT", "GLD"],
            horizon="1m",
        )
        mock_print.assert_called_with("Analog Report")


def test_handle_generate_newsletter_dispatches():
    """Verify handle_generate_newsletter invokes generate_daily_newsletter."""
    with patch("tasks.newsletter_generator.generate_daily_newsletter", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(session="close")
        handle_generate_newsletter(args)
        mock_run.assert_awaited_once_with(session="close")


def test_handle_sector_trade_dispatches():
    """Verify handle_sector_trade invokes run_sector_trade."""
    with patch("execution.sector_trading.run_sector_trade", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(action="entry", target_date="2026-09-01", dry_run=True)
        handle_sector_trade(args)
        mock_run.assert_awaited_once_with(action="entry", target_date_str="2026-09-01", dry_run=True)


def test_handle_daily_trade_actions_dispatches():
    """Verify handle_daily_trade routes entry, target-orders, and exit actions."""
    with (
        patch("execution.daily_trading.execute_daily_moo_entries", new_callable=AsyncMock) as mock_entry,
        patch("execution.daily_trading.place_daily_target_limit_orders", new_callable=AsyncMock) as mock_orders,
        patch("execution.daily_trading.execute_daily_close_exits", new_callable=AsyncMock) as mock_exit,
    ):
        # Entry
        handle_daily_trade(argparse.Namespace(action="entry", target_date=None, dry_run=False))
        mock_entry.assert_awaited_once()

        # Target-orders
        handle_daily_trade(argparse.Namespace(action="target-orders", target_date=None, dry_run=False))
        mock_orders.assert_awaited_once()

        # Exit
        handle_daily_trade(argparse.Namespace(action="exit", target_date=None, dry_run=False))
        mock_exit.assert_awaited_once()


def test_handle_frontier_tech_dispatches():
    """Verify handle_frontier_tech invokes run_frontier_tech_task."""
    with patch("tasks.frontier_tech_task.run_frontier_tech_task", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(mode="auto", dry_run=True, target_weight=0.05)
        handle_frontier_tech(args)
        mock_run.assert_awaited_once_with(mode="auto", dry_run=True, target_weight=0.05)


def test_handle_future_forces_dispatches():
    """Verify handle_future_forces invokes run_future_forces_task."""
    with patch("tasks.future_forces_task.run_future_forces_task", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(mode="sentinel", dry_run=True, force_market=True, target_weight=0.04)
        handle_future_forces(args)
        mock_run.assert_awaited_once_with(
            mode="sentinel",
            dry_run=True,
            force_market=True,
            target_weight=0.04,
        )


def test_handle_autoresearch_dispatches():
    """Verify handle_autoresearch invokes run or run_all based on track_id."""
    with (
        patch("autoresearch.runner.run_all", new_callable=AsyncMock) as mock_run_all,
        patch("autoresearch.runner.run", new_callable=AsyncMock) as mock_run,
    ):
        handle_autoresearch(argparse.Namespace(track_id="all", dry_run=True, cold_start=True))
        mock_run_all.assert_awaited_once_with(dry_run=True, cold_start=True)

        handle_autoresearch(argparse.Namespace(track_id="track_a", dry_run=False, cold_start=False))
        mock_run.assert_awaited_once_with(dry_run=False, track_id="track_a", cold_start=None)


def test_handle_bootstrap_autoresearch_dispatches():
    """Verify handle_bootstrap_autoresearch invokes bootstrap."""
    with patch("autoresearch.bootstrap.bootstrap", new_callable=AsyncMock) as mock_boot:
        args = argparse.Namespace()
        handle_bootstrap_autoresearch(args)
        mock_boot.assert_awaited_once()


def test_handle_daily_autoresearch_dispatches():
    """Verify handle_daily_autoresearch invokes run_daily_autoresearch."""
    with patch("tasks.daily_autoresearch.run_daily_autoresearch", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(dry_run=True, cold_start=True)
        handle_daily_autoresearch(args)
        mock_run.assert_awaited_once_with(dry_run=True, cold_start=True)


def test_handle_backtest_daily_autoresearch_dispatches():
    """Verify handle_backtest_daily_autoresearch invokes run_backtest_daily_autoresearch."""
    with patch("tasks.backtest_daily_autoresearch.run_backtest_daily_autoresearch", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(start_date="2026-05-01", weeks=2)
        handle_backtest_daily_autoresearch(args)
        mock_run.assert_awaited_once_with(start_date_str="2026-05-01", weeks=2)


def test_handle_audit_dispatches():
    """Verify handle_audit configures analyzer and invokes run_audit."""
    with (
        patch("core.audit.runner.configure") as mock_cfg_audit,
        patch("core.audit.analyzer.configure") as mock_cfg_analyzer,
        patch("core.audit.run_audit", new_callable=AsyncMock) as mock_run,
    ):
        args = argparse.Namespace(dry_run=True)
        handle_audit(args)
        mock_cfg_audit.assert_called_once()
        mock_cfg_analyzer.assert_called_once()
        mock_run.assert_awaited_once_with(dry_run=True)


def test_handle_audit_alpaca_dispatches():
    """Verify handle_audit_alpaca invokes run_alpaca_audit."""
    with patch("audit.alpaca_audit.run_alpaca_audit", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(model="GPT-4o", days=14, json=True)
        handle_audit_alpaca(args)
        mock_run.assert_awaited_once_with(model_name="GPT-4o", days=14, json_output=True)


def test_handle_audit_portfolios_dispatches():
    """Verify handle_audit_portfolios invokes run_portfolio_auditor_cli."""
    with patch("audit.portfolio_auditor.run_portfolio_auditor_cli", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace(target_date="2026-09-01", lookback_days=10, fix=True)
        handle_audit_portfolios(args)
        mock_run.assert_awaited_once_with(target_date="2026-09-01", lookback_days=10, fix=True)


def test_handle_cleanup_dispatches():
    """Verify handle_cleanup invokes run_cleanup."""
    with patch("core.cleanup.run_cleanup", new_callable=AsyncMock) as mock_run:
        args = argparse.Namespace()
        handle_cleanup(args)
        mock_run.assert_awaited_once()


def test_run_cli_entry_point():
    """Verify run_cli parses provided arg list and dispatches."""
    with patch("cli.ingest.run_weekend_ingest", new_callable=AsyncMock) as mock_run:
        run_cli(["weekend-ingest"])
        mock_run.assert_awaited_once()
