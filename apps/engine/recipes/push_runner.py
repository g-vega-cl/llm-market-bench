"""Push-based multi-stage LLM execution & random 2-week point-in-time backtester."""

from __future__ import annotations

import json
import os
import random
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from openai import AsyncOpenAI

from core.config import logger
from core.llm.handlers.base import execute_tool
from core.llm.tools import CANONICAL_TOOLS_REGISTRY
from recipes.push_hydrator import fetch_push_context_batch, hydrate_stage_prompt
from recipes.push_schema import MemoriesBlock, NewsBlock, PushStrategy

LLMCaller = Callable[[str, list[str], str | None], Awaitable[dict[str, Any]]]

_TRADE_LINE_RE = re.compile(r"(?<!not\s)\b(BUY|SELL)\s+([A-Z]{1,5})\b")


def parse_trade_signals(output_text: str) -> list[dict[str, str]]:
    """Extract BUY/SELL ticker signals from JSON blocks or plain text."""
    if not output_text:
        return []

    for json_match in re.finditer(r"\[[\s\S]*?\]", output_text):
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, list):
                signals = []
                for item in parsed:
                    if isinstance(item, dict) and item.get("action") in {"BUY", "SELL"} and item.get("ticker"):
                        signals.append(
                            {
                                "action": str(item["action"]).upper(),
                                "ticker": str(item["ticker"]).upper().strip(),
                            }
                        )
                if signals:
                    return signals
        except json.JSONDecodeError:
            continue

    seen: set[tuple[str, str]] = set()
    signals: list[dict[str, str]] = []
    for action, ticker in _TRADE_LINE_RE.findall(output_text):
        key = (action, ticker)
        if key not in seen:
            seen.add(key)
            signals.append({"action": action, "ticker": ticker})
    return signals


def _llm_endpoints(openrouter_key: str | None, model: str) -> list[tuple[str, str, str]]:
    if openrouter_key:
        model_id = "deepseek/deepseek-chat" if model == "auto-strata" else model
        return [("https://openrouter.ai/api/v1", openrouter_key, model_id)]
    proxy_key = os.getenv("FREE_PROXY_MASTER_KEY") or os.getenv("STRATA_API_KEY", "local")
    strata_url = os.getenv("STRATA_BASE_URL", "").strip()
    proxy_url = os.getenv("FREE_LLM_PROXY_URL", "https://llm.clvg.uk/v1").strip()
    endpoints: list[tuple[str, str, str]] = []
    if strata_url:
        endpoints.append((strata_url, proxy_key, model))
    if proxy_url and proxy_url != strata_url:
        endpoints.append((proxy_url, proxy_key, model))
    return endpoints or [("https://llm.clvg.uk/v1", proxy_key, model)]


async def _run_tool_loop(
    client: AsyncOpenAI,
    model_id: str,
    prompt: str,
    tool_schemas: list[dict[str, Any]],
    cutoff_date: str | None,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a quantitative trading strategy agent. Use the provided tools when helpful "
                "and finish with clear BUY/SELL ticker decisions (or HOLD) as JSON or concise text."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    tool_traces: list[str] = []
    for _ in range(4):
        kwargs: dict[str, Any] = {"model": model_id, "messages": messages, "temperature": 0.1}
        if tool_schemas:
            kwargs["tools"] = tool_schemas
        resp = await client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            return {"output": msg.content or "", "tool_calls": tool_traces}

        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_traces.append(f"{tc.function.name}({json.dumps(args)})")
            tool_result = await execute_tool(
                tc.function.name,
                args,
                model_name=model_id,
                cutoff_date=cutoff_date,
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(tool_result)[:4000]})

    return {"output": "Max tool iterations reached without final answer.", "tool_calls": tool_traces}


async def default_llm_caller(
    prompt: str,
    selected_tools: list[str],
    cutoff_date: str | None = None,
    openrouter_key: str | None = None,
    model: str = "auto-strata",
) -> dict[str, Any]:
    """Execute a single Stage with OpenAI-compatible tool calling and Strata->Proxy failover."""
    tool_schemas = [CANONICAL_TOOLS_REGISTRY[t] for t in selected_tools if t in CANONICAL_TOOLS_REGISTRY]
    endpoints = _llm_endpoints(openrouter_key, model)
    last_exc: Exception | None = None
    for idx, (base_url, api_key, model_id) in enumerate(endpoints):
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=90)
        try:
            return await _run_tool_loop(client, model_id, prompt, tool_schemas, cutoff_date)
        except Exception as exc:
            last_exc = exc
            if idx + 1 < len(endpoints):
                logger.warning("Recipe LLM endpoint %s failed (%s); failing over to next endpoint", base_url, exc)
                continue
            raise
    if last_exc:
        raise last_exc
    return {"output": "", "tool_calls": []}


def _max_lookback_hours(strategy: PushStrategy) -> int:
    max_h = 168
    for stage in strategy.stages:
        for block in stage.blocks:
            if isinstance(block, (NewsBlock, MemoriesBlock)):
                max_h = max(max_h, block.recency_hours)
    return max_h


async def run_push_live(
    strategy: PushStrategy,
    sb_client: Any,
    llm_caller: LLMCaller | None = None,
    as_of_utc: datetime | None = None,
) -> dict[str, Any]:
    """Run all Stages sequentially as of now (or as_of_utc) with selected tools."""
    now_utc = as_of_utc or datetime.now(UTC)
    caller = llm_caller or default_llm_caller
    news_rows, memory_rows = fetch_push_context_batch(sb_client, now_utc, _max_lookback_hours(strategy))

    prev_output: str | None = None
    stage_results: list[dict[str, Any]] = []
    for stage in strategy.stages:
        prompt = hydrate_stage_prompt(stage, news_rows, memory_rows, now_utc, prev_output=prev_output)
        res = await caller(prompt, stage.selected_tools, None)
        output_text = str(res.get("output", ""))
        stage_results.append(
            {
                "stage_id": stage.id,
                "title": stage.title,
                "prompt": prompt,
                "output": output_text,
                "tool_calls": res.get("tool_calls", []),
            }
        )
        prev_output = output_text

    signals = parse_trade_signals(prev_output or "")
    return {
        "mode": "live_turn",
        "as_of_utc": now_utc.isoformat(),
        "stages": stage_results,
        "final_output": prev_output or "",
        "signals": signals,
    }


def pick_random_two_week_window(
    available_dates: list[str],
    rng: random.Random | None = None,
) -> list[str]:
    """Select a random contiguous ~2-week (10 trading day) window to prevent overfitting."""
    unique_sorted = sorted(set(available_dates))
    if len(unique_sorted) <= 10:
        return unique_sorted
    chooser = rng or random.Random()
    max_start = len(unique_sorted) - 10
    start_idx = chooser.randint(0, max_start)
    return unique_sorted[start_idx : start_idx + 10]


def _load_window_dates(sb_client: Any) -> list[str]:
    """Fetch recent trading dates from price_history (SPY anchor), falling back to weekdays."""
    try:
        res = (
            sb_client.table("price_history")
            .select("fetched_at")
            .eq("ticker", "SPY")
            .order("fetched_at", desc=True)
            .limit(1000)
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


def _load_daily_closes(sb_client: Any, tickers: set[str], start_day: str, end_day: str) -> dict[str, dict[str, float]]:
    """Batch-fetch daily closing prices from price_history for traded tickers."""
    if not tickers:
        return {}
    daily_close: dict[str, dict[str, float]] = {}
    try:
        res = (
            sb_client.table("price_history")
            .select("ticker, fetched_at, close, price")
            .in_("ticker", sorted(tickers))
            .gte("fetched_at", f"{start_day}T00:00:00+00:00")
            .lte("fetched_at", f"{end_day}T23:59:59+00:00")
            .order("fetched_at", desc=False)
            .limit(10000)
            .execute()
        )
        for row in res.data or []:
            day = str(row.get("fetched_at", ""))[:10]
            tkr = str(row.get("ticker", "")).upper().strip()
            raw_px = row.get("close") if row.get("close") is not None else row.get("price")
            if day and tkr and raw_px is not None:
                daily_close.setdefault(tkr, {})[day] = float(raw_px)
    except Exception:
        logger.exception("Failed fetching daily closes from price_history")
    return daily_close


async def run_push_backtest(
    strategy: PushStrategy,
    sb_client: Any,
    llm_caller: LLMCaller | None = None,
    rng: random.Random | None = None,
    slippage_bps: float = 5.0,
) -> dict[str, Any]:
    """Run a random ~2-week point-in-time backtest across daily steps using price_history."""
    caller = llm_caller or default_llm_caller
    all_dates = _load_window_dates(sb_client)
    window_dates = pick_random_two_week_window(all_dates, rng=rng)
    end_dt = datetime.fromisoformat(f"{window_dates[-1]}T21:00:00+00:00")
    news_rows, memory_rows = fetch_push_context_batch(
        sb_client,
        end_dt,
        lookback_hours=_max_lookback_hours(strategy) + 24 * 20,
    )

    llm_calls_made = 0
    day_signals: list[tuple[int, str, list[dict[str, str]]]] = []
    traded_tickers: set[str] = set()

    for idx, day_str in enumerate(window_dates):
        step_dt = datetime.fromisoformat(f"{day_str}T14:30:00+00:00")
        prev_output: str | None = None
        for stage in strategy.stages:
            prompt = hydrate_stage_prompt(stage, news_rows, memory_rows, step_dt, prev_output=prev_output)
            try:
                res = await caller(prompt, stage.selected_tools, day_str)
                llm_calls_made += 1
                prev_output = str(res.get("output", ""))
            except Exception:
                logger.exception("Stage %s failed on backtest date %s", stage.id, day_str)
                prev_output = ""

        signals = parse_trade_signals(prev_output or "")
        day_signals.append((idx, day_str, signals))
        for sig in signals:
            traded_tickers.add(sig["ticker"])

    daily_close = _load_daily_closes(sb_client, traded_tickers, window_dates[0], window_dates[-1])

    trades: list[dict[str, Any]] = []
    skipped_trades: list[dict[str, Any]] = []
    starting_capital = 10000.0
    equity = starting_capital
    equity_curve: list[dict[str, Any]] = []
    peak = equity
    max_dd = 0.0
    slip = slippage_bps / 10000.0

    for idx, day_str, signals in day_signals:
        next_day = window_dates[idx + 1] if idx + 1 < len(window_dates) else None
        for sig in signals:
            tkr = sig["ticker"]
            prices = daily_close.get(tkr, {})
            entry_px = prices.get(day_str)
            exit_px = prices.get(next_day) if next_day else None
            if entry_px and exit_px and entry_px > 0:
                raw_ret = (exit_px - entry_px) / entry_px
                if sig["action"] == "SELL":
                    raw_ret = -raw_ret
                net_ret = raw_ret - (2 * slip)
                pnl_mid = 1000.0 * raw_ret
                pnl_net = 1000.0 * net_ret
                equity += pnl_net
                peak = max(peak, equity)
                dd = ((peak - equity) / peak) * 100.0 if peak > 0 else 0.0
                max_dd = max(max_dd, dd)
                trades.append(
                    {
                        "ticker": tkr,
                        "action": sig["action"],
                        "entry_time": day_str,
                        "entry_price": round(entry_px, 2),
                        "exit_time": next_day,
                        "exit_price": round(exit_px, 2),
                        "shares": round(1000.0 / entry_px, 4),
                        "pnl_midpoint": round(pnl_mid, 2),
                        "pnl_net": round(pnl_net, 2),
                        "return_pct_midpoint": round(raw_ret * 100.0, 2),
                        "return_pct_net": round(net_ret * 100.0, 2),
                        "exit_reason": "NEXT_DAY_CLOSE",
                        "confidence": 100,
                    }
                )
            else:
                skipped_trades.append(
                    {
                        "time": day_str,
                        "skip_type": "NO_PRICE_DATA",
                        "reason": f"Missing daily bar for {tkr} on {day_str} -> {next_day or 'EOF'}",
                    }
                )
        equity_curve.append({"time": day_str, "equity": round(equity, 2)})

    winning_trades = sum(1 for t in trades if t["pnl_net"] > 0)
    losing_trades = len(trades) - winning_trades
    gross_profit = sum(t["pnl_net"] for t in trades if t["pnl_net"] > 0)
    gross_loss = abs(sum(t["pnl_net"] for t in trades if t["pnl_net"] < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    win_rate = round((winning_trades / len(trades)) * 100.0, 1) if trades else 0.0
    total_net_pct = round(((equity - starting_capital) / starting_capital) * 100.0, 2)
    total_mid_pnl = sum(t["pnl_midpoint"] for t in trades)
    total_mid_pct = round((total_mid_pnl / starting_capital) * 100.0, 2)

    return {
        "mode": "backtest",
        "window_dates": window_dates,
        "starting_capital": starting_capital,
        "ending_capital_midpoint": round(starting_capital + total_mid_pnl, 2),
        "ending_capital_net": round(equity, 2),
        "total_return_pct_midpoint": total_mid_pct,
        "total_return_pct_net": total_net_pct,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown_pct": round(max_dd, 2),
        "total_trades": len(trades),
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "llm_calls_made": llm_calls_made,
        "trades": trades,
        "skipped_trades": skipped_trades,
        "equity_curve": equity_curve,
    }
