"""Macro options derivatives positioning and sentiment aggregation.

Fetches and formats cross-asset options metrics (SPY, QQQ, IWM, GLD) into a compact,
rate-resilient comparison table with DB cache reuse and isolated timeouts.
"""

import asyncio
from typing import Any

from core.config import MACRO_OPTIONS_TICKERS, logger
from execution.providers.massive import MassiveOptionsClient

DEFAULT_MACRO_OPTIONS_TICKERS: tuple[str, ...] = MACRO_OPTIONS_TICKERS


async def fetch_macro_options_sentiment(
    tickers: list[str] | tuple[str, ...] | None = None,
    timeout_per_ticker: float = 5.0,
) -> list[dict[str, Any]]:
    """Fetch options sentiment metrics for multiple macro tickers sequentially with timeout protection.

    Sequential execution ensures requests flow through the global token-bucket rate limiter,
    preventing 429 burst errors on Free Tier API plans. Cache hits in Supabase execute in <0.3s.

    Args:
        tickers: Iterable of tickers to fetch. Defaults to DEFAULT_MACRO_OPTIONS_TICKERS.
        timeout_per_ticker: Seconds before aborting a single ticker's fetch.

    Returns:
        List of parsed metrics dictionaries for tickers that successfully completed.
    """
    target_tickers = list(tickers) if tickers else list(DEFAULT_MACRO_OPTIONS_TICKERS)
    client = MassiveOptionsClient()
    successful_metrics: list[dict[str, Any]] = []

    for ticker in target_tickers:
        ticker_sym = ticker.upper().strip()
        try:
            snapshot_coro = client.get_options_snapshot(ticker_sym)
            snapshot = await asyncio.wait_for(snapshot_coro, timeout=timeout_per_ticker)

            if snapshot.get("status") == "OK" and snapshot.get("metrics"):
                successful_metrics.append(snapshot["metrics"])
            else:
                logger.warning(
                    "No options metrics returned for macro ticker %s (status: %s)",
                    ticker_sym,
                    snapshot.get("status"),
                )
        except TimeoutError:
            logger.warning(
                "Timeout fetching options metrics for macro ticker %s after %.1fs",
                ticker_sym,
                timeout_per_ticker,
            )
        except Exception as e:
            logger.warning("Error fetching options metrics for macro ticker %s: %s", ticker_sym, e)

    return successful_metrics


def format_macro_options_markdown_table(metrics_list: list[dict[str, Any]]) -> str:
    """Format multiple options metrics dictionaries into a single dense comparison table.

    Produces a clean, token-efficient table with unified session and staleness metadata.
    """
    if not metrics_list:
        return "No macro options data available."

    first = metrics_list[0]
    session_status = first.get("session_status", "N/A")
    staleness_note = first.get("staleness_note", "N/A")
    as_of = first.get("as_of_timestamp", "N/A")
    ticker_symbols = ", ".join(m.get("ticker", "N/A") for m in metrics_list)

    lines = [
        f"### 📊 Macro Options Sentiment ({ticker_symbols})",
        f"- **Market Session**: {session_status} ({staleness_note})",
        f"- **As-Of Timestamp**: {as_of}",
        "",
        "| Ticker | Spot Price | P/C Vol | P/C OI | ATM IV | 25Δ Skew | Max Pain | Outlier Flow |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for m in metrics_list:
        ticker = m.get("ticker", "UNKNOWN")
        px = f"${m['underlying_price']:.2f}" if m.get("underlying_price") else "N/A"
        pv_val = m.get("put_call_volume_ratio")
        pv = f"{pv_val:.2f}" if isinstance(pv_val, (int, float)) else str(pv_val or "N/A")
        poi_val = m.get("put_call_oi_ratio")
        poi = f"{poi_val:.2f}" if isinstance(poi_val, (int, float)) else str(poi_val or "N/A")
        atm_iv = f"{m['atm_implied_volatility'] * 100:.1f}%" if m.get("atm_implied_volatility") else "N/A"
        skew = (
            f"{m['volatility_skew_25d_diff_pct']:+.2f}%" if m.get("volatility_skew_25d_diff_pct") is not None else "N/A"
        )
        max_pain = f"${m['max_pain']:.2f}" if m.get("max_pain") else "N/A"

        unusual = m.get("unusual_activity", [])
        unusual_str = f"{len(unusual)} alerts" if unusual else "None"

        lines.append(f"| {ticker} | {px} | {pv} | {poi} | {atm_iv} | {skew} | {max_pain} | {unusual_str} |")

    return "\n".join(lines)


async def get_macro_options_summary(
    tickers: list[str] | tuple[str, ...] | None = None,
    primary_ticker: str | None = None,
    timeout_per_ticker: float = 5.0,
) -> str:
    """Orchestrate fetching and formatting cross-asset macro options sentiment.

    Args:
        tickers: Custom ticker list. If None, uses DEFAULT_MACRO_OPTIONS_TICKERS.
        primary_ticker: Optional primary ticker (e.g. SPY) to guarantee as first in the list.
        timeout_per_ticker: Timeout limit for each ticker query.

    Returns:
        Formatted Markdown table ready for prompt or newsletter injection.
    """
    target_list: list[str] = list(tickers) if tickers else list(DEFAULT_MACRO_OPTIONS_TICKERS)

    if primary_ticker:
        p = primary_ticker.upper().strip()
        if p in target_list:
            target_list.remove(p)
        target_list.insert(0, p)

    metrics = await fetch_macro_options_sentiment(
        tickers=target_list,
        timeout_per_ticker=timeout_per_ticker,
    )
    return format_macro_options_markdown_table(metrics)
