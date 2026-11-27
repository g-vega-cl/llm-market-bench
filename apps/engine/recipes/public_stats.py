"""Materialised public leaderboard rows for the recipe homepage.

The web layer is presentation-only (repo mandate), so the runner writes one
``recipe_public_stats`` row per live recipe each cycle: return since inception,
the SPY return over the same equity window, trade counts and the last executed
action. The homepage then reads a keyed table instead of parsing the JSONB
``paper_equity_curve`` in the browser.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, date, datetime, timedelta
from typing import Any

from core.config import logger

DEFAULT_SPY_TICKER = "SPY"
MAX_REASON_CHARS = 220
MAX_FEED_ROWS = 24
MAX_FEED_SIGNALS_PER_RUN = 3
LEADERBOARD_WINDOWS = (7, 30, 90, 0)
ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"


def _date_of(value: Any) -> str | None:
    """Extract the ISO date prefix from an equity-curve label like '2026-11-14 09:30 ET'."""
    text = str(value or "").strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        candidate = text[:10]
        try:
            date.fromisoformat(candidate)
        except ValueError:
            return None
        return candidate
    return None


def parse_equity_curve(curve: Any) -> list[tuple[str, float]]:
    """Return ``[(iso_date, equity)]`` for every readable point, preserving order."""
    points: list[tuple[str, float]] = []
    if not isinstance(curve, list):
        return points
    for entry in curve:
        if not isinstance(entry, dict):
            continue
        when = _date_of(entry.get("time"))
        raw_equity = entry.get("equity")
        if raw_equity is None:
            continue
        try:
            equity = float(raw_equity)
        except (TypeError, ValueError):
            continue
        if when is None or equity < 0:
            continue
        points.append((when, equity))
    return points


def return_pct(curve: Any) -> float | None:
    """Percent return from the first to the last equity point (None for a flat/empty curve)."""
    points = parse_equity_curve(curve)
    if len(points) < 2:
        return None
    first = points[0][1]
    last = points[-1][1]
    if first == 0:
        return None
    return round(((last - first) / first) * 100.0, 4)


def _price_rows(rows: Any) -> list[tuple[str, float]]:
    parsed: list[tuple[str, float]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        when = _date_of(row.get("fetched_at"))
        raw_price = row.get("price")
        if raw_price is None:
            continue
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue
        if when is None or price <= 0:
            continue
        parsed.append((when, price))
    parsed.sort(key=lambda item: item[0])
    return parsed


def _close_on_or_before(rows: list[tuple[str, float]], target: str) -> float | None:
    close: float | None = None
    for when, price in rows:
        if when > target:
            break
        close = price
    return close


def spy_return_pct(spy_rows: Any, first_date: str | None, last_date: str | None) -> float | None:
    """SPY percent return over the same window as the recipe's equity curve."""
    if not first_date or not last_date or last_date <= first_date:
        return None
    rows = _price_rows(spy_rows)
    start = _close_on_or_before(rows, first_date)
    end = _close_on_or_before(rows, last_date)
    if not start or not end or start <= 0:
        return None
    return round(((end - start) / start) * 100.0, 4)


def _reason_from_output(output: Any) -> str | None:
    text = " ".join(str(output or "").split())
    if not text:
        return None
    return text[:MAX_REASON_CHARS]


def build_last_action(job_result: Any) -> dict[str, Any]:
    """Summarise the most recent executed signal for the board's reason line."""
    if not isinstance(job_result, dict):
        return {}
    signals = job_result.get("executed_signals")
    if not isinstance(signals, list) or not signals:
        return {}
    signal = next((s for s in signals if isinstance(s, dict) and s.get("ticker")), None)
    if signal is None:
        return {}
    action: dict[str, Any] = {
        "action": str(signal.get("action") or "").upper(),
        "ticker": str(signal.get("ticker") or "").upper(),
    }
    raw_price = signal.get("price")
    if raw_price is not None:
        with contextlib.suppress(TypeError, ValueError):
            action["price"] = round(float(raw_price), 4)
    reason = _reason_from_output(job_result.get("output"))
    if reason:
        action["reason"] = reason
    return action


def build_public_stats(
    recipe: dict[str, Any],
    *,
    spy_rows: Any = None,
    last_job_result: Any = None,
    last_run_at: str | None = None,
    runs_today: int = 0,
    resolved_model: str | None = None,
) -> dict[str, Any]:
    """Pure builder for one ``recipe_public_stats`` row."""
    curve = recipe.get("paper_equity_curve") or []
    points = parse_equity_curve(curve)
    first_date = points[0][0] if points else None
    last_date = points[-1][0] if points else None
    trades = recipe.get("paper_trades") or []
    positions = recipe.get("paper_positions") or []
    return {
        "recipe_id": str(recipe.get("id")),
        "name": str(recipe.get("name") or "Untitled Strategy"),
        "is_live": bool(recipe.get("is_live")),
        "return_pct": return_pct(curve),
        "spy_return_pct": spy_return_pct(spy_rows, first_date, last_date),
        "trade_count": len(trades) if isinstance(trades, list) else 0,
        "open_positions": len(positions) if isinstance(positions, list) else 0,
        "runs_today": int(runs_today or 0),
        "first_equity_date": first_date,
        "last_equity_date": last_date,
        "last_run_at": last_run_at or recipe.get("updated_at"),
        "last_action": build_last_action(last_job_result),
        "resolved_model": resolved_model or recipe.get("resolved_model"),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return round(ordered[mid], 4)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 4)


def build_desk_summary(stats_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Homepage header counts, computed once by the runner instead of per request."""
    returns = [float(r["return_pct"]) for r in stats_rows if r.get("return_pct") is not None]
    beat_spy = sum(
        1
        for r in stats_rows
        if r.get("return_pct") is not None
        and r.get("spy_return_pct") is not None
        and float(r["return_pct"]) > float(r["spy_return_pct"])
    )
    return {
        "id": 1,
        "live_count": len(stats_rows),
        "beat_spy_count": beat_spy,
        "median_return_pct": median(returns),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def build_feed_rows(recipe_names: dict[str, str], last_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Same-day executed-signal tape, derived from results the runner already holds."""
    rows: list[dict[str, Any]] = []
    for recipe_id, result in last_results.items():
        name = recipe_names.get(recipe_id)
        at = result.get("_created_at")
        signals = result.get("executed_signals")
        if not name or not at or not isinstance(signals, list):
            continue
        for signal in signals[:MAX_FEED_SIGNALS_PER_RUN]:
            if not isinstance(signal, dict):
                continue
            ticker = str(signal.get("ticker") or "").upper()
            action = str(signal.get("action") or "").upper()
            if not ticker or not action:
                continue
            rows.append(
                {
                    "recipe_id": recipe_id,
                    "recipe_name": name,
                    "action": action,
                    "ticker": ticker,
                    "at": at,
                }
            )
    rows.sort(key=lambda row: str(row["at"]), reverse=True)
    return rows[:MAX_FEED_ROWS]


def _write_desk_materialisations(
    sb_client: Any, stats_rows: list[dict[str, Any]], last_results: dict[str, dict[str, Any]]
) -> None:
    """Persist the header and tape; the web layer only ever reads these tables."""
    try:
        sb_client.table("recipe_desk_summary").upsert(build_desk_summary(stats_rows), on_conflict="id").execute()
    except Exception:
        logger.exception("Failed upserting recipe desk summary")

    try:
        sb_client.table("recipe_desk_feed").delete().gte("id", 0).execute()
        names = {str(row["recipe_id"]): str(row["name"]) for row in stats_rows}
        feed = build_feed_rows(names, last_results)
        if feed:
            sb_client.table("recipe_desk_feed").insert(feed).execute()
    except Exception:
        logger.exception("Failed rewriting recipe desk feed")


def _fetch_live_recipes(sb_client: Any, page_size: int = 200) -> list[dict[str, Any]]:
    """Page through every live, non-archived recipe instead of trusting one .limit()."""
    collected: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = (
            sb_client.table("strategy_recipes")
            .select("id, name, is_live, paper_cash, paper_trades, paper_positions, paper_equity_curve, updated_at")
            .eq("is_live", True)
            .is_("archived_at", "null")
            .order("updated_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = page.data or []
        collected.extend(rows)
        if len(rows) < page_size:
            return collected
        offset += page_size


def _fetch_spy_rows(sb_client: Any, first_date: str, last_date: str, ticker: str) -> list[dict]:
    try:
        lookback = (date.fromisoformat(first_date) - timedelta(days=7)).isoformat()
        start = f"{lookback}T00:00:00+00:00"
        end = (date.fromisoformat(last_date) + timedelta(days=1)).isoformat()
        res = (
            sb_client.table("price_history")
            .select("ticker, price, fetched_at")
            .eq("ticker", ticker)
            .gte("fetched_at", start)
            .lt("fetched_at", f"{end}T00:00:00+00:00")
            .order("fetched_at", desc=False)
            .range(0, 499)
            .execute()
        )
        return res.data or []
    except Exception:
        logger.exception("Failed fetching %s price rows for recipe public stats", ticker)
        return []


def _fetch_last_results(sb_client: Any, recipe_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Most recent completed live_turn result per recipe, paginated past 500 rows."""
    if not recipe_ids:
        return {}
    target_count = len(set(recipe_ids))
    latest: dict[str, dict[str, Any]] = {}
    page_size = 500
    offset = 0
    for _ in range(10):
        try:
            res = (
                sb_client.table("recipe_execution_queue")
                .select("recipe_id, result_json, created_at")
                .eq("mode", "live_turn")
                .eq("status", "completed")
                .in_("recipe_id", recipe_ids)
                .order("created_at", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            )
        except Exception:
            logger.exception("Failed fetching recent live_turn results for public stats")
            return latest
        rows = res.data or []
        for row in rows:
            rid = str(row.get("recipe_id"))
            if rid and rid not in latest:
                result = row.get("result_json")
                entry = dict(result) if isinstance(result, dict) else {}
                entry["_created_at"] = row.get("created_at")
                latest[rid] = entry
        if len(latest) >= target_count or len(rows) < page_size:
            return latest
        offset += page_size
    return latest


def _count_runs_today(sb_client: Any, recipe_ids: list[str]) -> dict[str, int]:
    """Count completed live_turn runs today UTC without 2,000-row silent truncation."""
    if not recipe_ids:
        return {}
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    counts: dict[str, int] = {}
    page_size = 1000
    offset = 0
    while True:
        try:
            res = (
                sb_client.table("recipe_execution_queue")
                .select("recipe_id, created_at")
                .eq("mode", "live_turn")
                .eq("status", "completed")
                .in_("recipe_id", recipe_ids)
                .gte("created_at", midnight.isoformat())
                .range(offset, offset + page_size - 1)
                .execute()
            )
        except Exception:
            logger.exception("Failed counting live runs today for public stats")
            return counts
        rows = res.data or []
        for row in rows:
            rid = str(row.get("recipe_id"))
            if rid:
                counts[rid] = counts.get(rid, 0) + 1
        if len(rows) < page_size:
            return counts
        offset += page_size


def refresh_public_stats(
    sb_client: Any,
    *,
    spy_ticker: str = DEFAULT_SPY_TICKER,
    page_size: int = 200,
) -> dict[str, int]:
    """Rebuild ``recipe_public_stats`` for every live recipe. Returns write counters."""
    recipes = _fetch_live_recipes(sb_client, page_size=page_size)
    if not recipes:
        return {"live_recipes": 0, "rows_written": 0}

    recipe_ids = [str(r.get("id")) for r in recipes if r.get("id")]
    results = _fetch_last_results(sb_client, recipe_ids)
    runs_today = _count_runs_today(sb_client, recipe_ids)

    windows: dict[tuple[str, str], list[dict]] = {}
    rows: list[dict[str, Any]] = []
    for recipe in recipes:
        points = parse_equity_curve(recipe.get("paper_equity_curve") or [])
        spy_rows: list[dict] = []
        if points:
            key = (points[0][0], points[-1][0])
            if key not in windows:
                windows[key] = _fetch_spy_rows(sb_client, key[0], key[1], spy_ticker)
            spy_rows = windows[key]
        rid = str(recipe.get("id"))
        last_result = results.get(rid) or {}
        rows.append(
            build_public_stats(
                recipe,
                spy_rows=spy_rows,
                last_job_result=last_result,
                last_run_at=last_result.get("_created_at"),
                runs_today=runs_today.get(rid, 0),
                resolved_model=last_result.get("resolved_model"),
            )
        )

    try:
        sb_client.table("recipe_public_stats").upsert(rows, on_conflict="recipe_id").execute()
    except Exception:
        logger.exception("Failed upserting recipe public stats rows")
        return {"live_recipes": len(recipes), "rows_written": 0}

    pruned = _prune_stale_rows(sb_client, set(recipe_ids))
    _write_desk_materialisations(sb_client, rows, results)

    logger.info("Refreshed %d recipe public stats rows (pruned %d)", len(rows), pruned)
    bot_lb_stats = refresh_user_bot_leaderboard_stats(sb_client, page_size=page_size)
    return {
        "live_recipes": len(recipes),
        "rows_written": len(rows),
        "rows_pruned": pruned,
        **({"bot_lb_rows_written": bot_lb_stats["rows_written"]} if bot_lb_stats["rows_written"] else {}),
    }


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def _daily_close_equity(curve: Any) -> list[tuple[date, float]]:
    by_day: dict[date, float] = {}
    for iso_day, eq in parse_equity_curve(curve):
        try:
            d = date.fromisoformat(iso_day)
        except ValueError:
            continue
        by_day[d] = eq
    return sorted(by_day.items(), key=lambda item: item[0])


def _open_position_stats(positions: Any) -> tuple[float, int, int]:
    if not isinstance(positions, list):
        return 0.0, 0, 0
    total_val = 0.0
    wins = 0
    total = 0
    for pos in positions:
        if not isinstance(pos, dict):
            continue
        total += 1
        mv = _to_float(pos.get("market_value"))
        shares = _to_float(pos.get("shares"))
        curr = _to_float(pos.get("current_price"))
        entry = _to_float(pos.get("entry_price"))
        if mv is not None:
            total_val += mv
        elif shares is not None and (curr is not None or entry is not None):
            total_val += shares * (curr if curr is not None else entry or 0.0)
        unreal = _to_float(pos.get("unrealized_pnl_net"))
        if unreal is None and shares is not None and curr is not None and entry is not None:
            unreal = (curr - entry) * shares
        if unreal is not None and unreal > 0:
            wins += 1
    return total_val, wins, total


def _window_trade_stats(trades: Any, start_day: date | None) -> tuple[float, int, int]:
    if not isinstance(trades, list):
        return 0.0, 0, 0
    realized = 0.0
    wins = 0
    total = 0
    for tr in trades:
        if not isinstance(tr, dict):
            continue
        pnl = _to_float(tr.get("pnl_net"))
        if pnl is None:
            continue
        if start_day is not None:
            stamp = _date_of(tr.get("exit_time")) or _date_of(tr.get("entry_time"))
            if not stamp:
                continue
            try:
                if date.fromisoformat(stamp) < start_day:
                    continue
            except ValueError:
                continue
        total += 1
        realized += pnl
        if pnl > 0:
            wins += 1
    return realized, wins, total


def build_bot_leaderboard_window_rows(
    recipe: dict[str, Any],
    *,
    now_utc: datetime | None = None,
) -> list[dict[str, Any]]:
    """Compute pre-materialized 7d/30d/90d/All-Time rows for one public user bot."""
    now = now_utc or datetime.now(UTC)
    today = now.date()
    recipe_id = str(recipe.get("id"))
    cash = _to_float(recipe.get("paper_cash"))
    if cash is None:
        cash = 10000.0
    curve_points = parse_equity_curve(recipe.get("paper_equity_curve") or [])
    daily_closes = _daily_close_equity(recipe.get("paper_equity_curve") or [])
    pos_val, open_wins, open_total = _open_position_stats(recipe.get("paper_positions") or [])
    last_eq = curve_points[-1][1] if curve_points else (cash + pos_val)
    trades = recipe.get("paper_trades") or []
    updated_at = now.isoformat()

    rows: list[dict[str, Any]] = []
    for w in LEADERBOARD_WINDOWS:
        start_day = (today - timedelta(days=w)) if w > 0 else None
        start_eq = 10000.0
        if start_day is not None:
            for d, eq in daily_closes:
                if d <= start_day:
                    start_eq = eq
                else:
                    break
        realized, closed_wins, closed_total = _window_trade_stats(trades, start_day)

        pos_days = 0
        active_days = 0
        for idx in range(1, len(daily_closes)):
            prev_eq = daily_closes[idx - 1][1]
            curr_day, curr_eq = daily_closes[idx]
            if start_day is not None and curr_day < start_day:
                continue
            if prev_eq > 0 and curr_eq != prev_eq:
                active_days += 1
                if curr_eq > prev_eq:
                    pos_days += 1

        ret_pct = round(((last_eq - start_eq) / start_eq) * 100.0, 2) if start_eq > 0 else 0.0
        denom = closed_total + open_total
        win_rate = round(((closed_wins + open_wins) * 100.0) / denom, 2) if denom > 0 else None
        consistency = round(((pos_days + 2.0) * 100.0) / (active_days + 4.0), 2)
        est_weekdays = max(1, (w * 5 // 7) if w > 0 else 20)
        activity_rate = round(min(100.0, (active_days / est_weekdays) * 100.0), 2)
        has_activity = closed_total > 0 or open_total > 0 or active_days > 0 or abs(last_eq - start_eq) > 0.01
        rows.append(
            {
                "recipe_id": recipe_id,
                "time_window_days": w,
                "total_equity": round(last_eq, 2),
                "return_pct": ret_pct,
                "realized_pnl": round(realized, 2),
                "win_rate": win_rate,
                "total_trades": closed_total,
                "consistency_score": consistency,
                "up_days": pos_days,
                "active_days": active_days,
                "trading_activity_rate": activity_rate,
                "has_activity": has_activity,
                "updated_at": updated_at,
            }
        )
    return rows


def _fetch_all_public_user_bots(sb_client: Any, page_size: int = 200) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = (
            sb_client.table("strategy_recipes")
            .select(
                "id, user_id, name, is_live, is_public, is_template, paper_cash, paper_trades, paper_positions, paper_equity_curve, graph_json"
            )
            .eq("is_public", True)
            .eq("is_template", False)
            .is_("archived_at", "null")
            .order("updated_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = page.data or []
        for row in rows:
            if row.get("user_id") == ANONYMOUS_USER_ID:
                continue
            graph = row.get("graph_json")
            stages = graph.get("stages") if isinstance(graph, dict) else None
            if not isinstance(stages, list) or len(stages) != 1:
                continue
            collected.append(row)
        if len(rows) < page_size:
            return collected
        offset += page_size


def refresh_user_bot_leaderboard_stats(
    sb_client: Any,
    *,
    page_size: int = 200,
) -> dict[str, int]:
    """Rebuild `user_bot_leaderboard_stats` for every public non-archived user bot."""
    try:
        bots = _fetch_all_public_user_bots(sb_client, page_size=page_size)
    except Exception:
        logger.exception("Failed fetching public user bots for leaderboard stats")
        return {"bots": 0, "rows_written": 0}
    if not bots:
        return {"bots": 0, "rows_written": 0}

    now_utc = datetime.now(UTC)
    payload: list[dict[str, Any]] = []
    for bot in bots:
        if bot.get("id"):
            payload.extend(build_bot_leaderboard_window_rows(bot, now_utc=now_utc))
    if not payload:
        return {"bots": len(bots), "rows_written": 0}

    try:
        sb_client.table("user_bot_leaderboard_stats").upsert(
            payload, on_conflict="recipe_id,time_window_days"
        ).execute()
    except Exception:
        logger.exception("Failed upserting user_bot_leaderboard_stats")
        return {"bots": len(bots), "rows_written": 0}

    return {"bots": len(bots), "rows_written": len(payload)}


def _prune_stale_rows(sb_client: Any, live_ids: set[str], page_size: int = 500) -> int:
    """A paused or archived bot must leave the public board, not linger as LIVE."""
    stale: list[str] = []
    offset = 0
    while True:
        try:
            page = (
                sb_client.table("recipe_public_stats")
                .select("recipe_id")
                .range(offset, offset + page_size - 1)
                .execute()
            )
        except Exception:
            logger.exception("Failed reading recipe public stats rows for pruning")
            return 0
        batch = page.data or []
        stale.extend(str(r.get("recipe_id")) for r in batch if str(r.get("recipe_id")) not in live_ids)
        if len(batch) < page_size:
            break
        offset += page_size

    if not stale:
        return 0
    try:
        sb_client.table("recipe_public_stats").delete().in_("recipe_id", stale).execute()
    except Exception:
        logger.exception("Failed pruning stale recipe public stats rows")
        return 0
    return len(stale)
