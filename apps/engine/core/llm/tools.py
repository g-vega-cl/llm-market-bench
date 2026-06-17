"""Tool definitions and execution logic for LLMs.

Tool definitions are stored in a single canonical format (OpenAI Chat Completions
function-tool schema). Handlers translate to provider-specific formats via
``to_anthropic`` / ``to_gemini`` at the boundary.
"""

import contextlib

from core.config import logger
from core.db import get_supabase_client
from execution.market_data import MarketDataManager
from memory.embeddings import get_embedding

# =============================================================================
# FORMAT ADAPTERS
# =============================================================================


def _validate_canonical_tool(tool_def: dict) -> dict:
    """Validates a canonical tool definition and extracts its ``function`` dict."""
    fn = tool_def.get("function")
    if fn is None:
        raise KeyError(
            f"Tool definition missing 'function' key (expected canonical OpenAI format): {list(tool_def.keys())!r}"
        )
    if not isinstance(fn, dict):
        raise TypeError(f"'function' must be a dict, got {type(fn).__name__}: {fn!r}")
    missing = [k for k in ("name", "description", "parameters") if k not in fn]
    if missing:
        raise KeyError(f"'function' dict missing required keys {missing}: {list(fn.keys())!r}")
    return fn


def _strip_numeric_constraints(properties: dict) -> dict:
    """Strip ``minimum``/``maximum`` from JSON Schema property definitions.

    Gemini's API may enforce these at the API layer, but Python executors
    already validate ranges internally. Removing them avoids rejecting
    calls that would be valid before this code was unified.
    """
    return {
        name: {k: v for k, v in schema.items() if k not in ("minimum", "maximum")}
        for name, schema in properties.items()
    }


def to_anthropic(tool_def: dict) -> dict:
    """Translate a canonical (OpenAI-format) tool def to Anthropic format.

    Anthropic drops the ``{"type": "function", "function": {...}}`` wrapper
    and renames ``parameters`` to ``input_schema``.
    """
    fn = _validate_canonical_tool(tool_def)
    return {
        "name": fn["name"],
        "description": fn["description"],
        "input_schema": fn["parameters"],
    }


def to_gemini(tool_def: dict) -> dict:
    """Translate a canonical (OpenAI-format) tool def to Gemini format.

    Gemini drops the ``{"type": "function", "function": {...}}`` wrapper
    but keeps the ``parameters`` field name. Numeric constraints
    (``minimum``, ``maximum``) are stripped since Python executors
    handle validation and Gemini may reject constrained calls.
    """
    fn = _validate_canonical_tool(tool_def)
    parameters = fn["parameters"]
    if isinstance(parameters, dict) and "properties" in parameters:
        parameters = {
            **parameters,
            "properties": _strip_numeric_constraints(parameters["properties"]),
        }
    return {
        "name": fn["name"],
        "description": fn["description"],
        "parameters": parameters,
    }


# =============================================================================
# CANONICAL TOOL DEFINITIONS (OpenAI Chat Completions function-tool format)
# =============================================================================

STOCK_TOOL = {
    "type": "function",
    "function": {
        "name": "get_stock_quote",
        "description": ("Get real-time price and market cap for a stock ticker to verify its existence and liquidity."),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., AAPL, TSLA, NVDA)",
                },
            },
            "required": ["ticker"],
        },
    },
}

PRICE_HISTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_price_history",
        "description": "Get historical price and volume data for a stock ticker to see if news is priced in or to check volume indicators (ADV/RVOL).",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to retrieve (default 7).",
                },
            },
            "required": ["ticker"],
        },
    },
}

POSITION_PNL_TOOL = {
    "type": "function",
    "function": {
        "name": "get_position_pnl",
        "description": "Get current unrealized P&L and cost basis for a stock you already own.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol.",
                },
            },
            "required": ["ticker"],
        },
    },
}

VOLATILITY_METRICS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_volatility_metrics",
        "description": (
            "Calculate price volatility metrics and volume context to assess if a "
            "stock is over-extended or has unusual trading activity."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to retrieve (default 14).",
                },
            },
            "required": ["ticker"],
        },
    },
}

SECTOR_ALTERNATIVES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_sector_alternatives",
        "description": "Identify correlated stocks or competitors in the same sector to find less crowded plays.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol.",
                },
            },
            "required": ["ticker"],
        },
    },
}

CALCULATE_BUY_QUANTITY_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_buy_quantity",
        "description": (
            "Calculate how many shares to BUY based on a percentage of your available "
            "buying power (1-100%). This tool automatically enforces the mandatory "
            "10% total equity minimum position size."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol.",
                },
                "percentage": {
                    "type": "integer",
                    "description": "Percentage of available buying power to allocate (1-100).",
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["ticker", "percentage"],
        },
    },
}

CALCULATE_SELL_QUANTITY_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_sell_quantity",
        "description": (
            "Calculate how many shares to SELL based on a percentage of your current "
            "position (1-100%). If the remaining balance would fall below 10% of "
            "total equity, it will recommend a 100% (FULL) sell to avoid dust positions."
            " IMPORTANT: Avoid selling tiny amounts (e.g., 1-5% of position) unless clearing"
            " the entire position. Small sells create dust and are discouraged."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol.",
                },
                "percentage": {
                    "type": "integer",
                    "description": "Percentage of current position to sell (1-100).",
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["ticker", "percentage"],
        },
    },
}

RUN_STOCK_SCREENER_TOOL = {
    "type": "function",
    "function": {
        "name": "run_stock_screener",
        "description": (
            "Screen for stocks using various financial filters. Use this to identify "
            "investable assets when you have a market theme but no specific tickers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "market_cap_more_than": {
                    "type": "number",
                    "description": "Minimum market cap in USD (e.g., 1000000000 for 1B).",
                },
                "market_cap_lower_than": {"type": "number", "description": "Maximum market cap in USD."},
                "price_more_than": {"type": "number", "description": "Minimum stock price."},
                "price_lower_than": {"type": "number", "description": "Maximum stock price."},
                "beta_more_than": {"type": "number", "description": "Minimum beta (volatility relative to market)."},
                "beta_lower_than": {"type": "number", "description": "Maximum beta."},
                "volume_more_than": {"type": "number", "description": "Minimum average daily volume."},
                "volume_lower_than": {"type": "number", "description": "Maximum average daily volume."},
                "dividend_more_than": {"type": "number", "description": "Minimum dividend yield (e.g., 0.02 for 2%)."},
                "dividend_lower_than": {"type": "number", "description": "Maximum dividend yield."},
                "sector": {
                    "type": "string",
                    "description": "Filter by sector (e.g., 'Technology', 'Healthcare', 'Energy', 'Financial Services').",
                },
                "industry": {
                    "type": "string",
                    "description": "Filter by specific industry (e.g., 'Software—Infrastructure', 'Semiconductors').",
                },
                "exchange": {
                    "type": "string",
                    "description": "Filter by exchange (default: 'NYSE,NASDAQ'). Use 'NYSE,NASDAQ,AMEX' for broad US coverage.",
                },
                "limit": {"type": "integer", "description": "Maximum number of results (default 10, max 15)."},
            },
        },
    },
}

SEARCH_RELATED_TICKERS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_related_tickers",
        "description": (
            "Given a market theme or event, identify relevant stock tickers or ETFs that would be most impacted."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "description": "The market theme, concept, or event (e.g., 'Private Credit', 'AI demand surge').",
                },
            },
            "required": ["theme"],
        },
    },
}

FIND_UNCORRELATED_ASSETS_TOOL = {
    "type": "function",
    "function": {
        "name": "find_uncorrelated_assets",
        "description": (
            "Find asset pairs with low correlation and positive 90-day momentum. "
            "Useful for building diversified portfolios with uncorrelated assets. "
            "Returns pairs sorted by correlation (lowest first) that have positive returns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "max_correlation": {
                    "type": "number",
                    "description": "Maximum absolute correlation to include (0.0 to 1.0). Default 0.3. Lower values = more uncorrelated.",
                },
                "min_return": {
                    "type": "number",
                    "description": "Minimum 90-day return for both assets in percentage. Default 0.0.",
                },
                "method": {
                    "type": "string",
                    "enum": ["pearson", "spearman"],
                    "description": "Correlation method: 'pearson' (linear) or 'spearman' (rank-based). Default 'pearson'.",
                },
            },
        },
    },
}

GET_KEY_METRICS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_key_metrics",
        "description": (
            "Get fundamental financial key metrics (P/E ratio, PEG ratio, Debt-to-Equity, "
            "ROE, margins, etc.) for a stock ticker to assess valuation and financial health."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., AAPL, TSLA, NVDA)",
                },
                "period": {
                    "type": "string",
                    "enum": ["annual", "quarter"],
                    "description": "The period for key metrics: 'annual' or 'quarter' (default: 'annual').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of periods of history to retrieve (default: 2).",
                },
            },
            "required": ["ticker"],
        },
    },
}

GET_MARKET_HEALTH_BAROMETER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_market_health_barometer",
        "description": (
            "Fetch recent historical and current daily S&P 500 aggregate valuation "
            "and earnings metrics (aggregate PE ratio, Forward PE ratio, PB ratio, "
            "PS ratio, and earnings surprise beat rate) to assess broad market health and valuation regimes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of daily historical snapshots to retrieve (default: 5).",
                },
            },
            "required": [],
        },
    },
}

GET_EARNINGS_HISTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_earnings_history",
        "description": (
            "Retrieve historical earnings reports (actual vs. estimated EPS/revenue, surprise percentages) "
            "and check for the upcoming earnings announcement date for a specific stock ticker."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., AAPL, NVDA, TSLA)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent reports to retrieve (default: 8).",
                },
            },
            "required": ["ticker"],
        },
    },
}


SEARCH_PREDICTION_MARKETS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_prediction_markets",
        "description": (
            "Search for high-volume, classification-filtered active prediction markets "
            "(politics, economics, technology) stored in our database. Use this tool to "
            "find relevant markets to analyze sentiment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or search terms (e.g., 'inflation', 'fed rate cut', 'subsidies')",
                },
                "platform": {
                    "type": "string",
                    "enum": ["polymarket", "kalshi"],
                    "description": "Optional platform to filter search results ('polymarket' or 'kalshi').",
                },
            },
            "required": ["query"],
        },
    },
}

GET_PREDICTION_MARKET_ODDS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_prediction_market_odds",
        "description": (
            "Fetch real-time yes/no odds and metadata for a specific prediction market "
            "directly from the live Polymarket or Kalshi APIs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "market_id": {
                    "type": "string",
                    "description": "The unique market ID or ticker (e.g., Kalshi ticker 'FCUTJUN26' or Polymarket token ID).",
                },
                "platform": {
                    "type": "string",
                    "enum": ["polymarket", "kalshi"],
                    "description": "The platform hosting the market ('polymarket' or 'kalshi').",
                },
            },
            "required": ["market_id", "platform"],
        },
    },
}


# =============================================================================
# TOOL EXECUTION
# =============================================================================


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


async def execute_position_pnl_tool(ticker: str, owner_id: str) -> str:
    """Fetches current position P&L for the specific owner."""
    client = get_supabase_client()
    try:
        ticker = ticker.upper()
        res = client.table("position_pnl").select("*").eq("ticker", ticker).eq("owner_id", owner_id).execute()

        if not res.data:
            return f"You do not currently own a position in {ticker}."

        pos = res.data[0]
        return (
            f"Position for {ticker}:\n"
            f"- Quantity: {pos['quantity']}\n"
            f"- Avg Cost Basis: ${float(pos['average_cost_basis']):.2f}\n"
            f"- Current Price: ${float(pos['current_price']):.2f}\n"
            f"- Unrealized P&L: ${float(pos['unrealized_pnl_usd']):,.2f} ({float(pos['unrealized_pnl_pct']):.2f}%)"
        )
    except Exception as e:
        return f"Error fetching position P&L for {ticker}: {str(e)}"


async def execute_volatility_metrics_tool(ticker: str, days: int = 14) -> str:
    """Calculates volatility metrics and volume context for a ticker."""
    manager = MarketDataManager()
    try:
        data = await manager.get_history(ticker, days)

        if not data or len(data) < 2:
            return f"Insufficient historical data for {ticker} to calculate volatility."

        curr = data[0]["price"]
        prices = [p["price"] for p in data]

        import statistics

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


def compute_volume_context(history: list[dict]) -> str:
    """
    Compute human-readable volume context from price history.
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

        enriched_results = []
        for item in results:
            ticker = item.get("symbol")
            if ticker:
                history = await manager.get_history(ticker, days=20)
                vol_context = compute_volume_context(history) if history else "no volume data"
            else:
                vol_context = "unknown"
            enriched_results.append({**item, "volume_context": vol_context})

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


async def execute_sector_alternatives_tool(ticker: str) -> str:
    """Identifies sector alternatives for a ticker using vector search on past decisions."""
    client = get_supabase_client()
    try:
        ticker = ticker.upper()

        query_text = f"Market analysis and trading decision for {ticker} stock in this sector"
        embedding = get_embedding(query_text)

        if not embedding:
            return f"Could not generate embedding for {ticker} to find alternatives."

        res = client.rpc(
            "match_decisions",
            {
                "query_embedding": embedding,
                "match_threshold": 0.5,
                "match_count": 10,
            },
        ).execute()

        related_tickers = set()
        if res.data:
            for item in res.data:
                t = item.get("ticker")
                if t and t != ticker:
                    related_tickers.add(t)

        if not related_tickers:
            mem_res = client.table("memories").select("content").ilike("content", f"%{ticker}%").limit(5).execute()

            if mem_res.data:
                return f"No direct competitors found in decision history, but {ticker} appears in recent market events. Consider searching for standard competitors manually."

            return f"No alternative plays found for {ticker}."

        alts = list(related_tickers)[:5]
        return f"Sector Alternatives / Related Plays for {ticker} (based on history): {', '.join(alts)}"
    except Exception as e:
        return f"Error finding alternatives for {ticker}: {str(e)}"


async def execute_buy_quantity_tool(ticker: str, owner_id: str, percentage: int) -> str:
    """Calculates buy quantity with 10% equity floor enforcement."""
    from execution.portfolio import Portfolio

    ticker = ticker.upper()
    portfolio = Portfolio(owner_id)
    await portfolio.initialize()

    manager = MarketDataManager()
    try:
        quote = await manager.get_quote(ticker)
        if not quote or not quote.exists:
            return f"Error: Ticker '{ticker}' not found."

        price = quote.price

        current_prices = {t: p.average_cost_basis for t, p in portfolio.positions.items()}
        current_prices[ticker] = price

        metrics = portfolio.calculate_reg_t_metrics(current_prices)

        equity_floor_usd = metrics.total_equity * 0.10

        target_value_usd = metrics.buying_power * (percentage / 100.0)

        final_target_usd = target_value_usd
        compliance_note = ""

        if target_value_usd < equity_floor_usd:
            final_target_usd = equity_floor_usd
            compliance_note = (
                f"\nNOTE: Your requested {percentage}% allocation (${target_value_usd:,.2f}) was below the "
                f"10% Total Equity Floor (${equity_floor_usd:,.2f}). This tool has automatically "
                f"upsized your request to meet the minimum required position size."
            )

        if final_target_usd > metrics.buying_power:
            final_target_usd = metrics.buying_power
            compliance_note += f"\nWARNING: Insufficient Buying Power to meet the preferred allocation. Capped at ${metrics.buying_power:,.2f}."

        quantity = int(final_target_usd / price)

        if quantity == 0 and final_target_usd > 0:
            quantity = 1

        actual_cost = quantity * price

        status = "COMPLIANT ✅" if actual_cost >= equity_floor_usd else "INSUFFICIENT FUNDS ❌"

        return (
            f"BUY CALCULATION COMPLETE for {ticker}:\n"
            f"- Current Price: ${price:.2f}\n"
            f"- Total Buying Power: ${metrics.buying_power:,.2f}\n"
            f"- 10% Total Equity Floor: ${equity_floor_usd:,.2f}\n"
            f"- Recommended BUY Quantity: {quantity} shares (Est. Cost: ${actual_cost:,.2f})\n"
            f"- Status: {status}{compliance_note}\n\n"
            f"MANDATORY ACTION: Set your decision to 'BUY' for ticker '{ticker}' with quantity: {quantity}. "
            f"You MUST include 'buy_tool_called': true in your final JSON decision."
        )
    except Exception as e:
        return f"Error calculating buy quantity for {ticker}: {str(e)}"


async def execute_sell_quantity_tool(ticker: str, owner_id: str, percentage: int) -> str:
    """Calculates sell quantity with 10% equity 'dust' check."""
    from execution.portfolio import Portfolio

    client = get_supabase_client()

    ticker = ticker.upper()
    portfolio = Portfolio(owner_id)
    await portfolio.initialize()

    MarketDataManager()

    try:
        res = client.table("position_pnl").select("*").eq("ticker", ticker).eq("owner_id", owner_id).execute()

        if not res.data:
            return f"Error: You do not currently own a position in {ticker}."

        pos_data = res.data[0]
        total_shares = int(pos_data["quantity"])
        price = float(pos_data["current_price"])

        current_prices = {t: p.average_cost_basis for t, p in portfolio.positions.items()}
        current_prices[ticker] = price
        metrics = portfolio.calculate_reg_t_metrics(current_prices)
        equity_floor_usd = metrics.total_equity * 0.10

        sell_shares = int(total_shares * (percentage / 100.0))
        remaining_shares = total_shares - sell_shares
        remaining_value = remaining_shares * price

        compliance_note = ""
        if remaining_shares > 0 and remaining_value < equity_floor_usd:
            sell_shares = total_shares
            remaining_shares = 0
            compliance_note = (
                f"\nWARNING: Selling {percentage}% would leave a position worth ${remaining_value:,.2f}, "
                f"which is below your 10% Equity Floor (${equity_floor_usd:,.2f}). "
                f"To prevent 'dust' positions, this tool has mandated a 100% (FULL) sell."
            )

        if sell_shares == 0 and percentage > 0:
            sell_shares = 1

        sell_shares = min(sell_shares, total_shares)

        return (
            f"SELL CALCULATION COMPLETE for {ticker}:\n"
            f"- Current Holdings: {total_shares} shares\n"
            f"- Recommended SELL Quantity: {sell_shares} shares\n"
            f"- Remaining Position: {remaining_shares} shares{compliance_note}\n\n"
            f"MANDATORY ACTION: Set your decision to 'SELL' for ticker '{ticker}' with quantity: {sell_shares}. "
            f"You MUST include 'sell_tool_called': true in your final JSON decision."
        )

    except Exception as e:
        return f"Error calculating sell quantity for {ticker}: {str(e)}"


async def execute_search_related_tickers_tool(theme: str) -> str:
    """Uses LLM to search for tickers related to a theme."""
    from core.config import GEMINI_MODEL
    from core.llm.clients import get_gemini_client
    from core.llm.prompt_factory import PromptFactory
    from core.models import TickerSuggestion

    client = get_gemini_client()
    try:
        messages = PromptFactory.build_ticker_suggestion_messages(provider="gemini", event_summary=theme)

        resp = client.chat.completions.create(model=GEMINI_MODEL, response_model=TickerSuggestion, messages=messages)
        import asyncio

        if asyncio.iscoroutine(resp):
            resp = await resp

        return f"Suggested Tickers for '{theme}': {', '.join(resp.tickers)}\nReasoning: {resp.reasoning}"
    except Exception as e:
        return f"Error suggesting tickers for '{theme}': {str(e)}"


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
        runs = client.table("correlation_runs").select("id").order("run_date", ascending=False).limit(1).execute()

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


async def execute_key_metrics_tool(ticker: str, period: str = "annual", limit: int = 2) -> str:
    """Fetches fundamental financial key metrics for a ticker to help analyze valuation/health."""
    manager = MarketDataManager()
    try:
        data = await manager.get_key_metrics(ticker, period, limit)

        if not data:
            return f"No fundamental key metrics found for {ticker}."

        output = f"Fundamental Key Metrics for {ticker} ({period.capitalize()} periods, recent first):\n"
        for i, entry in enumerate(data, 1):
            date_str = entry.get("date") or "N/A"
            period_str = entry.get("period") or "N/A"
            year_str = entry.get("calendarYear") or "N/A"

            output += f"\n--- Period {i}: {period_str} {year_str} (Date: {date_str}) ---\n"

            # Helper to safely format decimal/float metrics
            def fmt(val, percentage=False):
                if val is None:
                    return "N/A"
                if percentage:
                    return f"{val * 100:.2f}%"
                return f"{val:.2f}"

            output += f"- P/E Ratio: {fmt(entry.get('peRatio'))}\n"
            output += f"- Price/Sales Ratio: {fmt(entry.get('priceToSalesRatio'))}\n"
            output += f"- Price/Book Ratio: {fmt(entry.get('pbRatio'))}\n"
            output += f"- EV/EBITDA: {fmt(entry.get('enterpriseValueOverEBITDA'))}\n"
            output += f"- Debt/Equity: {fmt(entry.get('debtToEquity'))}\n"
            output += f"- Current Ratio: {fmt(entry.get('currentRatio'))}\n"
            output += f"- ROE: {fmt(entry.get('roe'), percentage=True)}\n"
            output += f"- Dividend Yield: {fmt(entry.get('dividendYield'), percentage=True)}\n"
            output += f"- Free Cash Flow Yield: {fmt(entry.get('freeCashFlowYield'), percentage=True)}\n"
            output += f"- Book Value Per Share: ${fmt(entry.get('bookValuePerShare'))}\n"
            output += f"- Revenue Per Share: ${fmt(entry.get('revenuePerShare'))}\n"
            if "netIncomePerShare" in entry:
                output += f"- Net Income Per Share: ${fmt(entry.get('netIncomePerShare'))}\n"
            if "freeCashFlowPerShare" in entry:
                output += f"- Free Cash Flow Per Share: ${fmt(entry.get('freeCashFlowPerShare'))}\n"

        return output
    except Exception as e:
        return f"Error fetching key metrics for {ticker}: {str(e)}"


async def execute_market_health_barometer_tool(limit: int = 5) -> str:
    """Fetches S&P 500 aggregate valuation and earnings metrics from Supabase."""
    try:
        from core.db import get_supabase_client
        client = get_supabase_client()
        res = client.table("market_barometer_history").select("*").order("date", desc=True).limit(limit).execute()
        
        if not res.data:
            return "No S&P 500 Market Health Barometer data found."
            
        output = f"S&P 500 Aggregate Market Health Barometer (Recent {len(res.data)} daily snapshots):\n"
        for entry in res.data:
            date_str = entry.get("date") or "N/A"
            pe = entry.get("pe_ratio")
            fwd_pe = entry.get("forward_pe")
            pb = entry.get("pb_ratio")
            ps = entry.get("ps_ratio")
            surprise = entry.get("earnings_surprise_momentum")
            
            pe_val = f"{float(pe):.2f}" if pe is not None else "N/A"
            fwd_pe_val = f"{float(fwd_pe):.2f}" if fwd_pe is not None else "N/A"
            pb_val = f"{float(pb):.2f}" if pb is not None else "N/A"
            ps_val = f"{float(ps):.2f}" if ps is not None else "N/A"
            surprise_val = f"{float(surprise):.1f}%" if surprise is not None else "N/A"
            
            output += f"\n- Date: {date_str}\n"
            output += f"  * Aggregate Trailing P/E: {pe_val}\n"
            output += f"  * Aggregate Forward P/E:  {fwd_pe_val}\n"
            output += f"  * Aggregate P/S Ratio:   {ps_val}\n"
            output += f"  * Aggregate P/B Ratio:   {pb_val}\n"
            output += f"  * Earnings Beat Rate:     {surprise_val} of companies beating expectations\n"
            
        return output
    except Exception as e:
        logger.exception("Error executing get_market_health_barometer tool")
        return f"Error retrieving barometer data: {str(e)}"


async def execute_earnings_history_tool(ticker: str, limit: int = 8) -> str:
    """Fetches earnings history and upcoming calendar info for a ticker."""
    manager = MarketDataManager()
    try:
        data = await manager.get_earnings_history(ticker, limit)
        if not data:
            return f"No earnings history or upcoming reports found for {ticker}."

        output = f"Earnings History and Calendar for {ticker.upper()}:\n"
        
        upcoming = [e for e in data if e.get("isUpcoming")]
        past = [e for e in data if not e.get("isUpcoming")]

        if upcoming:
            output += "\n--- Upcoming Earnings Announcement ---\n"
            for entry in upcoming:
                est_eps = f"${entry['epsEstimated']:.2f}" if entry.get('epsEstimated') is not None else "N/A"
                est_rev = f"${entry['revenueEstimated'] / 1e9:.2f}B" if entry.get('revenueEstimated') is not None else "N/A"
                output += f"- Date: {entry['date']} | Estimated EPS: {est_eps} | Estimated Revenue: {est_rev}\n"

        if past:
            output += "\n--- Historical Earnings Reports (Recent first) ---\n"
            for entry in past:
                act_eps = f"${entry['epsActual']:.2f}" if entry.get('epsActual') is not None else "N/A"
                est_eps = f"${entry['epsEstimated']:.2f}" if entry.get('epsEstimated') is not None else "N/A"
                act_rev = f"${entry['revenueActual'] / 1e9:.2f}B" if entry.get('revenueActual') is not None else "N/A"
                est_rev = f"${entry['revenueEstimated'] / 1e9:.2f}B" if entry.get('revenueEstimated') is not None else "N/A"
                
                surprise = entry.get('surprisePct')
                surprise_str = f"{surprise:+.2f}%" if surprise is not None else "N/A"
                
                output += f"- Date: {entry['date']}\n"
                output += f"  * EPS: Actual {act_eps} vs Estimate {est_eps} (Surprise: {surprise_str})\n"
                output += f"  * Revenue: Actual {act_rev} vs Estimate {est_rev}\n"

        return output
    except Exception as e:
        logger.exception(f"Error executing get_earnings_history tool for {ticker}")
        return f"Error retrieving earnings history for {ticker}: {str(e)}"


async def execute_search_prediction_markets_tool(query: str, platform: str | None = None) -> str:
    """Search for active prediction markets in the database.

    Args:
        query: Keyword or search term.
        platform: Optional platform filter ('polymarket' or 'kalshi').

    Returns:
        Formatted string containing matching markets.
    """
    client = get_supabase_client()
    try:
        db_query = client.table("prediction_market_snapshots").select("*").eq("is_active", True)
        if platform:
            db_query = db_query.eq("platform", platform)

        # Use ilike for Postgres-side case-insensitive keyword search
        db_query = db_query.ilike("question", f"%{query}%")

        res = db_query.execute()

        if not res.data:
            return f"No active prediction markets found matching '{query}'."

        # Sort by volume descending
        sorted_markets = sorted(res.data, key=lambda x: x.get("volume_usd") or 0, reverse=True)

        output = f"Active Prediction Markets matching '{query}' (sorted by volume, highest first):\n\n"
        for i, market in enumerate(sorted_markets[:10], 1):
            yes_pct = float(market.get("yes_odds") or 0) * 100
            no_pct = float(market.get("no_odds") or 0) * 100
            volume = market.get("volume_usd") or 0

            output += (
                f"{i}. {market['question']} [{market['platform'].upper()} ID: {market['market_id']}]\n"
                f"   Category: {market['category']} | Volume: ${volume:,.2f}\n"
                f"   Current Odds: YES {yes_pct:.1f}% / NO {no_pct:.1f}%\n"
            )
            if market.get("ends_at"):
                output += f"   Ends At: {market['ends_at']}\n"
            output += "\n"

        return output.strip()
    except Exception as e:
        return f"Error searching prediction markets for '{query}': {str(e)}"


async def execute_get_prediction_market_odds_tool(market_id: str, platform: str) -> str:
    """Fetch real-time yes/no odds for a prediction market directly from the live API.

    Args:
        market_id: Unique market identifier or ticker.
        platform: 'polymarket' or 'kalshi'.

    Returns:
        Formatted string with real-time odds and details.
    """
    import httpx

    if platform.lower() == "polymarket":
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    # Fallback to query param
                    resp = await client.get(f"https://gamma-api.polymarket.com/markets?id={market_id}")
                    resp.raise_for_status()
                    data_list = resp.json()
                    if not data_list:
                        return f"Polymarket market '{market_id}' not found."
                    market_data = data_list[0]
                else:
                    resp.raise_for_status()
                    market_data = resp.json()

            question = market_data.get("question") or "Unknown Question"
            volume = float(market_data.get("volume") or 0)

            # Polymarket prices represent cents/probability (e.g. 0.52 = 52%)
            yes_price = market_data.get("outcomePrices")
            yes_pct = 0.0
            if yes_price and isinstance(yes_price, list) and len(yes_price) > 0:
                with contextlib.suppress(ValueError, TypeError):
                    yes_pct = float(yes_price[0]) * 100
            no_pct = 100.0 - yes_pct

            output = (
                f"Polymarket Live Data:\n"
                f"- Question: {question}\n"
                f"- Market ID: {market_id}\n"
                f"- Category: {market_data.get('category', 'N/A')}\n"
                f"- Current Odds: YES {yes_pct:.1f}% / NO {no_pct:.1f}%\n"
                f"- Total Volume: ${volume:,.2f}\n"
            )
            if market_data.get("end_date_iso"):
                output += f"- Ends At: {market_data['end_date_iso']}\n"
            return output.strip()

        except Exception as e:
            return f"Error fetching live Polymarket odds for '{market_id}': {str(e)}"

    elif platform.lower() == "kalshi":
        url = f"https://external-api.kalshi.com/trade-api/v2/markets/{market_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                market_data = resp.json().get("market") or resp.json()

            question = market_data.get("title") or "Unknown Title"
            volume = float(market_data.get("volume", 0))

            # Kalshi yields yes/no prices in cents (e.g. 52 = 52%)
            yes_price = float(market_data.get("yes_bid") or market_data.get("last_price") or 0)
            no_price = float(market_data.get("no_bid") or (100 - yes_price) or 0)

            output = (
                f"Kalshi Live Data:\n"
                f"- Question: {question}\n"
                f"- Ticker: {market_id}\n"
                f"- Status: {market_data.get('status', 'N/A')}\n"
                f"- Current Odds: YES {yes_price:.1f}% / NO {no_price:.1f}%\n"
                f"- Volume: {volume:,.0f} contracts\n"
            )
            if market_data.get("expiration_time"):
                output += f"- Expiration: {market_data['expiration_time']}\n"
            return output.strip()

        except Exception as e:
            return f"Error fetching live Kalshi odds for '{market_id}': {str(e)}"

    else:
        return f"Unsupported prediction market platform: '{platform}'."
