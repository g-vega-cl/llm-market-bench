"""Market data tools for quotes, price history, intraday profile, and ticker news."""

from core.config import logger
from tools._compat import MarketDataManager


def compute_volume_context(history: list[dict]) -> str:
    """Compute human-readable volume context from price history.

    Uses up to 20-day lookback for baseline, dynamic if fewer days available.
    Returns: "2.3x above 20-day average (85th percentile)"
    """
    volumes = [h["volume"] for h in history if h.get("volume")]
    if not volumes or len(volumes) < 5:
        return "insufficient volume data"

    latest_volume = volumes[0]
    lookback = volumes[:20] if len(volumes) >= 20 else volumes
    avg_volume = sum(lookback) / len(lookback)
    lookback_days = min(20, len(volumes))

    ratio = latest_volume / avg_volume if avg_volume > 0 else 0

    sorted_vols = sorted(volumes)
    below_count = sum(1 for v in sorted_vols if v < latest_volume)
    percentile = (below_count / len(sorted_vols)) * 100

    return f"{ratio:.1f}x above {lookback_days}-day average ({percentile:.0f}th percentile)"


async def execute_stock_tool(ticker: str) -> str:
    """Executes the stock tool and returns a stringified result for the LLM.

    Args:
        ticker: The stock ticker symbol.

    Returns:
        A formatted string with the stock quote data or an error message.
    """
    manager = MarketDataManager()
    try:
        data = await manager.get_quote(ticker)
        if not data or not data.exists:
            return f"Error: Ticker '{ticker}' not found."

        is_pm = await manager.is_premarket()
        if is_pm:
            pm_quote = await manager.get_premarket_quote(ticker)
            if pm_quote:
                pm_price = pm_quote["price"]
                prev_close = pm_quote["previous_close"]
                change = pm_quote["change"]
                change_pct = pm_quote["change_pct"]
                return (
                    f"Ticker: {data.ticker}\n"
                    f"Session: PRE-MARKET\n"
                    f"Pre-Market Price: ${pm_price:.2f}\n"
                    f"Previous Close: ${prev_close:.2f}\n"
                    f"Overnight Gap: {change:+.2f} ({change_pct:+.2f}%)\n"
                    f"Market Cap: ${data.market_cap / 1e9:.2f}B\n"
                    f"Status: VALID"
                )

        return (
            f"Ticker: {data.ticker}\n"
            f"Current Price: ${data.price:.2f}\n"
            f"Market Cap: ${data.market_cap / 1e9:.2f}B\n"
            f"Status: VALID"
        )
    except Exception as e:
        return f"Error fetching data for {ticker}: {str(e)}"


async def execute_price_history_tool(ticker: str, days: int = 7) -> str:
    """Fetches past prices for a ticker to help identify if news is priced in."""
    manager = MarketDataManager()
    try:
        data = await manager.get_history(ticker, days)

        if not data:
            return f"No historical price data found for {ticker}."

        history_str = f"Historical Price Data for {ticker} (Recent first):\n"
        for entry in data:
            vol_str = f", Volume: {entry['volume']}" if entry.get("volume") is not None else ""
            history_str += f"- {entry['fetched_at']}: ${entry['price']:.2f}{vol_str}\n"

        history_str += f"\nVolume Context: {compute_volume_context(data)}"

        return history_str
    except Exception as e:
        return f"Error fetching price history for {ticker}: {str(e)}"


async def execute_get_intraday_movement_profile_tool(
    ticker: str = "SPY",
    date: str | None = None,
    include_hourly_tape: bool = True,
) -> str:
    """Executes the get_intraday_movement_profile tool."""
    try:
        from analytics.intraday_profile import get_intraday_movement_report

        target_date = date or "latest_completed"
        report = await get_intraday_movement_report(
            ticker=ticker or "SPY",
            date_str=target_date,
            include_hourly_tape=include_hourly_tape,
        )
        return report.get("markdown", f"No intraday profile available for {ticker}.")
    except Exception as e:
        logger.exception("Error executing get_intraday_movement_profile tool for %s: %s", ticker, e)
        return f"Error executing get_intraday_movement_profile: {str(e)}"


async def execute_get_ticker_news_tool(ticker: str, limit: int = 5) -> str:
    """Executes the get_ticker_news tool to retrieve real-time stock news."""
    try:
        from analysis.ticker_news import execute_get_ticker_news_tool as _exec_news

        return await _exec_news(ticker=ticker, limit=limit)
    except Exception as e:
        logger.exception("Error executing get_ticker_news tool for %s: %s", ticker, e)
        return f"Error fetching news for '{ticker}': {str(e)}"
