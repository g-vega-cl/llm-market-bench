"""Tool definitions and execution logic for LLMs.

Tool definitions are stored in a single canonical format (OpenAI Chat Completions
function-tool schema). Handlers translate to provider-specific formats via
``to_anthropic`` / ``to_gemini`` at the boundary.
"""


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
            f"Tool definition missing 'function' key "
            f"(expected canonical OpenAI format): {list(tool_def.keys())!r}"
        )
    if not isinstance(fn, dict):
        raise TypeError(
            f"'function' must be a dict, got {type(fn).__name__}: {fn!r}"
        )
    missing = [k for k in ("name", "description", "parameters") if k not in fn]
    if missing:
        raise KeyError(
            f"'function' dict missing required keys {missing}: {list(fn.keys())!r}"
        )
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
        "description": (
            "Get real-time price and market cap for a stock ticker to verify "
            "its existence and liquidity."
        ),
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
        "description": "Get historical price data for a stock ticker to see if news is priced in.",
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
                "market_cap_more_than": {"type": "number", "description": "Minimum market cap in USD (e.g., 1000000000 for 1B)."},
                "market_cap_lower_than": {"type": "number", "description": "Maximum market cap in USD."},
                "price_more_than": {"type": "number", "description": "Minimum stock price."},
                "price_lower_than": {"type": "number", "description": "Maximum stock price."},
                "beta_more_than": {"type": "number", "description": "Minimum beta (volatility relative to market)."},
                "beta_lower_than": {"type": "number", "description": "Maximum beta."},
                "volume_more_than": {"type": "number", "description": "Minimum average daily volume."},
                "volume_lower_than": {"type": "number", "description": "Maximum average daily volume."},
                "dividend_more_than": {"type": "number", "description": "Minimum dividend yield (e.g., 0.02 for 2%)."},
                "dividend_lower_than": {"type": "number", "description": "Maximum dividend yield."},
                "sector": {"type": "string", "description": "Filter by sector (e.g., 'Technology', 'Healthcare', 'Energy', 'Financial Services')."},
                "industry": {"type": "string", "description": "Filter by specific industry (e.g., 'Software—Infrastructure', 'Semiconductors')."},
                "exchange": {"type": "string", "description": "Filter by exchange (default: 'NYSE,NASDAQ'). Use 'NYSE,NASDAQ,AMEX' for broad US coverage."},
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
            "Given a market theme or event, identify relevant stock tickers or ETFs "
            "that would be most impacted."
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
            history_str += f"- {entry['fetched_at']}: ${entry['price']:.2f}\n"

        return history_str
    except Exception as e:
        return f"Error fetching price history for {ticker}: {str(e)}"


async def execute_position_pnl_tool(ticker: str, owner_id: str) -> str:
    """Fetches current position P&L for the specific owner."""
    client = get_supabase_client()
    try:
        ticker = ticker.upper()
        res = client.table("position_pnl") \
            .select("*") \
            .eq("ticker", ticker) \
            .eq("owner_id", owner_id) \
            .execute()

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
    is_actively_trading: bool = True
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
            is_actively_trading=is_actively_trading
        )

        if not results:
            return "No stocks found matching the criteria."

        enriched_results = []
        for item in results:
            ticker = item.get('symbol')
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
            }
        ).execute()

        related_tickers = set()
        if res.data:
            for item in res.data:
                t = item.get("ticker")
                if t and t != ticker:
                    related_tickers.add(t)

        if not related_tickers:
            mem_res = client.table("memories") \
                .select("content") \
                .ilike("content", f"%{ticker}%") \
                .limit(5) \
                .execute()

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
        res = client.table("position_pnl") \
            .select("*") \
            .eq("ticker", ticker) \
            .eq("owner_id", owner_id) \
            .execute()

        if not res.data:
            return f"Error: You do not currently own a position in {ticker}."

        pos_data = res.data[0]
        total_shares = int(pos_data['quantity'])
        price = float(pos_data['current_price'])

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
        messages = PromptFactory.build_ticker_suggestion_messages(
            provider="gemini",
            event_summary=theme
        )

        resp = client.chat.completions.create(
            model=GEMINI_MODEL,
            response_model=TickerSuggestion,
            messages=messages
        )
        import asyncio
        if asyncio.iscoroutine(resp):
            resp = await resp

        return (
            f"Suggested Tickers for '{theme}': {', '.join(resp.tickers)}\n"
            f"Reasoning: {resp.reasoning}"
        )
    except Exception as e:
        return f"Error suggesting tickers for '{theme}': {str(e)}"


async def execute_find_uncorrelated_assets_tool(
    max_correlation: float = 0.3,
    min_return: float = 0.0,
    method: str = "pearson"
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
            filtered.append({
                **row,
                "abs_corr": abs(corr),
                "avg_return": (ret_a + ret_b) / 2,
            })

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
