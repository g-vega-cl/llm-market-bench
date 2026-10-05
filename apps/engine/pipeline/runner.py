"""High-level pipeline runners for daily ingestion, weekend analysis, and impact audits."""

import io
import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from analysis.cause_and_effect_analysis import perform_cause_and_effect_analysis
from analysis.market_feeling import analyze_market_feeling
from analysis.post_analysis import perform_post_analysis
from core.config import logger
from core.db import get_supabase_client
from pipeline.decision_processor import _stage_decision_processing
from pipeline.resolver import resolve_dep
from pipeline.stages import (
    _stage_analysis_and_consensus,
    _stage_dust_cleanup,
    _stage_ingest_and_snapshot,
    _stage_snapshots_and_pca,
)


async def run_ingest(force: bool = False, dry_run: bool = False):
    """Runs the full ingestion and analysis pipeline."""
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    engine_logger = logging.getLogger("engine")
    engine_logger.setLevel(logging.DEBUG)
    engine_logger.addHandler(handler)

    dt_cls = resolve_dep("datetime", datetime)
    now = dt_cls.now(UTC)
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_date = now.date()
    current_hour_et = dt_cls.now(ZoneInfo("America/New_York")).hour
    run_number = 1 if current_hour_et < 10 else (2 if current_hour_et < 13 else 3)

    log_blob = ""
    sb_client = None

    dust_cleanup_fn = resolve_dep("_stage_dust_cleanup", _stage_dust_cleanup)
    from analysis.intraday_news import sync_intraday_market_news

    sync_intraday_news_fn = resolve_dep("sync_intraday_market_news", sync_intraday_market_news)
    ingest_snapshot_fn = resolve_dep("_stage_ingest_and_snapshot", _stage_ingest_and_snapshot)
    analysis_consensus_fn = resolve_dep("_stage_analysis_and_consensus", _stage_analysis_and_consensus)
    decision_processing_fn = resolve_dep("_stage_decision_processing", _stage_decision_processing)
    snapshots_pca_fn = resolve_dep("_stage_snapshots_and_pca", _stage_snapshots_and_pca)
    market_feeling_fn = resolve_dep("analyze_market_feeling", analyze_market_feeling)
    get_client_fn = resolve_dep("get_supabase_client", get_supabase_client)
    log = resolve_dep("logger", logger)

    try:
        from core.utils import is_market_open_with_logging

        if dry_run:
            log.info("[DRY RUN] Ingestion running in simulation mode. Bypassing market-hours check.")
        elif not await is_market_open_with_logging(force):
            log_blob = log_capture.getvalue()
            if log_blob:
                try:
                    sb_client = get_client_fn()
                    sb_client.table("ingestion_logs").insert(
                        {
                            "run_id": run_id,
                            "run_date": str(run_date),
                            "run_number": run_number,
                            "log_blob": log_blob[:1000000],
                        }
                    ).execute()
                except Exception as e:
                    log.error(f"Failed to save ingestion log: {e}")
            return

        sb_client = get_client_fn()

        await dust_cleanup_fn(sb_client, dry_run=dry_run)

        try:
            await sync_intraday_news_fn(force=False, sb_client=sb_client)
        except Exception as e:
            log.warning(f"Intraday market news sync encountered error: {e}")

        data, sb_client = await ingest_snapshot_fn(dry_run=dry_run)
        sb_client = sb_client or get_client_fn()
        if not data:
            log_blob = log_capture.getvalue()
            if log_blob and not dry_run:
                try:
                    sb_client.table("ingestion_logs").insert(
                        {
                            "run_id": run_id,
                            "run_date": str(run_date),
                            "run_number": run_number,
                            "log_blob": log_blob[:1000000],
                        }
                    ).execute()
                except Exception as e:
                    log.error(f"Failed to save ingestion log: {e}")
            return

        try:
            decisions, macro_events, agg_ctx, uncrowded_ctx = await analysis_consensus_fn(data, sb_client)
            from analysis.consensus import get_last_consensus_events

            consensus_events = get_last_consensus_events()
            await decision_processing_fn(
                decisions,
                macro_events,
                data,
                agg_ctx,
                uncrowded_ctx,
                sb_client,
                consensus_events,
                dry_run=dry_run,
            )

            if not dry_run:
                try:
                    now_ny = dt_cls.now(ZoneInfo("America/New_York"))
                    if now_ny.weekday() == 0 and now_ny.hour < 11:
                        log.info("Monday morning detected — Checking systematic weekly sector portfolio entry...")
                        from execution.sector_trading import run_sector_trade

                        await run_sector_trade(action="entry")
                except Exception:
                    log.exception("Systematic weekly sector entry hook failed")

                try:
                    now_ny = dt_cls.now(ZoneInfo("America/New_York"))
                    if now_ny.hour == 9 and now_ny.minute >= 30:
                        log.info("Morning open session detected — Submitting daily SPY target limit orders...")
                        from execution.daily_trading import place_daily_target_limit_orders

                        await place_daily_target_limit_orders(dry_run=dry_run)
                except Exception:
                    log.exception("Daily SPY target limit orders hook failed")

                try:
                    now_ny = dt_cls.now(ZoneInfo("America/New_York"))
                    if now_ny.weekday() == 4 and now_ny.hour >= 15:
                        log.info("Friday afternoon detected — Checking systematic weekly sector portfolio exit...")
                        from execution.sector_trading import run_sector_trade

                        await run_sector_trade(action="exit")
                except Exception:
                    log.exception("Systematic weekly sector exit hook failed")

                try:
                    now_ny = dt_cls.now(ZoneInfo("America/New_York"))
                    if now_ny.hour >= 15:
                        log.info("Afternoon session detected — Checking daily systematic SPY close exits...")
                        from execution.daily_trading import execute_daily_close_exits

                        await execute_daily_close_exits(dry_run=dry_run)
                except Exception:
                    log.exception("Daily systematic SPY close exit hook failed")

            await snapshots_pca_fn(sb_client, dry_run=dry_run)

            log.info("Starting Market Feeling Analysis with MiniMax...")
            market_feeling = await market_feeling_fn()
            if market_feeling:
                log.info(
                    f"Market feeling: {market_feeling.get('sentiment_label')} {market_feeling.get('sentiment_emoji')}"
                )
            else:
                log.warning("Market feeling analysis did not produce a result.")

            if not dry_run:
                try:
                    log.info("Starting Isolated LIN Renko Flow...")
                    from tasks.lin_renko_task import run_lin_renko_flow

                    lin_result = await run_lin_renko_flow()
                    log.info(
                        f"Isolated LIN Renko Flow completed (Decision: {lin_result.get('decision', {}).get('decision')}, "
                        f"Trade Executed: {lin_result.get('trade_executed')})."
                    )
                except Exception:
                    log.exception("Isolated LIN Renko Flow execution failed")
        finally:
            from execution.providers.factory import get_active_provider_class

            await get_active_provider_class().disconnect_all()

        log_blob = log_capture.getvalue()
        if not dry_run:
            try:
                sb_client.table("ingestion_logs").insert(
                    {
                        "run_id": run_id,
                        "run_date": str(run_date),
                        "run_number": run_number,
                        "log_blob": log_blob[:1000000],
                    }
                ).execute()
            except Exception as e:
                log.error(f"Failed to save ingestion log: {e}")
        else:
            log.info(f"[DRY RUN] Simulation complete for run_id {run_id}. Log capture size: {len(log_blob)} chars.")
    finally:
        engine_logger.removeHandler(handler)


async def run_weekend_ingest():
    """Weekend read-only pipeline: news ingestion + market feeling update."""
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    engine_logger = logging.getLogger("engine")
    engine_logger.setLevel(logging.DEBUG)
    engine_logger.addHandler(handler)

    dt_cls = resolve_dep("datetime", datetime)
    now = dt_cls.now(UTC)
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_date = now.date()

    log_blob = ""
    get_client_fn = resolve_dep("get_supabase_client", get_supabase_client)
    ingest_snapshot_fn = resolve_dep("_stage_ingest_and_snapshot", _stage_ingest_and_snapshot)
    market_feeling_fn = resolve_dep("analyze_market_feeling", analyze_market_feeling)
    log = resolve_dep("logger", logger)

    try:
        sb_client = get_client_fn()

        data, sb_client = await ingest_snapshot_fn()
        sb_client = sb_client or get_client_fn()
        if not data:
            log_blob = log_capture.getvalue()
            if log_blob:
                try:
                    sb_client.table("ingestion_logs").insert(
                        {"run_id": run_id, "run_date": str(run_date), "run_number": 1, "log_blob": log_blob[:1000000]}
                    ).execute()
                except Exception as e:
                    log.error(f"Failed to save ingestion log: {e}")
            return

        log.info("Starting Weekend Market Feeling Analysis...")
        market_feeling = await market_feeling_fn(weekend_mode=True)
        if market_feeling:
            log.info(
                f"Weekend market feeling: {market_feeling.get('sentiment_label')} {market_feeling.get('sentiment_emoji')}"
            )
        else:
            log.warning("Weekend market feeling analysis did not produce a result.")

        log_blob = log_capture.getvalue()
        try:
            sb_client.table("ingestion_logs").insert(
                {"run_id": run_id, "run_date": str(run_date), "run_number": 1, "log_blob": log_blob[:1000000]}
            ).execute()
        except Exception as e:
            log.error(f"Failed to save ingestion log: {e}")
    finally:
        engine_logger.removeHandler(handler)


async def run_post_analysis():
    """Runs the post-analysis for historical trades."""
    try:
        await perform_post_analysis(windows=[5, 14, 30])
    finally:
        from execution.providers.factory import get_active_provider_class

        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()


async def run_cause_and_effect():
    """Runs the cause-and-effect analysis for market events."""
    try:
        await perform_cause_and_effect_analysis()
    finally:
        from execution.providers.factory import get_active_provider_class

        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()
