"""Hourly scheduler & queue worker daemon for Strategy Recipes (MiniPC runner)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from core.config import logger
from core.db import get_supabase_client
from core.time_utils import EASTERN_TZ
from recipes.intraday_bars import TRADING_SLOTS_ET, snapshot_live_intraday_bars
from recipes.news_corpus import sync_live_news_to_corpus
from recipes.portfolio_engine import DEFAULT_CONCURRENCY_CONFIG
from recipes.push_schema import PushStrategy
from recipes.worker import async_process_next_recipe_job, process_next_recipe_job

ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"
SLOT_WINDOW_SECONDS = 1200  # 20-minute trigger window per 09:30 / 12:30 / 15:30 ET slot
POLL_INTERVAL_SECONDS = 5
MAX_JOBS_PER_CYCLE = 25


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
    if isinstance(raw_graph, str):
        try:
            raw_graph = json.loads(raw_graph)
        except json.JSONDecodeError:
            return False
    if not isinstance(raw_graph, dict):
        return False
    try:
        PushStrategy.model_validate(raw_graph)
    except ValidationError:
        return False
    return True


def _canonical_slot_utc(slot_key: str) -> datetime:
    """Convert a 'YYYY-MM-DDTHH:MM' ET slot key to its canonical UTC datetime."""
    naive = datetime.fromisoformat(slot_key)
    return naive.replace(tzinfo=EASTERN_TZ).astimezone(UTC)


def enqueue_live_recipes(sb_client: Any, *, slot_start_utc: datetime | None = None) -> int:
    """Enqueue live_turn jobs for active Push v2 is_live recipes without an open or same-slot job."""
    live_res = (
        sb_client.table("strategy_recipes")
        .select("id, user_id, name, graph_json")
        .eq("is_live", True)
        .limit(500)
        .execute()
    )
    live_recipes = live_res.data or []
    if not live_recipes:
        return 0

    open_res = (
        sb_client.table("recipe_execution_queue")
        .select("recipe_id")
        .in_("status", ["pending", "processing"])
        .limit(1000)
        .execute()
    )
    open_ids = {str(r.get("recipe_id")) for r in (open_res.data or [])}

    if slot_start_utc is not None:
        slot_res = (
            sb_client.table("recipe_execution_queue")
            .select("recipe_id")
            .eq("mode", "live_turn")
            .gte("created_at", slot_start_utc.isoformat())
            .limit(1000)
            .execute()
        )
        open_ids.update(str(r.get("recipe_id")) for r in (slot_res.data or []))

    new_jobs: list[dict[str, Any]] = []
    for rec in live_recipes:
        rec_id = str(rec.get("id", ""))
        if not rec_id or rec_id in open_ids:
            continue
        if not _is_valid_single_stage_graph(rec.get("graph_json")):
            logger.warning(
                "Skipping live recipe %s (%s): graph_json is not a valid single-stage Push v2 strategy",
                rec.get("name"),
                rec_id,
            )
            continue
        new_jobs.append(
            {
                "recipe_id": rec_id,
                "user_id": rec.get("user_id") or ANONYMOUS_USER_ID,
                "mode": "live_turn",
                "priority": 1,
                "status": "pending",
                "provider": "auto-strata",
                "model": "strata",
                "weeks_requested": [],
                "progress_pct": 0,
            }
        )

    if not new_jobs:
        return 0

    sb_client.table("recipe_execution_queue").insert(new_jobs).execute()
    logger.info("Enqueued %d hourly live_turn recipe jobs", len(new_jobs))
    return len(new_jobs)


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
    return {
        "news_synced": int(news_stats.get("inserted", 0)),
        "live_enqueued": live_enqueued,
        "jobs_processed": jobs_processed,
        "jobs_failed": jobs_failed,
    }


def _drain_sync_queue(sb_client: Any, max_jobs: int = MAX_JOBS_PER_CYCLE) -> None:
    """Drain queued jobs sequentially from the sync poll loop without stalling on failures."""
    for _ in range(max_jobs):
        outcome = process_next_recipe_job(sb_client)
        if outcome == "EMPTY":
            break


def _run_daemon_loop(sb_client: Any) -> None:
    """Run 3x/day ET (09:30, 12:30, 15:30) recipe cycles while draining queued jobs every 5s."""
    try:
        seed_starter_recipes(sb_client)
    except Exception:
        logger.exception("Failed seeding starter recipes during worker startup; continuing loop")

    last_slot_key: str | None = None
    while True:
        now_utc = datetime.now(UTC)
        slot_key = due_trading_slot(now_utc, last_slot_key)
        if slot_key is not None:
            slot_dt_utc = _canonical_slot_utc(slot_key)
            try:
                stats = asyncio.run(run_hourly_cycle(sb_client, as_of_utc=now_utc, slot_start_utc=slot_dt_utc))
                snapped = asyncio.run(
                    snapshot_live_intraday_bars(sb_client, _collect_recipe_watchlist(sb_client), slot_dt_utc)
                )
                logger.info("Scheduled ET slot %s cycle complete: %s (bars_snapped=%d)", slot_key, stats, snapped)
            except Exception:
                logger.exception("Scheduled ET slot %s recipe cycle failed", slot_key)
            last_slot_key = slot_key
        else:
            _drain_sync_queue(sb_client)

        time.sleep(POLL_INTERVAL_SECONDS)


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
