"""Global Macro Tracker

This module continuously tracks bond yields globally, commodity prices,
international market performance, interest rates, and the DXY (Dollar Index).
It calculates daily percentage changes and 30-day volatility to flag unusual market movements,
providing vital contextual "regime" awareness to the LLM prior to decision-making.
"""

import logging

logger = logging.getLogger("engine")

# The default list of macro tickers to track
MACRO_TICKERS = {
    "Equities": {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "DIA": "Dow Jones", "IWM": "Russell 2000", "LIN": "Linde plc"},
    "International": {
        "EWJ": "Japan",
        "EWY": "South Korea",
        "VGK": "Europe",
        "MCHI": "China",
        "EEM": "Emerging Markets",
        "EWU": "United Kingdom",
        "EWC": "Canada",
        "INDA": "India",
    },
    "Commodities": {
        "GLD": "Gold",
        "SLV": "Silver",
        "CPER": "Copper",
        "USO": "Oil (WTI)",
        "UNG": "Natural Gas",
    },
    "Fixed Income": {
        "IEF": "7-10yr Treasury",
        "TLT": "20+yr Treasury",
        "TIP": "TIPS (Inflation)",
    },
    "FX & Risk": {
        "UUP": "US Dollar Index",
        "VIXY": "Volatility Index",
    },
    "Crypto": {
        "BTCUSD": "Bitcoin",
    },
}


async def get_global_macro_context(market_data_manager) -> str:
    """Fetches macro context including daily % change and 30-day volatility from cache.

    Args:
        market_data_manager: Instance of MarketDataManager

    Returns:
        str: A human-readable text block detailing current global macro environment.
    """
    logger.info("Gathering Global Macro Context...")

    # Fetch S&P 500 Market Health Barometer
    barometer_block = ""
    try:
        res_baro = (
            market_data_manager.client.table("market_barometer_history")
            .select("*")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        if res_baro.data:
            baro = res_baro.data[0]
            pe = float(baro["pe_ratio"]) if baro.get("pe_ratio") is not None else None
            fwd_pe = float(baro["forward_pe"]) if baro.get("forward_pe") is not None else None
            pb = float(baro["pb_ratio"]) if baro.get("pb_ratio") is not None else None
            ps = float(baro["ps_ratio"]) if baro.get("ps_ratio") is not None else None
            beat_rate = (
                float(baro["earnings_surprise_momentum"])
                if baro.get("earnings_surprise_momentum") is not None
                else None
            )

            pe_str = f"{pe:.2f}" if pe is not None else "N/A"
            fwd_pe_str = f"{fwd_pe:.2f}" if fwd_pe is not None else "N/A"
            pb_str = f"{pb:.2f}" if pb is not None else "N/A"
            ps_str = f"{ps:.2f}" if ps is not None else "N/A"
            beat_str = f"{beat_rate:.1f}%" if beat_rate is not None else "N/A"

            barometer_block = (
                f"\n[ S&P 500 MARKET HEALTH BAROMETER (Date: {baro.get('date')}) ]\n"
                f"- Aggregate Trailing P/E: {pe_str}\n"
                f"- Aggregate Forward P/E:  {fwd_pe_str}\n"
                f"- Aggregate P/S Ratio:   {ps_str}\n"
                f"- Aggregate P/B Ratio:   {pb_str}\n"
                f"- Earnings Beat Rate:     {beat_str} of companies beat estimates in the recent quarter"
            )
    except Exception as e:
        logger.warning(f"Failed to fetch S&P 500 Market Health Barometer: {e}")

    # Flatten all tickers into a single list to batch fetch
    all_tickers = []
    for _category, items in MACRO_TICKERS.items():
        all_tickers.extend(items.keys())

    try:
        # Fetch pre-calculated macro stats directly from the database cache in one query
        res = market_data_manager.client.table("market_data_cache").select("*").in_("ticker", all_tickers).execute()
        cache_map = {row["ticker"]: row for row in res.data} if res.data else {}
    except Exception as e:
        logger.error(f"Failed to fetch pre-calculated macro statistics: {e}")
        cache_map = {}

    context_lines = ["\n--- GLOBAL MACRO ENVIRONMENT ---"]
    context_lines.append("The following indicators describe the underlying market 'regime' for today:")
    if barometer_block:
        context_lines.append(barometer_block)

    for category, category_dict in MACRO_TICKERS.items():
        context_lines.append(f"\n[ {category.upper()} ]")
        for ticker, name in category_dict.items():
            row = cache_map.get(ticker)
            if not row:
                continue

            price = float(row.get("price") or 0.0)
            today_pct_change = float(row.get("today_pct_change") or 0.0)
            stdev_pct = float(row.get("stdev_pct") or 0.0)
            regime_flag = row.get("regime_flag") or "Normal"

            if stdev_pct > 0:
                flag_text = regime_flag
                if regime_flag == "⚠️ HIGHLY UNUSUAL":
                    flag_text = "⚠️ HIGHLY UNUSUAL (Regime Shift)"

                context_lines.append(
                    f"{name} ({ticker}): {price:.2f} "
                    f"[{today_pct_change:+.2f}% today] "
                    f"| {flag_text} (30d stdev: {stdev_pct:.2f}%)"
                )
            else:
                context_lines.append(f"{name} ({ticker}): {price:.2f} [{today_pct_change:+.2f}% today]")

    return "\n".join(context_lines)
