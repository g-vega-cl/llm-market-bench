"""Macroeconomic indicators, FRED time series, yield curves, and volatility regimes."""

import statistics

from core.config import logger
from tools._compat import MarketDataManager


async def execute_get_global_macro_context_tool() -> str:
    """Retrieves the global macroeconomic context without hardcoded instructions."""
    try:
        from core.macro_tracker import get_global_macro_context

        manager = MarketDataManager()
        return await get_global_macro_context(manager)
    except Exception as e:
        logger.exception(f"Error in execute_get_global_macro_context_tool: {e}")
        return f"Error retrieving global macro context: {str(e)}"


async def execute_get_volatility_index_details_tool(lookback_days: int = 90) -> str:
    """Retrieves canonical spot Cboe VIX (^VIX) metrics and VIX futures ETF (VIXY/VIXM) term structure."""
    try:
        manager = MarketDataManager()
        # Fetch histories for Spot VIX (^VIX) and VIX futures ETFs (VIXY, VIXM), plus SPY benchmark
        vix_data = await manager.get_history("^VIX", days=lookback_days)
        vixy_data = await manager.get_history("VIXY", days=lookback_days)
        vixm_data = await manager.get_history("VIXM", days=lookback_days)
        spy_data = await manager.get_history("SPY", days=lookback_days)

        if not vixy_data or not vixm_data or not spy_data:
            return "Error: Could not retrieve price history for VIXY, VIXM, or SPY."

        def pearson_correlation(x: list[float], y: list[float]) -> float:
            if len(x) != len(y) or len(x) < 2:
                return 0.0
            mean_x = sum(x) / len(x)
            mean_y = sum(y) / len(y)
            diffs_x = [xv - mean_x for xv in x]
            diffs_y = [yv - mean_y for yv in y]
            num = sum(dx * dy for dx, dy in zip(diffs_x, diffs_y, strict=True))
            den_x = sum(dx * dx for dx in diffs_x)
            den_y = sum(dy * dy for dy in diffs_y)
            if den_x == 0 or den_y == 0:
                return 0.0
            return num / ((den_x * den_y) ** 0.5)

        # Map ETF histories to dates
        vixy_by_date = {row["fetched_at"][:10]: float(row["price"]) for row in vixy_data}
        vixm_by_date = {row["fetched_at"][:10]: float(row["price"]) for row in vixm_data}
        spy_by_date = {row["fetched_at"][:10]: float(row["price"]) for row in spy_data}

        # Align on overlapping ETF dates
        common_dates = sorted(list(set(vixy_by_date.keys()) & set(vixm_by_date.keys()) & set(spy_by_date.keys())))
        if len(common_dates) < 5:
            return f"Insufficient overlapping price history (found only {len(common_dates)} days) to compute volatility metrics."

        vixy_prices = [vixy_by_date[d] for d in common_dates]
        vixm_prices = [vixm_by_date[d] for d in common_dates]
        spy_prices = [spy_by_date[d] for d in common_dates]

        vixy_returns = [(vixy_prices[i] - vixy_prices[i - 1]) / vixy_prices[i - 1] for i in range(1, len(common_dates))]
        vixm_returns = [(vixm_prices[i] - vixm_prices[i - 1]) / vixm_prices[i - 1] for i in range(1, len(common_dates))]
        spy_returns = [(spy_prices[i] - spy_prices[i - 1]) / spy_prices[i - 1] for i in range(1, len(common_dates))]

        curr_vixy = vixy_prices[-1]
        curr_vixm = vixm_prices[-1]
        vixy_1d_return = vixy_returns[-1] * 100 if vixy_returns else 0.0
        vixm_1d_return = vixm_returns[-1] * 100 if vixm_returns else 0.0

        # Term Structure & Curve Structure from VIXY/VIXM ratio
        ratios = [vixy_prices[idx] / vixm_prices[idx] for idx in range(len(vixy_prices))]
        curr_ratio = ratios[-1]
        smaller_ratio = sum(1 for r in ratios if r < curr_ratio)
        ratio_percentile = (smaller_ratio / len(ratios)) * 100

        if curr_ratio > 0.95 or ratio_percentile > 85:
            curve_state = f"BACKWARDATION / MARKET STRESS (VIXY/VIXM Ratio: {curr_ratio:.3f}, Percentile: {ratio_percentile:.1f}% - Front futures elevated vs mid-term)"
        elif curr_ratio < 0.78 or ratio_percentile < 15:
            curve_state = f"STRONG CONTANGO / ROLL DRAG (VIXY/VIXM Ratio: {curr_ratio:.3f}, Percentile: {ratio_percentile:.1f}% - Upward sloping futures curve, steep roll decay drag)"
        else:
            curve_state = f"NORMAL CONTANGO (VIXY/VIXM Ratio: {curr_ratio:.3f}, Percentile: {ratio_percentile:.1f}% - Upward sloping futures curve)"

        # Check for Canonical Spot VIX (^VIX)
        vix_by_date = {row["fetched_at"][:10]: float(row["price"]) for row in (vix_data or [])}
        spot_vix_dates = sorted(list(set(vix_by_date.keys()) & set(spy_by_date.keys())))

        if len(spot_vix_dates) >= 5:
            vix_prices = [vix_by_date[d] for d in spot_vix_dates]
            vix_returns = [
                (vix_prices[i] - vix_prices[i - 1]) / vix_prices[i - 1] for i in range(1, len(spot_vix_dates))
            ]
            curr_vix = vix_prices[-1]
            vix_1d_return = vix_returns[-1] * 100 if vix_returns else 0.0

            sub_returns_vix = vix_returns[-30:]
            vix_realized_vol = (
                statistics.stdev(sub_returns_vix) * (252**0.5) * 100 if len(sub_returns_vix) >= 2 else 0.0
            )

            smaller_vix = sum(1 for p in vix_prices if p < curr_vix)
            vix_percentile = (smaller_vix / len(vix_prices)) * 100

            sma_10 = sum(vix_prices[-10:]) / min(10, len(vix_prices))
            sma_30 = sum(vix_prices[-30:]) / min(30, len(vix_prices))
            if curr_vix > sma_10 > sma_30:
                trend_state = "STRONG VOLATILITY EXPANSION (VIX > SMA_10 > SMA_30)"
            elif curr_vix < sma_10 < sma_30:
                trend_state = "STRONG VOLATILITY CONTRACTION (VIX < SMA_10 < SMA_30)"
            elif curr_vix > sma_30:
                trend_state = "MODERATE VOLATILITY EXPANSION (VIX > SMA_30)"
            else:
                trend_state = "CONSOLIDATION / MEAN REVERSION"

            # Volatility Regime derived from canonical Spot VIX levels + historical percentile
            if curr_vix >= 30.0 or (curr_vix >= 25.0 and vix_percentile >= 85.0):
                regime = f"🚨 PANIC ZONE / EXTREME FEAR (Spot VIX: {curr_vix:.2f} >= 28-30 or >85th percentile)"
            elif curr_vix >= 20.0 or vix_percentile >= 75.0:
                regime = f"⚠️ ELEVATED VOLATILITY / CAUTION (Spot VIX: {curr_vix:.2f} in 20-30 range)"
            elif curr_vix < 15.0 or vix_percentile <= 15.0:
                regime = f"🟢 COMPLACENCY ZONE / LOW VOLATILITY (Spot VIX: {curr_vix:.2f} < 15 or <15th percentile)"
            else:
                regime = f"NORMAL VOLATILITY / BASELINE REGIME (Spot VIX: {curr_vix:.2f} in 15-20 range)"

            sub_spy_aligned = [spy_by_date[d] for d in spot_vix_dates]
            sub_returns_spy = [
                (sub_spy_aligned[i] - sub_spy_aligned[i - 1]) / sub_spy_aligned[i - 1]
                for i in range(1, len(sub_spy_aligned))
            ][-30:]
            spy_correlation_30d = pearson_correlation(sub_returns_vix, sub_returns_spy)

            spot_vix_block = (
                f"=== Cboe Volatility Index (Spot VIX: ^VIX) ===\n"
                f"- Spot VIX Level:              {curr_vix:.2f} [{vix_1d_return:+.2f}% today]\n"
                f"- Spot VIX {len(vix_prices)}d Percentile:      {vix_percentile:.1f}%\n"
                f"- Spot VIX 30d Realized Vol:   {vix_realized_vol:.2f}%\n"
                f"- Volatility Regime:           {regime}\n"
                f"- Moving Average Trend:        {trend_state}\n"
                f"- Correlation with SPY (30d):  {spy_correlation_30d:+.3f}\n\n"
            )
        else:
            # Fallback if ^VIX is not available
            sub_returns_vixy = vixy_returns[-30:]
            spy_correlation_30d = pearson_correlation(sub_returns_vixy, spy_returns[-30:])
            spot_vix_block = (
                f"=== Cboe Volatility Index (Spot VIX: ^VIX) ===\n"
                f"- Spot VIX: Unavailable (falling back to futures ETF proxy)\n"
                f"- Correlation with SPY (30d):  {spy_correlation_30d:+.3f}\n\n"
            )

        sub_returns_vixy = vixy_returns[-30:]
        vixy_realized_vol = statistics.stdev(sub_returns_vixy) * (252**0.5) * 100 if len(sub_returns_vixy) >= 2 else 0.0
        sub_returns_10d = vixy_returns[-10:]
        vix_vol_of_vol = statistics.stdev(sub_returns_10d) * (252**0.5) * 100 if len(sub_returns_10d) >= 2 else 0.0

        futures_block = (
            f"=== VIX Futures Term Structure & Roll Dynamics ===\n"
            f"- VIXY (Short-Term Futures ETF): ${curr_vixy:.2f} [{vixy_1d_return:+.2f}% today]\n"
            f"- VIXM (Mid-Term Futures ETF):   ${curr_vixm:.2f} [{vixm_1d_return:+.2f}% today]\n"
            f"- VIXY 30d Realized Volatility:  {vixy_realized_vol:.2f}%\n"
            f"- Volatility of Volatility (VVIX Proxy): {vix_vol_of_vol:.2f}%\n"
            f"- Term Structure (VIXY/VIXM):    {curr_ratio:.3f} ({ratio_percentile:.1f}% percentile)\n"
            f"- Futures Curve State:           {curve_state}\n\n"
            f"⚠️ VIX vs VIXY NOTICE: VIXY & VIXM are futures ETFs subject to persistent contango roll decay "
            f"(structural downward price drag over time). Spot VIX (^VIX) is a mean-reverting cash index. "
            f"Never use VIXY share price level as a proxy for market volatility or complacency."
        )

        return spot_vix_block + futures_block
    except Exception as e:
        logger.exception(f"Error in execute_get_volatility_index_details_tool: {e}")
        return f"Error retrieving volatility index details: {str(e)}"


async def execute_macro_economic_series_tool(
    series_id_or_alias: str,
    lookback_periods: int = 12,
    units: str = "lin",
    frequency: str | None = None,
) -> str:
    """Executes the get_macro_economic_series tool to fetch and format FRED macroeconomic data."""
    from core.fred import fetch_fred_series_observations, format_fred_observations_markdown

    try:
        data = await fetch_fred_series_observations(
            series_id_or_alias=series_id_or_alias,
            lookback_periods=lookback_periods,
            units=units,
            frequency=frequency,
        )
        if "error" in data and not data.get("observations"):
            return f"Error retrieving FRED series '{series_id_or_alias}': {data['error']}"

        return format_fred_observations_markdown(
            series_id=data.get("series_id", series_id_or_alias),
            title=data.get("title", series_id_or_alias),
            units=data.get("units", units),
            frequency=data.get("frequency", frequency or "N/A"),
            observations=data.get("observations", []),
        )
    except Exception as e:
        logger.exception("Error executing get_macro_economic_series tool: %s", e)
        return f"Error fetching macroeconomic series '{series_id_or_alias}': {str(e)}"


async def execute_yield_curve_regime_tool() -> str:
    """Executes the get_yield_curve_regime tool to classify macroeconomic monetary flow regime."""
    from analytics.yield_curve import get_yield_curve_regime_report

    try:
        report = await get_yield_curve_regime_report()
        return report.get("markdown") or str(report)
    except Exception as e:
        logger.exception("Error executing get_yield_curve_regime tool: %s", e)
        return f"Error analyzing yield curve regime: {str(e)}"


async def execute_get_today_economic_releases_tool(
    target_date: str | None = None,
    country: str | None = "US",
) -> str:
    """Executes the get_today_economic_releases tool to fetch live economic calendar prints."""
    try:
        from core.economic_releases import get_today_economic_releases_summary

        summary = await get_today_economic_releases_summary(
            target_date=target_date,
            country=country if country else None,
        )
        return summary if summary else "No scheduled or released economic indicators found for the specified criteria."
    except Exception as e:
        logger.exception("Error executing get_today_economic_releases tool: %s", e)
        return f"Error retrieving economic releases: {str(e)}"
