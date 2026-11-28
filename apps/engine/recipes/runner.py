"""30-minute market-hours scheduler, 5-minute Turbo mode, & queue worker daemon."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from core.config import logger
from core.db import get_supabase_client
from core.time_utils import EASTERN_TZ
from recipes.intraday_bars import snapshot_live_intraday_bars
from recipes.news_corpus import sync_live_news_to_corpus
from recipes.portfolio_engine import DEFAULT_CONCURRENCY_CONFIG
from recipes.public_stats import refresh_public_stats
from recipes.push_schema import is_valid_single_stage_graph
from recipes.worker import (
    async_process_next_recipe_job,
    fail_stale_compile_jobs,
    process_next_recipe_job,
)
from trading.market_calendar import get_market_calendar, is_known_us_market_holiday

ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"
LIVE_SLOTS_ET: tuple[tuple[int, int], ...] = (
    (9, 30),
    (10, 0),
    (10, 30),
    (11, 0),
    (11, 30),
    (12, 0),
    (12, 30),
    (13, 0),
    (13, 30),
    (14, 0),
    (14, 30),
    (15, 0),
    (15, 30),
    (16, 0),
)
SLOT_WINDOW_SECONDS = 1200  # 20-minute trigger window per 30-minute ET slot (09:30..16:00)
TURBO_INTERVAL_SECONDS = 300  # 5-minute cadence while Turbo is active
TURBO_POLL_INTERVAL_SECONDS = 30  # Poll active Turbo bots at most once every 30s
NEWS_SYNC_MIN_INTERVAL_SECONDS = 300
PUBLIC_STATS_MIN_INTERVAL_SECONDS = 60
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
COMPILE_CONCURRENCY = max(1, int(os.environ.get("RECIPE_COMPILE_CONCURRENCY", "3")))
STALE_COMPILE_SWEEP_INTERVAL_SECONDS = 60


def _to_et(now_dt: datetime) -> datetime:
    return now_dt.astimezone(EASTERN_TZ) if now_dt.tzinfo else now_dt.replace(tzinfo=UTC).astimezone(EASTERN_TZ)


def _is_us_holiday_fallback(day_et: date) -> bool:
    """Holiday check delegated to the single session implementation."""
    return is_known_us_market_holiday(day_et)


def is_us_market_hours_et(now_dt: datetime) -> bool:
    """True inside the real session (holidays and 13:00 half-day closes included)."""
    return get_market_calendar().is_open(_to_et(now_dt))


def due_trading_slot(now_dt: datetime, last_slot_key: str | None = None) -> str | None:
    """Return 'YYYY-MM-DDTHH:MM' ET key when now_dt falls inside a 30-min market slot (09:30-close ET).

    The slot grid is fixed at 30 minutes, but the last slot follows the real
    session close: on a 13:00 half day no slot after 13:00 ET is ever due.
    """
    dt_et = _to_et(now_dt)
    if dt_et.weekday() >= 5 or _is_us_holiday_fallback(dt_et.date()):
        return None
    session = get_market_calendar().session_for(dt_et.date())
    if session is None:
        return None
    close_et = session[1]
    day_str = dt_et.date().isoformat()
    for hour_et, minute_et in LIVE_SLOTS_ET:
        slot_start = dt_et.replace(hour=hour_et, minute=minute_et, second=0, microsecond=0)
        if slot_start > close_et:
            return None
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


def _insert_live_jobs_idempotent(sb_client: Any, new_jobs: list[dict[str, Any]]) -> int:
    """Insert live_turn jobs, tolerating 23505 unique-index conflicts under replica lag."""
    if not new_jobs:
        return 0
    try:
        sb_client.table("recipe_execution_queue").insert(new_jobs).execute()
        return len(new_jobs)
    except Exception as exc:
        if "23505" not in str(exc) and "duplicate key" not in str(exc).lower():
            raise
        inserted = 0
        for job in new_jobs:
            try:
                sb_client.table("recipe_execution_queue").insert(job).execute()
                inserted += 1
            except Exception as row_exc:
                if "23505" in str(row_exc) or "duplicate key" in str(row_exc).lower():
                    logger.debug("Skipped duplicate open live_turn for recipe %s", job.get("recipe_id"))
                    continue
                raise
        return inserted


def enqueue_live_recipes_with_stats(
    sb_client: Any,
    *,
    slot_start_utc: datetime | None = None,
    recent_turbo_cutoff_utc: datetime | None = None,
) -> dict[str, int]:
    """Enqueue live_turn jobs and return the counters the scheduler health check needs.

    Recipes the owner removed from My Strategies keep their rows (archived_at is
    set) but must never be turned over again, so the query requires NULL there.

    ``recent_turbo_cutoff_utc`` prevents double-firing bots that ran a 5m Turbo
    turn immediately prior to a 30m slot without inflating ``skipped_open`` ops
    alerts.
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
    recent_turbo_ids: set[str] = set()
    if recent_turbo_cutoff_utc is not None and (slot_start_utc is None or recent_turbo_cutoff_utc < slot_start_utc):
        recent_turbo_ids = _fetch_open_recipe_ids(sb_client, slot_start_utc=recent_turbo_cutoff_utc) - open_ids

    new_jobs: list[dict[str, Any]] = []
    skipped_recent_turbo = 0
    for rec in live_recipes:
        rec_id = str(rec.get("id", ""))
        if not rec_id:
            continue
        if rec_id in open_ids:
            stats["skipped_open"] += 1
            continue
        if rec_id in recent_turbo_ids:
            skipped_recent_turbo += 1
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
        stats["enqueued"] = _insert_live_jobs_idempotent(sb_client, new_jobs)
        logger.info("Enqueued %d scheduled live_turn recipe jobs", stats["enqueued"])

    accounted = stats["enqueued"] + stats["skipped_open"] + skipped_recent_turbo + stats["skipped_invalid_graph"]
    if accounted != stats["seen"]:
        _record_ops_event(
            sb_client,
            "live_enqueue_accounting_mismatch",
            severity="error",
            detail={**stats, "skipped_recent_turbo": skipped_recent_turbo, "accounted": accounted},
        )
    elif stats["seen"] and (stats["skipped_open"] / stats["seen"]) > SKIP_RATIO_ALERT:
        _record_ops_event(
            sb_client,
            "live_enqueue_high_skip_ratio",
            severity="warning",
            detail={**stats, "skip_ratio": round(stats["skipped_open"] / stats["seen"], 4)},
        )

    return stats


def enqueue_live_recipes(
    sb_client: Any,
    *,
    slot_start_utc: datetime | None = None,
    recent_turbo_cutoff_utc: datetime | None = None,
) -> int:
    """Backward-compatible wrapper returning only the enqueued count."""
    return enqueue_live_recipes_with_stats(
        sb_client,
        slot_start_utc=slot_start_utc,
        recent_turbo_cutoff_utc=recent_turbo_cutoff_utc,
    )["enqueued"]


def _fetch_active_turbo_recipes(sb_client: Any, now_utc: datetime) -> list[dict[str, Any]]:
    """Fetch live, non-archived recipes with an unexpired Turbo window."""
    collected: list[dict[str, Any]] = []
    offset = 0
    now_iso = now_utc.isoformat()
    while True:
        page = (
            sb_client.table("strategy_recipes")
            .select("id, user_id, name, graph_json, turbo_expires_at")
            .eq("is_live", True)
            .is_("archived_at", "null")
            .gt("turbo_expires_at", now_iso)
            .order("id")
            .range(offset, offset + LIVE_PAGE_SIZE - 1)
            .execute()
        )
        batch = page.data or []
        collected.extend(batch)
        if len(batch) < LIVE_PAGE_SIZE:
            return collected
        offset += LIVE_PAGE_SIZE


def enqueue_turbo_recipes(sb_client: Any, *, now_utc: datetime | None = None) -> int:
    """Enqueue 5-minute live_turn jobs for bots with an active Turbo window during market hours."""
    current_utc = now_utc or datetime.now(UTC)
    if not is_us_market_hours_et(current_utc):
        return 0

    turbo_recipes = _fetch_active_turbo_recipes(sb_client, current_utc)
    if not turbo_recipes:
        return 0

    cutoff_utc = current_utc - timedelta(seconds=TURBO_INTERVAL_SECONDS)
    skip_ids = _fetch_open_recipe_ids(sb_client, slot_start_utc=cutoff_utc)

    new_jobs: list[dict[str, Any]] = []
    for rec in turbo_recipes:
        rec_id = str(rec.get("id", ""))
        if not rec_id or rec_id in skip_ids:
            continue
        if not _is_valid_single_stage_graph(rec.get("graph_json")):
            logger.warning("Skipping turbo recipe %s (%s): invalid Push v2 graph", rec.get("name"), rec_id)
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
        inserted = _insert_live_jobs_idempotent(sb_client, new_jobs)
        logger.info("Enqueued %d turbo (5m) live_turn recipe jobs", inserted)
        return inserted
    return 0


def expire_live_bots(sb_client: Any) -> int:
    """Pause bots whose token-funded week lapsed.

    Idempotent and transactional server-side; safe to run every cycle. A failure
    here must not abort the rest of the cycle, so it logs and returns 0.
    """
    try:
        res = sb_client.rpc("expire_live_bots", {}).execute()
        return int(res.data or 0)
    except Exception:
        logger.exception("Live expiry sweep failed; bots stay live until the next cycle")
        return 0


def refill_weekly_tokens(sb_client: Any) -> int:
    """Top every account up for the current ET week.

    The ledger is the user list: anyone who has ever loaded the app has a
    balance row, so no auth.users scan is needed. Idempotent server-side — a
    second call inside the same week returns 0 — which is what makes it safe to
    run every cycle and on both workers. A failure here must not abort the rest
    of the cycle: the on-load refill still covers anyone who visits.
    """
    try:
        res = sb_client.rpc("refill_all_accounts", {}).execute()
        return int(res.data or 0)
    except Exception:
        logger.exception("Weekly token refill failed; visitors still refill on load")
        return 0


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
    refills_applied = refill_weekly_tokens(sb_client)
    expired_live = expire_live_bots(sb_client)
    return {
        "news_synced": int(news_stats.get("inserted", 0)),
        "live_enqueued": live_enqueued,
        "jobs_processed": jobs_processed,
        "jobs_failed": jobs_failed,
        "public_stats_rows": int(public_stats.get("rows_written", 0)),
        "refills_applied": refills_applied,
        "expired_live": expired_live,
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


@dataclass
class LiveLaneState:
    last_slot_key: str | None = None
    last_news_sync_utc: datetime | None = None
    last_turbo_poll_utc: datetime | None = None
    last_stats_refresh_utc: datetime | None = None


async def _is_trading_day_et(now_utc: datetime) -> bool:
    """Check FMP + fallback US holiday calendar for the current ET date."""
    dt_et = _to_et(now_utc)
    if dt_et.weekday() >= 5 or _is_us_holiday_fallback(dt_et.date()):
        return False
    try:
        return await asyncio.to_thread(get_market_calendar().is_session_day, dt_et.date())
    except Exception:
        logger.debug("MarketCalendar trading-day lookup failed; using fallback", exc_info=True)
        return True


async def run_scheduled_slot(sb_client: Any, slot_key: str, now_utc: datetime) -> dict[str, int]:
    """One 30-min ET market slot (09:30..16:00): news, enqueue, drain, bars, public stats."""
    slot_dt_utc = _canonical_slot_utc(slot_key)
    recent_turbo_cutoff = now_utc - timedelta(seconds=TURBO_INTERVAL_SECONDS)
    news_stats = await sync_live_news_to_corpus(sb_client, as_of_utc=now_utc)
    live_enqueued = enqueue_live_recipes(
        sb_client,
        slot_start_utc=slot_dt_utc,
        recent_turbo_cutoff_utc=recent_turbo_cutoff,
    )
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


def _elapsed_at_least(prev: datetime | None, now_utc: datetime, seconds: int) -> bool:
    return prev is None or (now_utc - prev).total_seconds() >= seconds


async def run_live_lane_tick(
    sb_client: Any,
    now_utc: datetime,
    state: LiveLaneState,
) -> LiveLaneState:
    """Execute one poll tick of the live lane: 30m slot, throttled 5m Turbo, or drain."""
    slot_key = due_trading_slot(now_utc, state.last_slot_key)
    if slot_key is not None:
        if not await _is_trading_day_et(now_utc):
            state.last_slot_key = slot_key
            return state
        try:
            await run_scheduled_slot(sb_client, slot_key, now_utc)
            state.last_slot_key = slot_key
            state.last_news_sync_utc = now_utc
            state.last_stats_refresh_utc = now_utc
        except Exception:
            logger.exception("Scheduled ET slot %s live cycle failed; will retry next tick", slot_key)
        return state

    try:
        if (
            is_us_market_hours_et(now_utc)
            and _elapsed_at_least(state.last_turbo_poll_utc, now_utc, TURBO_POLL_INTERVAL_SECONDS)
            and await _is_trading_day_et(now_utc)
        ):
            state.last_turbo_poll_utc = now_utc
            turbo_enqueued = enqueue_turbo_recipes(sb_client, now_utc=now_utc)
            if turbo_enqueued > 0 and _elapsed_at_least(
                state.last_news_sync_utc, now_utc, NEWS_SYNC_MIN_INTERVAL_SECONDS
            ):
                await sync_live_news_to_corpus(sb_client, as_of_utc=now_utc)
                state.last_news_sync_utc = now_utc

        live_done = await drain_lane(sb_client, mode="live_turn", concurrency=LIVE_TURN_CONCURRENCY)
        if live_done > 0 and _elapsed_at_least(
            state.last_stats_refresh_utc, now_utc, PUBLIC_STATS_MIN_INTERVAL_SECONDS
        ):
            try:
                refresh_public_stats(sb_client)
                state.last_stats_refresh_utc = now_utc
            except Exception:
                logger.exception("Public stats refresh failed after turbo/live drain")
    except Exception:
        logger.exception("Live turn lane iteration failed")

    return state


async def _live_lane_loop(sb_client: Any) -> None:
    """Run scheduled 30m ET market cycles, 5m Turbo ticks, and immediate live_turn jobs."""
    state = LiveLaneState()
    while True:
        await run_live_lane_tick(sb_client, datetime.now(UTC), state)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _backtest_lane_loop(sb_client: Any) -> None:
    """Drain up to BACKTEST_CONCURRENCY backtests without blocking live_turn jobs."""
    while True:
        try:
            await drain_lane(sb_client, mode="backtest", max_jobs=BACKTEST_CONCURRENCY)
        except Exception:
            logger.exception("Backtest lane iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _compile_lane_loop(sb_client: Any) -> None:
    """Drain /build compile jobs on their own lane so a backtest never delays one.

    A compile is interactive: the user is staring at the builder while it runs, so
    it gets a bounded semaphore of its own rather than queueing behind backtests.
    Once a minute it also fails compile rows no worker ever claimed, so a job that
    outlived the daemon cannot hold a user's 2-pending cap hostage.
    """
    last_sweep_utc: datetime | None = None
    while True:
        try:
            now_utc = datetime.now(UTC)
            if (
                last_sweep_utc is None
                or (now_utc - last_sweep_utc).total_seconds() >= STALE_COMPILE_SWEEP_INTERVAL_SECONDS
            ):
                last_sweep_utc = now_utc
                try:
                    stale = fail_stale_compile_jobs(sb_client)
                    if stale:
                        logger.warning("Failed %d stale compile job(s) no worker claimed", stale)
                except Exception:
                    logger.exception("Stale compile sweep failed")

            processed = await drain_lane(
                sb_client, mode="compile", max_jobs=COMPILE_CONCURRENCY, concurrency=COMPILE_CONCURRENCY
            )
            if processed == 0:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except Exception:
            logger.exception("Compile lane iteration failed")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _async_daemon_loop(sb_client: Any) -> None:
    await asyncio.gather(
        _live_lane_loop(sb_client),
        _backtest_lane_loop(sb_client),
        _compile_lane_loop(sb_client),
    )


def _run_daemon_loop(sb_client: Any) -> None:
    """Run dual-lane 30m ET + 5m Turbo live scheduler concurrently with backtest lane."""
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
