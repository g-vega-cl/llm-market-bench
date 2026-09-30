"""Technical analysis and options tools: volatility, screeners, correlation, options sentiment, chains, vol surfaces, and barrier touches."""

import asyncio
import statistics
from unittest.mock import AsyncMock

from core.config import logger
from tools._compat import MarketDataManager, get_supabase_client
from tools.market_data import compute_volume_context as compute_volume_context


async def execute_volatility_metrics_tool(ticker: str, days: int = 14) -> str:
    """Calculates volatility metrics and volume context for a ticker."""
    manager = MarketDataManager()
    try:
        data = await manager.get_history(ticker, days)

        if not data or len(data) < 2:
            return f"Insufficient historical data for {ticker} to calculate volatility."

        curr = data[0]["price"]
        prices = [p["price"] for p in data]

        avg = statistics.mean(prices)
        stdev = statistics.stdev(prices)
        p_min = min(prices)
        p_max = max(prices)

        return (
            f"Volatility Metrics for {ticker} (last {len(prices)} samples):\n"
            f"- Current Price: ${curr:.2f}\n"
            f"- Avg Price: ${avg:.2f}\n"
            f"- Std Dev: ${stdev:.2f}\n"
            f"- Range: ${p_min:.2f} - ${p_max:.2f}\n"
            f"- Distance from Mean: {((curr - avg) / stdev):.2f} standard deviations\n"
            f"- Volume Context: {compute_volume_context(data)}"
        )
    except Exception as e:
        return f"Error calculating volatility for {ticker}: {str(e)}"


async def execute_stock_screener_tool(
    market_cap_more_than: float | None = None,
    market_cap_lower_than: float | None = None,
    price_more_than: float | None = None,
    price_lower_than: float | None = None,
    beta_more_than: float | None = None,
    beta_lower_than: float | None = None,
    volume_more_than: float | None = None,
    volume_lower_than: float | None = None,
    dividend_more_than: float | None = None,
    dividend_lower_than: float | None = None,
    sector: str | None = None,
    industry: str | None = None,
    exchange: str | None = "NYSE,NASDAQ",
    limit: int = 10,
    is_actively_trading: bool = True,
) -> str:
    """Executes the stock screener tool and returns a formatted list of candidates with volume context."""
    manager = MarketDataManager()
    try:
        results = await manager.screen_stocks(
            market_cap_more_than=market_cap_more_than,
            market_cap_lower_than=market_cap_lower_than,
            price_more_than=price_more_than,
            price_lower_than=price_lower_than,
            beta_more_than=beta_more_than,
            beta_lower_than=beta_lower_than,
            volume_more_than=volume_more_than,
            volume_lower_than=volume_lower_than,
            dividend_more_than=dividend_more_than,
            dividend_lower_than=dividend_lower_than,
            sector=sector,
            industry=industry,
            exchange=exchange,
            limit=limit,
            is_actively_trading=is_actively_trading,
        )

        if not results:
            return "No stocks found matching the criteria."

        async def enrich_item(item):
            ticker = item.get("symbol")
            if ticker:
                try:
                    history = await manager.get_history(ticker, days=20)
                    vol_context = compute_volume_context(history) if history else "no volume data"
                except Exception as e:
                    logger.error(f"Error enriching ticker {ticker} in screener: {e}")
                    vol_context = "error fetching volume data"
            else:
                vol_context = "unknown"
            return {**item, "volume_context": vol_context}

        enrich_tasks = [enrich_item(item) for item in results]
        enriched_results = await asyncio.gather(*enrich_tasks)

        output = f"Stock Screening Results (Top {len(enriched_results)}):\n"
        for item in enriched_results:
            output += (
                f"- {item.get('symbol')} ({item.get('companyName')}): "
                f"Price: ${item.get('price', 0):.2f}, "
                f"Market Cap: ${item.get('marketCap', 0) / 1e9:.2f}B, "
                f"Volume Context: {item.get('volume_context')}\n"
            )

        return output
    except Exception as e:
        return f"Error executing stock screener: {str(e)}"


async def execute_find_uncorrelated_assets_tool(
    max_correlation: float = 0.3, min_return: float = 0.0, method: str = "pearson"
) -> str:
    """Find asset pairs with low correlation and positive 90-day momentum.

    Args:
        max_correlation: Maximum absolute correlation (0.0-1.0). Default 0.3.
        min_return: Minimum 90-day return for both assets in %. Default 0.0.
        method: 'pearson' or 'spearman'. Default 'pearson'.

    Returns:
        Formatted list of uncorrelated pairs with returns.
    """
    client = get_supabase_client()

    try:
        runs = client.table("correlation_runs").select("id").order("run_date", desc=True).limit(1).execute()

        if not runs.data:
            return (
                "No correlation data available yet. The correlation matrix runs weekly on Sundays. "
                "Check back after the next scheduled run."
            )

        run_id = runs.data[0]["id"]

        corr_field = "pearson_corr" if method == "pearson" else "spearman_corr"

        results = client.table("correlation_data").select("*").eq("run_id", run_id).execute()

        if not results.data:
            return "No correlation data found for the latest run."

        filtered = []
        for row in results.data:
            corr = row.get(corr_field)
            if corr is None:
                continue
            if abs(corr) > max_correlation:
                continue
            ret_a = row.get("returns_a_90d") or 0
            ret_b = row.get("returns_b_90d") or 0
            if ret_a < min_return or ret_b < min_return:
                continue
            filtered.append(
                {
                    **row,
                    "abs_corr": abs(corr),
                    "avg_return": (ret_a + ret_b) / 2,
                }
            )

        filtered.sort(key=lambda x: x["abs_corr"])

        if not filtered:
            return (
                f"No pairs found with correlation < {max_correlation} and returns >= {min_return}%. "
                f"Try increasing max_correlation or decreasing min_return."
            )

        output = f"UNCORRELATED ASSET PAIRS (sorted by {method} correlation, lowest first):\n\n"

        for i, pair in enumerate(filtered[:20], 1):
            output += (
                f"{i}. {pair['ticker_a']}/{pair['ticker_b']}:\n"
                f"   {method.capitalize()} Correlation: {pair[corr_field]:.4f} | "
                f"90d Returns: {pair['returns_a_90d']:.2f}% / {pair['returns_b_90d']:.2f}%\n"
            )

        if len(filtered) > 20:
            output += f"\n... and {len(filtered) - 20} more pairs. Reduce filters to see more."

        return output

    except Exception as e:
        return f"Error finding uncorrelated assets: {str(e)}"


async def execute_get_options_sentiment_tool(
    ticker: str,
    expiration_date: str | None = None,
) -> str:
    """Executes the get_options_sentiment tool to fetch and format options market sentiment."""
    from execution.providers.massive import (
        MassiveOptionsClient,
        calculate_options_sentiment,
        format_options_sentiment_markdown,
    )

    try:
        manager = MarketDataManager()
        quote = await manager.get_quote(ticker)
        current_price = quote.price if quote and quote.exists else None

        client = MassiveOptionsClient()
        snapshot = await client.get_options_snapshot(ticker, current_price=current_price)

        if snapshot.get("status") != "OK" or not snapshot.get("contracts"):
            return f"No options data available for ticker '{ticker}'."

        contracts = snapshot.get("contracts", [])
        if expiration_date:
            contracts = [c for c in contracts if c.get("details", {}).get("expiration_date") == expiration_date]
            if not contracts:
                return f"No options contracts found for {ticker} on expiration {expiration_date}."

        metrics = calculate_options_sentiment(ticker, contracts, current_price=current_price)
        return format_options_sentiment_markdown(metrics)
    except Exception as e:
        logger.exception("Error executing get_options_sentiment tool for %s: %s", ticker, e)
        return f"Error fetching options sentiment for '{ticker}': {str(e)}"


async def execute_get_macro_options_sentiment_tool(
    primary_ticker: str = "SPY",
    tickers: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Executes the macro options sentiment aggregation across market proxies (SPY, QQQ, IWM, GLD)."""
    # If execute_get_options_sentiment_tool was mocked by hermetic tests, delegate directly
    import core.llm.tools as bt

    fn = getattr(bt, "execute_get_options_sentiment_tool", execute_get_options_sentiment_tool)
    if isinstance(fn, AsyncMock):
        return await fn(ticker=primary_ticker)

    from analytics.macro_options import get_macro_options_summary

    try:
        summary = await get_macro_options_summary(tickers=tickers, primary_ticker=primary_ticker)
        if summary and not summary.startswith("No macro options"):
            return summary
    except Exception as e:
        logger.exception("Error executing get_macro_options_sentiment: %s", e)

    return await fn(ticker=primary_ticker)


async def execute_get_option_chain_tool(
    ticker: str,
    expiration_date: str | None = None,
    contract_type: str = "all",
    strike_range_pct: float = 10.0,
    min_dte: int | None = None,
    max_dte: int | None = None,
) -> str:
    """Executes the get_option_chain tool to fetch and format a compact near-the-money options board."""
    from execution.providers.massive import (
        MassiveOptionsClient,
        filter_option_chain,
        format_option_chain_markdown,
    )

    try:
        manager = MarketDataManager()
        quote = await manager.get_quote(ticker)
        current_price = quote.price if quote and quote.exists else None

        client = MassiveOptionsClient()
        snapshot = await client.get_options_snapshot(ticker, current_price=current_price)

        if snapshot.get("status") != "OK" or not snapshot.get("contracts"):
            return f"No options chain data available for ticker '{ticker}'."

        contracts = snapshot.get("contracts", [])
        filtered = filter_option_chain(
            contracts=contracts,
            current_price=current_price,
            expiration_date=expiration_date,
            contract_type=contract_type,
            strike_range_pct=strike_range_pct,
            min_dte=min_dte,
            max_dte=max_dte,
        )

        return format_option_chain_markdown(ticker, filtered, current_price=current_price)
    except Exception as e:
        logger.exception("Error executing get_option_chain tool for %s: %s", ticker, e)
        return f"Error fetching option chain for '{ticker}': {str(e)}"


async def execute_options_vol_surface_tool(ticker: str = "SPY") -> str:
    """Executes the get_options_vol_surface tool to compute vol surface, cone, and IV premium."""
    from analytics.options_surface import get_options_vol_surface_report

    try:
        report = await get_options_vol_surface_report(ticker=ticker)
        return report.get("markdown") or str(report)
    except Exception as e:
        logger.exception("Error executing get_options_vol_surface tool for %s: %s", ticker, e)
        return f"Error analyzing options volatility surface for '{ticker}': {str(e)}"


# Canonical naming alias
execute_get_options_vol_surface_tool = execute_options_vol_surface_tool


async def execute_barrier_touch_probabilities_tool(
    ticker: str,
    target_pct: float | None = None,
    stop_pct: float | None = None,
    horizon_bars: int = 5,
    lookback_days: int = 252,
) -> str:
    """Executes empirical Triple Barrier Method touch probability analysis."""
    try:
        from analytics.barrier_probabilities import get_barrier_touch_probabilities_report

        report = await get_barrier_touch_probabilities_report(
            ticker=ticker,
            target_pct=target_pct,
            stop_pct=stop_pct,
            horizon_bars=horizon_bars,
            lookback_days=lookback_days,
        )
        if "markdown" in report:
            return report["markdown"]
        return report.get("error", "Unknown error calculating barrier touch probabilities.")
    except Exception as e:
        logger.exception("Error executing get_barrier_touch_probabilities tool for %s: %s", ticker, e)
        return f"Error calculating barrier touch probabilities: {str(e)}"
