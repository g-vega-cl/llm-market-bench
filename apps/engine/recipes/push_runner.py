"""Push-based single-call LLM execution & 3x/day ET point-in-time backtester."""

from __future__ import annotations

import inspect
import json
import random
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from core.config import logger
from core.time_utils import EASTERN_TZ
from recipes.backtest_accounting import BacktestAccumulator
from recipes.intraday_bars import (
    CORPUS_MIN_DATE,
    expand_dates_to_et_slots,
    fetch_intraday_bars_for_ticker,
    resolve_slot_price,
)
from recipes.intraday_bars import (
    load_daily_closes as _load_daily_closes,
)
from recipes.llm_caller import LLMCaller, default_llm_caller
from recipes.llm_caller import invoke_llm as _invoke_llm
from recipes.portfolio_engine import (
    DEFAULT_CONCURRENCY_CONFIG,
    PortfolioState,
    apply_portfolio_step,
    enrich_open_positions,
    format_portfolio_prompt_block,
)
from recipes.push_hydrator import fetch_push_context_batch, hydrate_stage_prompt
from recipes.push_schema import MemoriesBlock, NewsBlock, PushStrategy

ProgressCallback = Callable[[int, dict[str, Any]], Awaitable[None] | None]

_TRADE_LINE_RE = re.compile(r"(?<!not\s)\b(BUY|SELL|EXIT)\s+([A-Z]{1,5})\b")
_VALID_ACTIONS = {"BUY", "SELL", "EXIT"}


def _parse_json_signal_array(chunk: str) -> list[dict[str, str]]:
    """Parse one candidate JSON array into validated BUY/SELL/EXIT signal dicts."""
    try:
        parsed = json.loads(chunk)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    signals: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "").upper().strip()
        ticker = str(item.get("ticker") or "").upper().strip()
        if action in _VALID_ACTIONS and ticker:
            signals.append({"action": action, "ticker": ticker})
    return signals


def parse_trade_signals(output_text: str) -> list[dict[str, str]]:
    """Extract BUY/SELL/EXIT ticker signals from JSON blocks or plain text."""
    if not output_text:
        return []

    for json_match in re.finditer(r"\[[\s\S]*?\]", output_text):
        signals = _parse_json_signal_array(json_match.group(0))
        if signals:
            return signals

    seen: set[tuple[str, str]] = set()
    signals: list[dict[str, str]] = []
    for action, ticker in _TRADE_LINE_RE.findall(output_text):
        key = (action, ticker)
        if key not in seen:
            seen.add(key)
            signals.append({"action": action, "ticker": ticker})
    return signals


def _max_lookback_hours(strategy: PushStrategy) -> int:
    max_h = 168
    for stage in strategy.stages:
        for block in stage.blocks:
            if isinstance(block, (NewsBlock, MemoriesBlock)):
                max_h = max(max_h, block.recency_hours)
    return max_h


async def _resolve_live_prices(tickers: set[str]) -> dict[str, float]:
    """Fetch current live quote prices concurrently for open or newly signaled tickers."""
    if not tickers:
        return {}
    import asyncio

    from tools._compat import MarketDataManager

    ordered = sorted(tickers)
    manager = MarketDataManager()
    results = await asyncio.gather(*(manager.get_quote(tkr) for tkr in ordered), return_exceptions=True)
    prices: dict[str, float] = {}
    for tkr, quote in zip(ordered, results, strict=True):
        if isinstance(quote, Exception):
            logger.warning("Failed fetching live quote for %s during live_turn", tkr, exc_info=quote)
            continue
        if quote and quote.exists and quote.price:
            prices[tkr] = float(quote.price)
    return prices


async def run_push_live(
    strategy: PushStrategy,
    sb_client: Any,
    llm_caller: LLMCaller | None = None,
    as_of_utc: datetime | None = None,
    recipe_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the single LLM stage live with persistent Long-Only portfolio tracking."""
    now_utc = as_of_utc or datetime.now(UTC)
    now_et_label = now_utc.astimezone(EASTERN_TZ).strftime("%Y-%m-%d %H:%M ET")
    caller = llm_caller or default_llm_caller
    news_rows, memory_rows = fetch_push_context_batch(sb_client, now_utc, _max_lookback_hours(strategy))

    concurrency_cfg = (recipe_row or {}).get("concurrency_config") or DEFAULT_CONCURRENCY_CONFIG
    portfolio = PortfolioState.from_recipe_row(recipe_row)
    held_tickers = {str(p.get("ticker", "")).upper() for p in portfolio.positions if p.get("ticker")}
    live_prices = await _resolve_live_prices(held_tickers)
    portfolio_block = format_portfolio_prompt_block(
        portfolio,
        current_prices=live_prices,
        concurrency_config=concurrency_cfg,
    )

    prev_output: str | None = None
    stage_results: list[dict[str, Any]] = []
    for stage in strategy.stages:
        prompt = hydrate_stage_prompt(
            stage,
            news_rows,
            memory_rows,
            now_utc,
            prev_output=prev_output,
            portfolio_block=portfolio_block,
        )
        res = await _invoke_llm(caller, prompt, stage.selected_tools, None, as_of_utc=None)
        output_text = str(res.get("output", ""))
        stage_results.append(
            {
                "stage_id": stage.id,
                "title": stage.title,
                "prompt": prompt,
                "output": output_text,
                "tool_calls": res.get("tool_calls", []),
                "trace": res.get("trace") or {"rounds": [], "forced_final_synthesis": False},
            }
        )
        prev_output = output_text

    signals = parse_trade_signals(prev_output or "")
    new_tickers = {sig["ticker"] for sig in signals if sig["ticker"] not in live_prices}
    if new_tickers:
        live_prices.update(await _resolve_live_prices(new_tickers))

    step_res = apply_portfolio_step(
        portfolio,
        slot_label=now_et_label,
        signals=signals,
        prices=live_prices,
        concurrency_config=concurrency_cfg,
    )

    return {
        "mode": "live_turn",
        "as_of_utc": now_utc.isoformat(),
        "slot_label": now_et_label,
        "stages": stage_results,
        "final_output": prev_output or "",
        "signals": signals,
        "executed_signals": step_res["executed_signals"],
        "signal_prices": live_prices,
        "updated_portfolio": {
            "paper_cash": round(portfolio.cash, 2),
            "paper_positions": enrich_open_positions(portfolio, live_prices),
            "paper_trades": portfolio.trades,
            "paper_equity_curve": portfolio.equity_curve,
        },
    }


def pick_random_two_week_window(
    available_dates: list[str],
    rng: random.Random | None = None,
) -> list[str]:
    """Select a random contiguous 2-week (10 trading day) window to prevent overfitting."""
    unique_sorted = sorted(set(available_dates))
    if len(unique_sorted) <= 10:
        return unique_sorted
    chooser = rng or random.Random()
    max_start = len(unique_sorted) - 10
    start_idx = chooser.randint(0, max_start)
    return unique_sorted[start_idx : start_idx + 10]


def _load_window_dates(sb_client: Any) -> list[str]:
    """Fetch recent trading dates >= CORPUS_MIN_DATE from price_history (SPY anchor)."""
    try:
        res = (
            sb_client.table("price_history")
            .select("fetched_at")
            .eq("ticker", "SPY")
            .gte("fetched_at", f"{CORPUS_MIN_DATE}T00:00:00+00:00")
            .order("fetched_at", desc=True)
            .limit(500)
            .execute()
        )
        dates = [str(r.get("fetched_at", ""))[:10] for r in (res.data or []) if r.get("fetched_at")]
        if dates:
            return sorted(set(dates))
    except Exception:
        logger.exception("Failed fetching SPY trading calendar from price_history")

    today = datetime.now(UTC).date()
    return [
        (today - timedelta(days=offset)).isoformat()
        for offset in range(20, 0, -1)
        if (today - timedelta(days=offset)).weekday() < 5
    ]


async def _ensure_slot_prices(
    acc: BacktestAccumulator,
    sb_client: Any,
    tickers: set[str],
    start_day: str,
    end_day: str,
    slot_dt_utc: datetime,
) -> dict[str, float]:
    """Fetch missing intraday/daily prices for tickers and resolve slot execution prices."""
    unseen = {t for t in tickers if t and t not in acc.intraday_bars}
    if unseen:
        daily_map = _load_daily_closes(sb_client, unseen, start_day, end_day)
        for tkr in unseen:
            acc.daily_close.setdefault(tkr, {}).update(daily_map.get(tkr, {}))
            bars = await fetch_intraday_bars_for_ticker(sb_client, tkr, start_day, end_day)
            acc.intraday_bars[tkr] = bars

    resolved: dict[str, float] = {}
    for tkr in tickers:
        px = resolve_slot_price(acc.intraday_bars.get(tkr, []), acc.daily_close, tkr, slot_dt_utc)
        if px and px > 0:
            resolved[tkr] = px
    return resolved


async def _emit_progress(
    on_progress: ProgressCallback | None,
    progress_pct: int,
    snapshot: dict[str, Any],
) -> None:
    if on_progress is None:
        return
    maybe_awaitable = on_progress(progress_pct, snapshot)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable


async def run_push_backtest(
    strategy: PushStrategy,
    sb_client: Any,
    llm_caller: LLMCaller | None = None,
    rng: random.Random | None = None,
    slippage_bps: float = 5.0,
    on_progress: ProgressCallback | None = None,
    concurrency_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a 10-trading-day, 3x/day ET (09:30/12:30/15:30) point-in-time swing backtest."""
    caller = llm_caller or default_llm_caller
    all_dates = _load_window_dates(sb_client)
    window_dates = pick_random_two_week_window(all_dates, rng=rng)
    slots = expand_dates_to_et_slots(window_dates)
    start_day = window_dates[0] if window_dates else datetime.now(UTC).date().isoformat()
    end_day = window_dates[-1] if window_dates else start_day
    end_dt = slots[-1]["timestamp_utc"] if slots else datetime.now(UTC)

    news_rows, memory_rows = fetch_push_context_batch(
        sb_client,
        end_dt,
        lookback_hours=_max_lookback_hours(strategy) + 24 * 20,
    )

    acc = BacktestAccumulator(
        window_dates=[s["slot_label"] for s in slots],
        slippage_bps=slippage_bps,
        concurrency_config=concurrency_config or dict(DEFAULT_CONCURRENCY_CONFIG),
    )
    total_slots = len(slots)

    await _emit_progress(
        on_progress,
        10,
        acc.snapshot(days_completed=0, current_day=slots[0]["slot_label"] if slots else None),
    )

    last_prices: dict[str, float] = {}
    for idx, slot in enumerate(slots):
        held_tickers = {str(p["ticker"]).upper() for p in acc.portfolio.positions}
        held_prices = await _ensure_slot_prices(
            acc,
            sb_client,
            held_tickers,
            start_day,
            end_day,
            slot["timestamp_utc"],
        )
        portfolio_block = format_portfolio_prompt_block(
            acc.portfolio,
            current_prices=held_prices,
            concurrency_config=acc.concurrency_config,
        )

        prev_output: str | None = None
        last_prompt = ""
        last_trace: dict[str, Any] | None = None
        day_tool_calls: list[str] = []
        day_status = "completed"
        for stage in strategy.stages:
            prompt = hydrate_stage_prompt(
                stage,
                news_rows,
                memory_rows,
                slot["timestamp_utc"],
                prev_output=prev_output,
                portfolio_block=portfolio_block,
            )
            last_prompt = prompt
            try:
                res = await _invoke_llm(
                    caller,
                    prompt,
                    stage.selected_tools,
                    slot["day_str"],
                    as_of_utc=slot["timestamp_iso"],
                )
                acc.llm_calls_made += 1
                prev_output = str(res.get("output", ""))
                day_tool_calls.extend(str(tc) for tc in (res.get("tool_calls") or []))
                last_trace = res.get("trace")
            except Exception:
                logger.exception("Stage %s failed on backtest slot %s", stage.id, slot["slot_label"])
                prev_output = ""
                day_status = "error"

        signals = parse_trade_signals(prev_output or "")
        needed_tickers = held_tickers | {sig["ticker"] for sig in signals}
        slot_prices = await _ensure_slot_prices(
            acc,
            sb_client,
            needed_tickers,
            start_day,
            end_day,
            slot["timestamp_utc"],
        )
        last_prices = slot_prices

        acc.settle_slot(
            idx=idx,
            slot_label=slot["slot_label"],
            signals=signals,
            slot_prices=slot_prices,
            tool_calls=day_tool_calls,
            output_text=prev_output or "",
            day_status=day_status,
            is_final_step=(idx == total_slots - 1),
            prompt=last_prompt,
            trace=last_trace,
        )

        steps_done = idx + 1
        progress_pct = 95 if steps_done >= total_slots else 10 + round((steps_done / total_slots) * 85)
        next_label = slots[idx + 1]["slot_label"] if idx + 1 < total_slots else slot["slot_label"]
        await _emit_progress(
            on_progress,
            progress_pct,
            acc.snapshot(days_completed=steps_done, current_day=next_label, latest_prices=slot_prices),
        )

    return acc.snapshot(
        days_completed=total_slots,
        current_day=slots[-1]["slot_label"] if slots else None,
        latest_prices=last_prices,
    )
