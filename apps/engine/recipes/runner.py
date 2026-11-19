"""Hourly scheduler & queue worker daemon for Strategy Recipes (MiniPC runner)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import logger
from core.db import get_supabase_client
from core.time_utils import EASTERN_TZ
from recipes.intraday_bars import TRADING_SLOTS_ET, snapshot_live_intraday_bars
from recipes.news_corpus import sync_live_news_to_corpus
from recipes.portfolio_engine import DEFAULT_CONCURRENCY_CONFIG
from recipes.public_stats import refresh_public_stats
from recipes.push_schema import is_valid_single_stage_graph
from recipes.worker import async_process_next_recipe_job, process_next_recipe_job

ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"
SLOT_WINDOW_SECONDS = 1200  # 20-minute trigger window per 09:30 / 12:30 / 15:30 ET slot
POLL_INTERVAL_SECONDS = 5
MAX_JOBS_PER_CYCLE = 25
LIVE_TURN_CONCURRENCY = int(os.environ.get("RECIPE_LIVE_CONCURRENCY", "10"))
# Backtests are no longer pinned to local Strata (they run on the free-llm proxy
# via auto-go), so the lane can hold several jobs. The database enforces the same
# cap in pop_next_recipe_job(), which counts processing backtests under the
# dequeue advisory lock.
# The SQL function is authoritative (c_max_processing_backtests = 3); a larger
# lane value would only spin on the advisory lock, so clamp to it.
BACKTEST_CONCURRENCY = min(3, max(1, int(os.environ.get("RECIPE_BACKTEST_CONCURRENCY", "3"))))


def due_trading_slot(now_dt: datetime, last_slot_key: str | None = None) -> str | None:
    """Return 'YYYY-MM-DDTHH:MM' ET key when now_dt falls inside a 09:30/12:30/15:30 ET slot."""
    dt_et = now_dt.astimezone(EASTERN_TZ) if now_dt.tzinfo else now_dt.replace(tzinfo=UTC).astimezone(EASTERN_TZ)
    if dt_et.weekday() >= 5:
        return None
    day_str = dt_et.date().isoformat()
    for hour_et, minute_et in TRADING_SLOTS_ET:
        slot_start = dt_et.replace(hour=hour_et, minute=minute_et, second=0, microsecond=0)
        delta_sec = (dt_et - slot_start).total_seconds()
        if 0 <= delta_sec < SLOT_WINDOW_SECONDS:
            slot_key = f"{day_str}T{hour_et:02d}:{minute_et:02d}"
            return None if slot_key == last_slot_key else slot_key
    return None


def _collect_recipe_watchlist(sb_client: Any) -> list[str]:
    """Collect held paper tickers from live/public recipes for live slot bar archiving."""
    tickers: set[str] = {"SPY"}
    try:
        res = sb_client.table("strategy_recipes").select("paper_positions").eq("is_live", True).limit(200).execute()
        for row in res.data or []:
            for pos in row.get("paper_positions") or []:
                tkr = str(pos.get("ticker", "")).upper().strip()
                if tkr:
                    tickers.add(tkr)
    except Exception:
        logger.debug("Failed loading recipe watchlist for intraday bar snapshot", exc_info=True)
    return sorted(tickers)


def load_starter_recipes() -> list[dict[str, Any]]:
    """Load canonical starter recipes from packages/config/starter-recipes.json."""
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "packages" / "config" / "starter-recipes.json"
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return list(data)


def seed_starter_recipes(sb_client: Any) -> int:
    """Idempotently seed starter Push v2 templates into strategy_recipes."""
    templates = load_starter_recipes()
    existing_res = sb_client.table("strategy_recipes").select("name").eq("is_template", True).limit(100).execute()
    existing_names = {str(r.get("name", "")) for r in (existing_res.data or [])}

    inserted = 0
    for tmpl in templates:
        name = str(tmpl.get("name", ""))
        if not name or name in existing_names:
            continue
        payload = {
            "user_id": ANONYMOUS_USER_ID,
            "name": name,
            "description": tmpl.get("description", ""),
            "is_public": True,
            "is_template": True,
            "is_live": False,
            "cadence": tmpl.get("cadence", "3h"),
            "graph_json": tmpl,
            "concurrency_config": dict(DEFAULT_CONCURRENCY_CONFIG),
        }
        sb_client.table("strategy_recipes").insert(payload).execute()
        inserted += 1
        logger.info("Seeded starter recipe template: %s", name)
    return inserted


def _is_valid_single_stage_graph(raw_graph: Any) -> bool:
    """True only when graph_json validates as a single-stage Push v2 strategy.

    The scheduler validates with the same schema the worker uses. A row that fails
    validation is skipped here instead of being queued, which would otherwise leave
    a failed queue row behind on every hourly cycle.
    """
    return is_valid_single_stage_graph(raw_graph)


def _canonical_slot_utc(slot_key: str) -> datetime:
    """Convert a 'YYYY-MM-DDTHH:MM' ET slot key to its canonical UTC datetime."""
    naive = datetime.fromisoformat(slot_key)
    return naive.replace(tzinfo=EASTERN_TZ).astimezone(UTC)


LIVE_PAGE_SIZE = 200
OPEN_JOBS_PAGE_SIZE = 500
SKIP_RATIO_ALERT = 0.10


def _record_ops_event(
    sb_client: Any,
    event: str,
    *,
    severity: str = "warning",
    detail: dict[str, Any] | None = None,
) -> None:
    """Persist durable scheduler telemetry so a silent truncation surfaces as data."""
    payload = {"event": event, "severity": severity, "detail": detail or {}}
    try:
        sb_client.table("recipe_ops_events").insert(payload).execute()
    except Exception:
        logger.exception("Failed recording recipe ops event %s", event)
    if severity == "error":
        logger.error("recipe_ops_event %s: %s", event, detail or {})
    else:
        logger.warning("recipe_ops_event %s: %s", event, detail or {})


def _fetch_live_recipes(sb_client: Any) -> list[dict[str, Any]]:
    """Page through every live, non-archived recipe instead of trusting one .limit()."""
    collected: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = (
            sb_client.table("strategy_recipes")
            .select("id, user_id, name, graph_json")
            .eq("is_live", True)
            .is_("archived_at", "null")
            .order("id")
            .range(offset, offset + LIVE_PAGE_SIZE - 1)
            .execute()
        )
        batch = page.data or []
        collected.extend(batch)
        if len(batch) < LIVE_PAGE_SIZE:
            return collected
        offset += LIVE_PAGE_SIZE


def _fetch_open_recipe_ids(sb_client: Any, *, slot_start_utc: datetime | None = None) -> set[str]:
    """Every recipe with an open job (and, when scheduled, one already run this slot)."""
    open_ids: set[str] = set()
    offset = 0
    while True:
        page = (
            sb_client.table("recipe_execution_queue")
            .select("recipe_id")
            .in_("status", ["pending", "processing"])
            .order("id")
            .range(offset, offset + OPEN_JOBS_PAGE_SIZE - 1)
            .execute()
        )
        batch = page.data or []
        open_ids.update(str(r.get("recipe_id")) for r in batch if r.get("recipe_id"))
        if len(batch) < OPEN_JOBS_PAGE_SIZE:
            break
        offset += OPEN_JOBS_PAGE_SIZE

    if slot_start_utc is None:
        return open_ids

    offset = 0
    while True:
        page = (
            sb_client.table("recipe_execution_queue")
            .select("recipe_id")
            .eq("mode", "live_turn")
            .gte("created_at", slot_start_utc.isoformat())
            .order("id")
            .range(offset, offset + OPEN_JOBS_PAGE_SIZE - 1)
            .execute()
        )
        batch = page.data or []
        open_ids.update(str(r.get("recipe_id")) for r in batch if r.get("recipe_id"))
        if len(batch) < OPEN_JOBS_PAGE_SIZE:
            return open_ids
        offset += OPEN_JOBS_PAGE_SIZE


def enqueue_live_recipes_with_stats(sb_client: Any, *, slot_start_utc: datetime | None = None) -> dict[str, int]:
    """Enqueue live_turn jobs and return the counters the scheduler health check needs.

    Recipes the owner removed from My Strategies keep their rows (archived_at is
    set) but must never be turned over again, so the query requires NULL there.

    The previous implementation read at most 500 live recipes with a single
    ``.limit(500)``, so with several live recipes per user the excess was
    silently never scheduled. Everything is paged now, and the counters are
    reconciled against what was seen: an accounting mismatch, or more than 10%
    of live recipes skipped because they already had an open job, is recorded in
    ``recipe_ops_events`` and logged as an error.
    """
    live_recipes = _fetch_live_recipes(sb_client)
    stats = {
        "seen": len(live_recipes),
        "enqueued": 0,
        "skipped_open": 0,
        "skipped_invalid_graph": 0,
    }
    if not live_recipes:
        return stats

    open_ids = _fetch_open_recipe_ids(sb_client, slot_start_utc=slot_start_utc)

    new_jobs: list[dict[str, Any]] = []
    for rec in live_recipes:
        rec_id = str(rec.get("id", ""))
        if not rec_id:
            continue
        if rec_id in open_ids:
            stats["skipped_open"] += 1
            continue
        if not _is_valid_single_stage_graph(rec.get("graph_json")):
            logger.warning(
                "Skipping live recipe %s (%s): graph_json is not a valid single-stage Push v2 strategy",
                rec.get("name"),
                rec_id,
            )
            stats["skipped_invalid_graph"] += 1
            continue
        new_jobs.append(
            {
                "recipe_id": rec_id,
                "user_id": rec.get("user_id") or ANONYMOUS_USER_ID,
                "mode": "live_turn",
                "priority": 1,
                "status": "pending",
                "provider": "free-llm-proxy",
                "model": "auto-go",
                "weeks_requested": [],
                "progress_pct": 0,
            }
        )

    if new_jobs:
        sb_client.table("recipe_execution_queue").insert(new_jobs).execute()
        stats["enqueued"] = len(new_jobs)
        logger.info("Enqueued %d hourly live_turn recipe jobs", len(new_jobs))

    accounted = stats["enqueued"] + stats["skipped_open"] + stats["skipped_invalid_graph"]
    if accounted != stats["seen"]:
        _record_ops_event(
            sb_client,
            "live_enqueue_accounting_mismatch",
            severity="error",
            detail={**stats, "accounted": accounted},
        )
    elif stats["seen"] and (stats["skipped_open"] / stats["seen"]) > SKIP_RATIO_ALERT:
        _record_ops_event(
            sb_client,
            "live_enqueue_high_skip_ratio",
            severity="warning",
            detail={**stats, "skip_ratio": round(stats["skipped_open"] / stats["seen"], 4)},
        )

    return stats


def enqueue_live_recipes(sb_client: Any, *, slot_start_utc: datetime | None = None) -> int:
    """Backward-compatible wrapper returning only the enqueued count."""
    return enqueue_live_recipes_with_stats(sb_client, slot_start_utc=slot_start_utc)["enqueued"]


async def run_hourly_cycle(
    sb_client: Any,
    *,
    as_of_utc: datetime | None = None,
    slot_start_utc: datetime | None = None,
    max_jobs: int = MAX_JOBS_PER_CYCLE,
) -> dict[str, int]:
    """Sync live news, enqueue hourly live recipes, and drain pending queue jobs."""
    news_stats = await sync_live_news_to_corpus(sb_client, as_of_utc=as_of_utc)
    live_enqueued = (
        enqueue_live_recipes(sb_client, slot_start_utc=slot_start_utc)
        if slot_start_utc is not None
        else enqueue_live_recipes(sb_client)
    )
    jobs_processed = 0
    jobs_failed = 0
    for _ in range(max_jobs):
        outcome = await async_process_next_recipe_job(sb_client)
        if outcome == "EMPTY":
            break
        if outcome == "COMPLETED":
            jobs_processed += 1
        else:
            jobs_failed += 1
    public_stats = refresh_public_stats(sb_client)
    return {
        "news_synced": int(news_stats.get("inserted", 0)),
        "live_enqueued": live_enqueued,
        "jobs_processed": jobs_processed,
        "jobs_failed": jobs_failed,
        "public_stats_rows": int(public_stats.get("rows_written", 0)),
    }


async def drain_lane(
    sb_client: Any,
    *,
    mode: str,
    max_jobs: int = MAX_JOBS_PER_CYCLE,
    concurrency: int | None = None,
) -> int:
    """Drain queued jobs for a single execution lane (live_turn or backtest).

    Jobs are processed serially by default so callers that do not care about
    concurrency (tests, one-off drains) never fan out accidentally. The daemon
    passes ``concurrency=LIVE_TURN_CONCURRENCY`` for the live_turn lane and
    ``BACKTEST_CONCURRENCY`` for the backtest lane so many users' jobs run in
    parallel behind a bounded semaphore, matching the database-side cap.
    """
    if concurrency is None:
        concurrency = BACKTEST_CONCURRENCY if mode == "backtest" else 1

    if concurrency <= 1:
        processed = 0
        for _ in range(max_jobs):
            outcome = await async_process_next_recipe_job(sb_client, target_mode=mode)
            if outcome == "EMPTY":
                break
            if outcome == "COMPLETED":
                processed += 1
        return processed

    semaphore = asyncio.Semaphore(concurrency)

    async def _process_one() -> str:
        async with semaphore:
            return await async_process_next_recipe_job(sb_client, target_mode=mode)

    tasks = [_process_one() for _ in range(max_jobs)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = 0
    for r in results:
        if isinstance(r, Exception):
            logger.exception("Live turn drain task failed: %s", r)
        elif r == "COMPLETED":
            processed += 1
    return processed


def _drain_sync_queue(sb_client: Any, max_jobs: int = MAX_JOBS_PER_CYCLE) -> None:
    """Drain queued jobs sequentially from the sync poll loop without stalling on failures."""
    for _ in range(max_jobs):
        outcome = process_next_recipe_job(sb_client)
        if outcome == "EMPTY":
            break


async def run_scheduled_slot(sb_client: Any, slot_key: str, now_utc: datetime) -> dict[str, int]:
    """One 09:30/12:30/15:30 ET cycle: news, enqueue, drain, bars, public stats.

    Extracted from ``_live_lane_loop`` so the deployed daemon path is testable —
    the board used to be materialised only on the ``--once`` path.
    """
    slot_dt_utc = _canonical_slot_utc(slot_key)
    news_stats = await sync_live_news_to_corpus(sb_client, as_of_utc=now_utc)
    live_enqueued = enqueue_live_recipes(sb_client, slot_start_utc=slot_dt_utc)
    live_done = await drain_lane(sb_client, mode="live_turn", concurrency=LIVE_TURN_CONCURRENCY)
    snapped = await snapshot_live_intraday_bars(sb_client, _collect_recipe_watchlist(sb_client), slot_dt_utc)
    logger.info(
        "Scheduled ET slot %s live cycle complete: news=%s enqueued=%d done=%d bars_snapped=%d",
        slot_key,
        news_stats,
        live_enqueued,
        live_done,
        snapped,
    )
    try:
        refresh_public_stats(sb_client)
    except Exception:
        logger.exception("Public stats refresh failed for slot %s", slot_key)
    return {
        "live_enqueued": live_enqueued,
        "live_done": live_done,
        "bars_snapped": snapped,
    }


async def _live_lane_loop(sb_client: Any) -> None:
    """Run scheduled 3x/day ET cycles and non-blocking live_turn jobs on clvg.uk auto-go."""
    last_slot_key: str | None = None
    while True:
        now_utc = datetime.now(UTC)
        slot_key = due_trading_slot(now_utc, last_slot_key)
        if slot_key is not None:
            try:
                await run_scheduled_slot(sb_client, slot_key, now_utc)
            except Exception:
                logger.exception("Scheduled ET slot %s live cycle failed", slot_key)
            last_slot_key = slot_key
        else:
            try:
                await drain_lane(sb_client, mode="live_turn")
            except Exception:
                logger.exception("Live turn lane iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _backtest_lane_loop(sb_client: Any) -> None:
    """Drain up to BACKTEST_CONCURRENCY backtests without blocking live_turn jobs."""
    while True:
        try:
            await drain_lane(sb_client, mode="backtest", max_jobs=BACKTEST_CONCURRENCY)
        except Exception:
            logger.exception("Backtest lane iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _async_daemon_loop(sb_client: Any) -> None:
    await asyncio.gather(_live_lane_loop(sb_client), _backtest_lane_loop(sb_client))


def _run_daemon_loop(sb_client: Any) -> None:
    """Run dual-lane 3x/day ET scheduler + live_turn lane concurrently with strict 1x backtest lane."""
    try:
        seed_starter_recipes(sb_client)
    except Exception:
        logger.exception("Failed seeding starter recipes during worker startup; continuing loop")

    asyncio.run(_async_daemon_loop(sb_client))


def main() -> int:
    parser = argparse.ArgumentParser(description="Recipe Studio hourly scheduler & queue worker")
    parser.add_argument("--loop", action="store_true", help="Run continuous hourly scheduler + queue poller")
    parser.add_argument("--once", action="store_true", help="Run one hourly sync, enqueue, and queue drain cycle")
    parser.add_argument("--seed-only", action="store_true", help="Seed starter templates into strategy_recipes")
    parser.add_argument("--sync-news-only", action="store_true", help="Sync live news into recipe_news_corpus")
    args = parser.parse_args()

    sb = get_supabase_client()
    if args.seed_only:
        count = seed_starter_recipes(sb)
        logger.info("Seeded %d starter templates.", count)
        return 0
    if args.sync_news_only:
        stats = asyncio.run(sync_live_news_to_corpus(sb))
        logger.info("News sync complete: %s", stats)
        return 0
    if args.loop:
        _run_daemon_loop(sb)
        return 0

    # Default action and --once both execute a single sync + enqueue + drain pass.
    if args.once:
        logger.debug("Running explicit single-shot recipe cycle (--once)")
    try:
        seed_starter_recipes(sb)
    except Exception:
        logger.exception("Failed seeding starter recipes prior to single run")
    stats = asyncio.run(run_hourly_cycle(sb))
    logger.info("Recipe cycle complete: %s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
