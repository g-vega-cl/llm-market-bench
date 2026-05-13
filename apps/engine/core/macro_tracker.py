"""Global Macro Tracker

This module continuously tracks bond yields globally, commodity prices, 
international market performance, interest rates, and the DXY (Dollar Index).
It calculates daily percentage changes and 30-day volatility to flag unusual market movements,
providing vital contextual "regime" awareness to the LLM prior to decision-making.
"""

import logging
import math

logger = logging.getLogger("engine")

# The default list of macro tickers to track
MACRO_TICKERS = {
    "Equities": {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq 100",
        "DIA": "Dow Jones",
        "IWM": "Russell 2000"
    },
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
    """Fetches macro context including daily % change and 30-day volatility.
    
    Args:
        market_data_manager: Instance of MarketDataManager
        
    Returns:
        str: A human-readable text block detailing current global macro environment.
    """
    logger.info("Gathering Global Macro Context...")
    
    # Flatten all tickers into a single list to batch fetch quotes
    all_tickers = []
    for category, items in MACRO_TICKERS.items():
        all_tickers.extend(items.keys())
        
    # Batch fetch current quotes
    quotes = await market_data_manager.get_quotes(all_tickers)
    
    context_lines = ["\n--- GLOBAL MACRO ENVIRONMENT ---"]
    context_lines.append("The following indicators describe the underlying market 'regime' for today:")
    
    for category, category_dict in MACRO_TICKERS.items():
        context_lines.append(f"\n[ {category.upper()} ]")
        for ticker, name in category_dict.items():
            quote = quotes.get(ticker)
            if not quote or not quote.exists or math.isnan(quote.price):
                continue
                
            # Fetch up to 30 days of history to compute stdev and prev close
            history = await market_data_manager.get_history(ticker, days=30)
            
            if len(history) < 2:
                # Fallback if no history
                context_lines.append(f"{name} ({ticker}): {quote.price:.2f} | (No history available)")
                continue
                
            # Calculate daily % returns over the available history
            returns = []
            for i in range(len(history) - 1):
                prev = history[i+1]["price"]
                curr = history[i]["price"]
                if prev > 0:
                    returns.append((curr - prev) / prev)
            
            # Today's move (current quote vs yesterday's close)
            yesterday_close = history[0]["price"] if history else quote.price
            # If quote.price matches history[0], we are closed (or very stale). If not, we take current quote.
            # To be safe against weekends, just compare quote price to history[0] (or history[1] if quote = history[0])
            if abs(quote.price - history[0]["price"]) < 0.001 and len(history) > 1:
                # Market is closed, so 'today's' move is history[0] vs history[1]
                yesterday_close = history[1]["price"]
                today_px = history[0]["price"]
            else:
                today_px = quote.price
                
            if yesterday_close > 0:
                today_pct_change = ((today_px - yesterday_close) / yesterday_close) * 100
            else:
                today_pct_change = 0.0
                
            # Compute standard deviation
            if len(returns) > 2:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
                stdev_pct = math.sqrt(variance) * 100
                
                # Compare absolute change to stdev
                if abs(today_pct_change) > (2.0 * stdev_pct):
                    regime_flag = "⚠️ HIGHLY UNUSUAL (Regime Shift)"
                elif abs(today_pct_change) > (1.5 * stdev_pct):
                    regime_flag = "❗ UNUSUAL"
                else:
                    regime_flag = "Normal"
                    
                context_lines.append(
                    f"{name} ({ticker}): {today_px:.2f} "
                    f"[{today_pct_change:+.2f}% today] "
                    f"| {regime_flag} (30d stdev: {stdev_pct:.2f}%)"
                )
            else:
                context_lines.append(f"{name} ({ticker}): {today_px:.2f} [{today_pct_change:+.2f}% today]")
                
    context_lines.append(
        "\n**Instruction:** Use this snapshot to understand if markets are risk-on, risk-off, or experiencing "
        "abnormal volatility. Do not bet against severe macro trends without an extraordinary catalyst."
    )
    
    return "\n".join(context_lines)
