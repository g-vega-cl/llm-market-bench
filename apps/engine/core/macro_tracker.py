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
    "Equities": {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "DIA": "Dow Jones", "IWM": "Russell 2000"},
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

    context_lines.append(
        "\n**Instruction:** Use this snapshot to understand if markets are risk-on, risk-off, or experiencing "
        "abnormal volatility. Do not bet against severe macro trends without an extraordinary catalyst."
    )

    return "\n".join(context_lines)
