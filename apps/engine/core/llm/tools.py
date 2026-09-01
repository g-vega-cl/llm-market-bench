"""Tool definitions and execution logic for LLMs.

Tool definitions are stored in a single canonical format (OpenAI Chat Completions
function-tool schema). Handlers translate to provider-specific formats via
``to_anthropic`` / ``to_gemini`` at the boundary.
"""

import contextlib
import contextvars

from core.config import logger
from core.db import get_async_supabase_client, get_supabase_client
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

AUDIT_FINANCIAL_VALUATION_TOOL = {
    "type": "function",
    "function": {
        "name": "audit_financial_valuation",
        "description": (
            "Perform an institutional-grade DCF (Discounted Cash Flow) and comparable company valuation "
            "audit for a stock ticker. The tool retrieves historical growth rates, forward analyst estimates, "
            "WACC inputs, and peer ratios from FMP dynamically, executes perpetuity value bridges, "
            "and returns a formatted report with implied intrinsic value vs current price."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., AAPL, NVDA, TSLA)",
                },
                "growth_rate": {
                    "type": "number",
                    "description": "Optional forecast growth rate (e.g., 0.12 for 12%). If omitted, defaults to analyst consensus forward estimates.",
                },
                "discount_rate": {
                    "type": "number",
                    "description": "Optional discount rate/WACC (e.g., 0.085 for 8.5%). If omitted, calculates dynamically using CAPM.",
                },
                "terminal_growth": {
                    "type": "number",
                    "description": "Optional perpetuity growth rate (e.g., 0.025 for 2.5%). Default: 0.025.",
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


FETCH_DAILY_NEWSLETTER_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_daily_newsletter",
        "description": "Fetch the AI Wall Street synthesized daily market newsletter briefing (market open or close) containing executive summary, bullet points, macro narrative, and trade scenarios.",
        "parameters": {
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "enum": ["open", "close", "latest"],
                    "description": "Newsletter session window ('open' for morning briefing, 'close' for market wrap, or 'latest'). Default 'latest'.",
                },
                "target_date": {
                    "type": "string",
                    "description": "Optional ISO date (YYYY-MM-DD) to fetch the newsletter for. If omitted, returns the most recent newsletter.",
                },
                "include_full_content": {
                    "type": "boolean",
                    "description": "Whether to include the full ~1,500-word Markdown article content or just the executive summary and bullet points (default true).",
                },
            },
        },
    },
}

FETCH_NEWSLETTER_CONTENT_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_newsletter_content",
        "description": "Fetch the full text content of one or more newsletter articles using their source IDs from today's menu.",
        "parameters": {
            "type": "object",
            "properties": {
                "source_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of source IDs (e.g. ['news_goldmansachs_8b21c43f']) to fetch.",
                }
            },
            "required": ["source_ids"],
        },
    },
}

SEARCH_PAST_MEMORIES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_past_memories",
        "description": "Perform a semantic vector search (RAG) against past market events, government incentives, lessons learned, and historical trade reasoning.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Semantic query describing the topic, ticker, or historical pattern to search for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of historical snippets to return (default 5).",
                },
            },
            "required": ["query"],
        },
    },
}

GET_THEMATIC_FLOWS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_thematic_flows",
        "description": "Fetch active macro thematic capital flows and sector rotation theses (e.g. AI Winners -> Power/Cooling, Crypto Miners -> AI Datacenters).",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of thematic flows to return (default 5).",
                },
            },
            "required": [],
        },
    },
}

ADD_THEMATIC_FLOW_TOOL = {
    "type": "function",
    "function": {
        "name": "add_thematic_flow",
        "description": "Register a new macro capital flow or thematic rotation thesis into long-term memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Detailed description of the macro rotation thesis or capital flow pattern.",
                },
                "importance_score": {
                    "type": "integer",
                    "description": "Importance rating from 1 to 10 (default 8).",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category tag (e.g. AI_CAPEX_ROTATION, MACRO_REGIME).",
                },
            },
            "required": ["content"],
        },
    },
}


active_news_summaries = contextvars.ContextVar("active_news_summaries", default=None)
active_news_chunks = contextvars.ContextVar("active_news_chunks", default=None)


WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Perform a general web search to find breaking news, stock prices, or market reports.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web.",
                }
            },
            "required": ["query"],
        },
    },
}


GET_PORTFOLIO_LEDGER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_portfolio_ledger",
        "description": "Retrieve the current portfolio cash, total equity, buying power (SMA), and details of all stock holdings including their average cost basis and current market value.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_TODAYS_NEWS_MENU_TOOL = {
    "type": "function",
    "function": {
        "name": "get_todays_news_menu",
        "description": "Retrieve a list of concise summaries and subjects of today's newsletters (the headline menu).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_MARKET_FEELING_TOOL = {
    "type": "function",
    "function": {
        "name": "get_market_feeling",
        "description": "Retrieve the latest generated market sentiment label, confidence score, emoji, and qualitative feeling details from other LLM models.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_GLOBAL_MACRO_CONTEXT_TOOL = {
    "type": "function",
    "function": {
        "name": "get_global_macro_context",
        "description": "Fetch a broad, clean snapshot of the global macroeconomic environment including equity indices, commodity prices, crypto, interest rate/bond yield proxies (IEF/TLT), and volatility ETF proxies (VIXY) with daily % changes and volatility regime classifications.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_VOLATILITY_INDEX_DETAILS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_volatility_index_details",
        "description": "Fetch high-fidelity historical stats, percentiles, trends, and curve structure (contango/backwardation proxy) for the VIX short-term (VIXY) and mid-term (VIXM) index ETFs to detect volatility expansion/contraction regimes.",
        "parameters": {
            "type": "object",
            "properties": {
                "lookback_days": {
                    "type": "integer",
                    "description": "Number of history days to use for calculating percentile ranks and moving averages (default: 90).",
                }
            },
            "required": [],
        },
    },
}

GET_VERIFIER_REJECTIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_verifier_rejections",
        "description": "Retrieve recent trade rejection logs and verifier feedback reasons for past decisions to understand why proposed trades failed verification or compliance checks.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional ticker symbol to filter rejections by (e.g. 'AAPL').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent rejection records to retrieve (default: 5).",
                },
            },
            "required": [],
        },
    },
}


GET_MACRO_ECONOMIC_SERIES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_macro_economic_series",
        "description": (
            "Fetch official macroeconomic time series data from Federal Reserve Economic Data (FRED) "
            "with historical observations, trends, and change metrics. Supports high-level aliases "
            "(e.g. 'fed_funds', 'yield_curve_10y2y', 'treasury_10y', 'treasury_2y', 'cpi', 'core_cpi', "
            "'unemployment', 'high_yield_spread', 'm2', 'fed_balance_sheet', 'reverse_repo', "
            "'nonfarm_payrolls', 'initial_claims', 'real_gdp', 'retail_sales', 'pce', 'consumer_sentiment', "
            "'breakeven_5y', 'breakeven_10y') as well as any raw FRED series ID (e.g. 'WALCL', 'PCEPI')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "series_id_or_alias": {
                    "type": "string",
                    "description": "Macro indicator alias (e.g. 'fed_funds', 'yield_curve_10y2y', 'cpi', 'unemployment', 'high_yield_spread') or raw FRED series ID (e.g. 'FEDFUNDS', 'T10Y2Y', 'WALCL').",
                },
                "lookback_periods": {
                    "type": "integer",
                    "description": "Number of recent historical observation periods to retrieve (default: 12).",
                },
                "units": {
                    "type": "string",
                    "description": "Data transformation unit: 'lin' (Levels/default), 'chg' (Change), 'ch1' (Change from 1 year ago), 'pch' (% Change), 'pc1' (% Change from 1 year ago).",
                },
                "frequency": {
                    "type": "string",
                    "description": "Optional frequency aggregation: 'd' (Daily), 'w' (Weekly), 'm' (Monthly), 'q' (Quarterly), 'a' (Annual).",
                },
            },
            "required": ["series_id_or_alias"],
        },
    },
}


GET_OPTIONS_SENTIMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "get_options_sentiment",
        "description": (
            "Fetch options market sentiment, Put/Call ratios (by volume and open interest), "
            "ATM implied volatility, 25-delta volatility skew, Max Pain strike price, and unusual options activity alerts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., AAPL, NVDA, TSLA, SPY).",
                },
                "expiration_date": {
                    "type": "string",
                    "description": "Optional specific expiration date (YYYY-MM-DD). If omitted, aggregates across active cycles.",
                },
            },
            "required": ["ticker"],
        },
    },
}

GET_OPTION_CHAIN_TOOL = {
    "type": "function",
    "function": {
        "name": "get_option_chain",
        "description": (
            "Fetch a compact near-the-money options chain table with bid, ask, last price, volume, "
            "open interest, implied volatility, and option Greeks (Delta, Gamma, Theta, Vega)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., AAPL, NVDA, TSLA).",
                },
                "expiration_date": {
                    "type": "string",
                    "description": "Optional specific expiration date (YYYY-MM-DD).",
                },
                "contract_type": {
                    "type": "string",
                    "enum": ["all", "call", "put"],
                    "description": "Filter by contract type ('all', 'call', 'put'). Default 'all'.",
                },
                "strike_range_pct": {
                    "type": "number",
                    "description": "Strike range percentage around current price (default 10.0 for +/- 10%).",
                },
                "min_dte": {
                    "type": "integer",
                    "description": "Minimum days to expiration.",
                },
                "max_dte": {
                    "type": "integer",
                    "description": "Maximum days to expiration.",
                },
            },
            "required": ["ticker"],
        },
    },
}


CANONICAL_TOOLS_REGISTRY = {
    "get_stock_quote": STOCK_TOOL,
    "get_price_history": PRICE_HISTORY_TOOL,
    "get_position_pnl": POSITION_PNL_TOOL,
    "get_volatility_metrics": VOLATILITY_METRICS_TOOL,
    "get_sector_alternatives": SECTOR_ALTERNATIVES_TOOL,
    "calculate_buy_quantity": CALCULATE_BUY_QUANTITY_TOOL,
    "calculate_sell_quantity": CALCULATE_SELL_QUANTITY_TOOL,
    "run_stock_screener": RUN_STOCK_SCREENER_TOOL,
    "search_related_tickers": SEARCH_RELATED_TICKERS_TOOL,
    "find_uncorrelated_assets": FIND_UNCORRELATED_ASSETS_TOOL,
    "get_key_metrics": GET_KEY_METRICS_TOOL,
    "audit_financial_valuation": AUDIT_FINANCIAL_VALUATION_TOOL,
    "get_market_health_barometer": GET_MARKET_HEALTH_BAROMETER_TOOL,
    "get_earnings_history": GET_EARNINGS_HISTORY_TOOL,
    "search_prediction_markets": SEARCH_PREDICTION_MARKETS_TOOL,
    "get_prediction_market_odds": GET_PREDICTION_MARKET_ODDS_TOOL,
    "fetch_daily_newsletter": FETCH_DAILY_NEWSLETTER_TOOL,
    "fetch_newsletter_content": FETCH_NEWSLETTER_CONTENT_TOOL,
    "search_past_memories": SEARCH_PAST_MEMORIES_TOOL,
    "get_thematic_flows": GET_THEMATIC_FLOWS_TOOL,
    "add_thematic_flow": ADD_THEMATIC_FLOW_TOOL,
    "get_portfolio_ledger": GET_PORTFOLIO_LEDGER_TOOL,
    "get_todays_news_menu": GET_TODAYS_NEWS_MENU_TOOL,
    "get_market_feeling": GET_MARKET_FEELING_TOOL,
    "get_global_macro_context": GET_GLOBAL_MACRO_CONTEXT_TOOL,
    "get_volatility_index_details": GET_VOLATILITY_INDEX_DETAILS_TOOL,
    "get_verifier_rejections": GET_VERIFIER_REJECTIONS_TOOL,
    "get_macro_economic_series": GET_MACRO_ECONOMIC_SERIES_TOOL,
    "get_options_sentiment": GET_OPTIONS_SENTIMENT_TOOL,
    "get_option_chain": GET_OPTION_CHAIN_TOOL,
    "web_search": WEB_SEARCH_TOOL,
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

        import asyncio

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


async def execute_sector_alternatives_tool(ticker: str) -> str:
    """Identifies sector alternatives for a ticker using FMP industry screener, correlation matrix, and decision history."""
    client = get_supabase_client()
    ticker = ticker.upper()

    industry_competitors = []
    correlated_plays = []
    historical_plays = []

    # 1. Fetch Company Profile & Screen Stocks from FMP
    manager = MarketDataManager()
    sector = None
    industry = None
    try:
        profiles = await manager.get_company_profile(ticker)
        if profiles and isinstance(profiles, list):
            profile = profiles[0]
            sector = profile.get("sector")
            industry = profile.get("industry")

        if sector or industry:
            screen_results = await manager.screen_stocks(sector=sector, industry=industry, limit=5)
            if screen_results:
                for item in screen_results:
                    sym = item.get("symbol")
                    if sym and sym != ticker:
                        name = item.get("companyName", "")
                        price = item.get("price", 0.0)
                        mcap = item.get("marketCap", 0.0)
                        mcap_str = f"${mcap / 1e9:.2f}B" if mcap else "unknown"
                        industry_competitors.append(f"{sym} ({name}) - Price: ${price:.2f}, Market Cap: {mcap_str}")
    except Exception as e:
        logger.warning(f"Error fetching company profile/screening for sector alternatives: {e}")

    # 2. Fetch Statistical Correlations from Database
    try:
        runs = client.table("correlation_runs").select("id").order("run_date", desc=True).limit(1).execute()
        if runs.data:
            run_id = runs.data[0]["id"]
            res_a = client.table("correlation_data").select("*").eq("run_id", run_id).eq("ticker_a", ticker).execute()
            res_b = client.table("correlation_data").select("*").eq("run_id", run_id).eq("ticker_b", ticker).execute()

            corr_rows = (res_a.data or []) + (res_b.data or [])

            filtered_corrs = []
            for row in corr_rows:
                corr = row.get("pearson_corr")
                if corr is not None and corr >= 0.40:
                    other_ticker = row.get("ticker_b") if row.get("ticker_a") == ticker else row.get("ticker_a")
                    ret_other = row.get("returns_b_90d") if row.get("ticker_a") == ticker else row.get("returns_a_90d")
                    ret_other_val = f"{ret_other:.2f}%" if ret_other is not None else "N/A"
                    filtered_corrs.append({"ticker": other_ticker, "corr": corr, "ret": ret_other_val})

            filtered_corrs.sort(key=lambda x: x["corr"], reverse=True)
            for c in filtered_corrs[:5]:
                correlated_plays.append(f"{c['ticker']} (Correlation: {c['corr']:.4f} | 90d Return: {c['ret']})")
    except Exception as e:
        logger.warning(f"Error fetching correlation data for sector alternatives: {e}")

    # 3. Vector Search on Past Decisions
    try:
        query_text = f"Market analysis and trading decision for {ticker} stock in this sector"
        embedding = get_embedding(query_text)
        if embedding:
            res = client.rpc(
                "match_decisions",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": 10,
                },
            ).execute()
            if res.data:
                related_tickers_set = set()
                for item in res.data:
                    t = item.get("ticker")
                    if t and t != ticker:
                        related_tickers_set.add(t)
                historical_plays = list(related_tickers_set)[:5]
    except Exception as e:
        logger.warning(f"Error fetching decision history vector search: {e}")

    # Aggregating results
    output = f"Sector Alternatives & Related Plays for {ticker}:\n\n"
    has_results = False

    if sector or industry:
        output += f"1. Industry Competitors (Sector: {sector or 'Unknown'}, Industry: {industry or 'Unknown'}):\n"
        if industry_competitors:
            for item in industry_competitors:
                output += f"   - {item}\n"
            has_results = True
        else:
            output += "   - No other liquid stocks found in this industry.\n"
        output += "\n"

    if correlated_plays:
        output += "2. Highly Correlated Assets (90d Pearson Correlation >= 0.40):\n"
        for item in correlated_plays:
            output += f"   - {item}\n"
        output += "\n"
        has_results = True

    if historical_plays:
        output += "3. Historical Related Plays (From past agent decisions):\n"
        output += f"   - {', '.join(historical_plays)}\n"
        output += "\n"
        has_results = True

    if not has_results:
        try:
            mem_res = client.table("memories").select("content").ilike("content", f"%{ticker}%").limit(5).execute()
            if mem_res.data:
                return (
                    f"No direct competitors or correlated assets found for {ticker}, but "
                    f"the ticker appears in recent market events. Consider searching for standard competitors manually."
                )
        except Exception:
            pass
        return f"No alternative plays or correlated assets found for {ticker}."

    return output.strip()


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


async def execute_key_metrics_tool(ticker: str, period: str = "annual", limit: int = 2) -> str:
    """Fetches fundamental financial key metrics for a ticker to help analyze valuation/health."""
    manager = MarketDataManager()
    try:
        data = await manager.get_key_metrics(ticker, period, limit)

        if not data:
            return f"No fundamental key metrics found for {ticker}."

        # Fetch quote, estimates, and annual history to calculate Forward P/E and CAPE
        price = None
        forward_pe = None
        cape_val = None
        avg_eps = None
        eps_count = 0
        next_eps_est = None

        try:
            quote = await manager.get_quote(ticker)
            if quote and quote.exists:
                price = quote.price
        except Exception as e:
            logger.warning(f"Failed to fetch quote for new metrics calculation for {ticker}: {e}")

        # Helper to safely format decimal/float metrics
        def fmt(val, percentage=False):
            if val is None:
                return "N/A"
            if percentage:
                return f"{val * 100:.2f}%"
            return f"{val:.2f}"

        if price and price > 0:
            # Calculate Forward P/E
            try:
                estimates = await manager.get_analyst_estimates(ticker, period="annual", limit=5)
                if estimates and isinstance(estimates, list):
                    from datetime import datetime

                    now_year = datetime.now().year
                    for est in estimates:
                        est_date = est.get("date")
                        if est_date:
                            try:
                                est_year = int(est_date.split("-")[0])
                                if est_year >= now_year:
                                    next_eps_est = est.get("epsAvg")
                                    break
                            except ValueError:
                                pass
                    if next_eps_est is None and estimates:
                        next_eps_est = estimates[0].get("epsAvg")
                    if next_eps_est is not None:
                        try:
                            next_eps_est_val = float(next_eps_est)
                            if next_eps_est_val > 0:
                                forward_pe = price / next_eps_est_val
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                logger.warning(f"Failed to calculate Forward P/E for {ticker}: {e}")

            # Calculate CAPE (10-Yr Avg EPS)
            try:
                # Fetch up to 10 annual records
                annual_metrics = await manager.get_key_metrics(ticker, period="annual", limit=10)
                if annual_metrics:
                    eps_values = []
                    for yr_entry in annual_metrics:
                        val = yr_entry.get("netIncomePerShare")
                        if val is not None:
                            with contextlib.suppress(ValueError, TypeError):
                                eps_values.append(float(val))
                    if len(eps_values) >= 3:
                        avg_eps = sum(eps_values) / len(eps_values)
                        eps_count = len(eps_values)
                        if avg_eps > 0:
                            cape_val = price / avg_eps
            except Exception as e:
                logger.warning(f"Failed to calculate CAPE for {ticker}: {e}")

        output = f"Fundamental Key Metrics for {ticker} ({period.capitalize()} periods, recent first):\n"
        for i, entry in enumerate(data, 1):
            date_str = entry.get("date") or "N/A"
            period_str = entry.get("period") or "N/A"
            year_str = entry.get("calendarYear") or "N/A"

            output += f"\n--- Period {i}: {period_str} {year_str} (Date: {date_str}) ---\n"

            output += f"- P/E Ratio: {fmt(entry.get('peRatio'))}\n"
            output += f"- Price/Sales Ratio: {fmt(entry.get('priceToSalesRatio'))}\n"

            pb = entry.get("pbRatio")
            book_to_market = (1.0 / pb) if (pb is not None and pb != 0) else None
            output += f"- Price/Book Ratio: {fmt(pb)}\n"
            output += f"- Book-to-Market Ratio: {fmt(book_to_market)}\n"

            output += f"- EV/EBITDA: {fmt(entry.get('enterpriseValueOverEBITDA'))}\n"
            output += f"- Debt/Equity: {fmt(entry.get('debtToEquity'))}\n"
            output += f"- Current Ratio: {fmt(entry.get('currentRatio'))}\n"
            output += f"- ROE: {fmt(entry.get('roe'), percentage=True)}\n"
            output += f"- Dividend Yield: {fmt(entry.get('dividendYield'), percentage=True)}\n"
            output += f"- Free Cash Flow Yield: {fmt(entry.get('freeCashFlowYield'), percentage=True)}\n"
            if "priceToFreeCashFlowsRatio" in entry:
                output += f"- Price/Free Cash Flow Ratio: {fmt(entry.get('priceToFreeCashFlowsRatio'))}\n"
            output += f"- Book Value Per Share: ${fmt(entry.get('bookValuePerShare'))}\n"
            output += f"- Revenue Per Share: ${fmt(entry.get('revenuePerShare'))}\n"
            if "netIncomePerShare" in entry:
                output += f"- Net Income Per Share: ${fmt(entry.get('netIncomePerShare'))}\n"
            if "freeCashFlowPerShare" in entry:
                output += f"- Free Cash Flow Per Share: ${fmt(entry.get('freeCashFlowPerShare'))}\n"

        output += "\n--- Current Valuation Metrics (Derived) ---\n"
        if price and price > 0:
            output += f"- Current Stock Price: ${price:.2f}\n"
            if forward_pe is not None:
                output += f"- Forward P/E: {fmt(forward_pe)} (based on Next FY EPS Est. of ${fmt(next_eps_est)})\n"
            else:
                output += "- Forward P/E: N/A\n"
            if cape_val is not None:
                output += f"- CAPE ({eps_count}-Yr Avg EPS): {fmt(cape_val)} (Average EPS: ${fmt(avg_eps)})\n"
            else:
                output += "- CAPE (10-Yr Avg EPS): N/A\n"
        else:
            output += "- Current Stock Price: N/A\n"
            output += "- Forward P/E: N/A\n"
            output += "- CAPE (10-Yr Avg EPS): N/A\n"

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
            pfcf = entry.get("pfcf_ratio")
            surprise = entry.get("earnings_surprise_momentum")

            pe_val = f"{float(pe):.2f}" if pe is not None else "N/A"
            fwd_pe_val = f"{float(fwd_pe):.2f}" if fwd_pe is not None else "N/A"
            pb_val = f"{float(pb):.2f}" if pb is not None else "N/A"
            ps_val = f"{float(ps):.2f}" if ps is not None else "N/A"
            pfcf_val = f"{float(pfcf):.2f}" if pfcf is not None else "N/A"
            surprise_val = f"{float(surprise):.1f}%" if surprise is not None else "N/A"

            output += f"\n- Date: {date_str}\n"
            output += f"  * Aggregate Trailing P/E: {pe_val}\n"
            output += f"  * Aggregate Forward P/E:  {fwd_pe_val}\n"
            output += f"  * Aggregate P/S Ratio:   {ps_val}\n"
            output += f"  * Aggregate P/B Ratio:   {pb_val}\n"
            output += f"  * Aggregate Price/FCF:    {pfcf_val}\n"
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
                est_eps = f"${entry['epsEstimated']:.2f}" if entry.get("epsEstimated") is not None else "N/A"
                est_rev = (
                    f"${entry['revenueEstimated'] / 1e9:.2f}B" if entry.get("revenueEstimated") is not None else "N/A"
                )
                output += f"- Date: {entry['date']} | Estimated EPS: {est_eps} | Estimated Revenue: {est_rev}\n"

        if past:
            output += "\n--- Historical Earnings Reports (Recent first) ---\n"
            for entry in past:
                act_eps = f"${entry['epsActual']:.2f}" if entry.get("epsActual") is not None else "N/A"
                est_eps = f"${entry['epsEstimated']:.2f}" if entry.get("epsEstimated") is not None else "N/A"
                act_rev = f"${entry['revenueActual'] / 1e9:.2f}B" if entry.get("revenueActual") is not None else "N/A"
                est_rev = (
                    f"${entry['revenueEstimated'] / 1e9:.2f}B" if entry.get("revenueEstimated") is not None else "N/A"
                )

                surprise = entry.get("surprisePct")
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


async def execute_financial_valuation_tool(
    ticker: str,
    growth_rate: float | None = None,
    discount_rate: float | None = None,
    terminal_growth: float = 0.025,
) -> str:
    """Executes the financial valuation audit tool and returns a markdown-formatted report."""
    ticker = ticker.upper()
    manager = MarketDataManager()

    try:
        # 1. Fetch market quote data (price, market cap)
        quote = await manager.get_quote(ticker)
        if not quote or not quote.exists:
            return f"Error: Ticker '{ticker}' not found or could not fetch price data."

        price = quote.price
        market_cap = quote.market_cap
        if price <= 0 or market_cap <= 0:
            return f"Error: Invalid pricing or market cap retrieved for {ticker} (Price: {price}, Market Cap: {market_cap})."

        # Calculate initial shares outstanding estimate
        shares_outstanding = market_cap / price

        # 2. Fetch key metrics history — try quarterly first for earnings-week relevance,
        # fall back to annual via the FMP provider's 402→annual fallback handler.
        key_metrics = await manager.get_key_metrics(ticker, period="quarter", limit=2)
        if not key_metrics:
            return f"Error: No key metrics data found for {ticker}."

        latest_metric = key_metrics[0]

        # Detect if we got annual fallback (FMP plan tier limits) so the report
        # can flag the degradation for the LLM.
        actual_period = str(latest_metric.get("period") or "")
        metrics_degradation_note = ""
        if "Q" not in actual_period.upper():
            metrics_degradation_note = (
                "\n> ⚠️ NOTE: FMP quarterly metrics unavailable on current plan "
                "(402 Payment Required). DCF using annual fallback metrics; "
                "earnings-week signals should be discounted accordingly.\n"
            )

        # 3. Fetch profile (for Beta)
        profile = await manager.get_company_profile(ticker)
        beta = 1.0
        company_name = ticker
        if profile and isinstance(profile, list) and len(profile) > 0:
            p = profile[0]
            company_name = p.get("companyName") or ticker
            try:
                beta = float(p.get("beta") or 1.0)
            except (ValueError, TypeError):
                beta = 1.0

        # 4. Fetch analyst consensus estimates
        estimates = await manager.get_analyst_estimates(ticker, period="annual", limit=5)

        # 5. Fetch financial growth history
        growth_history = await manager.get_financial_growth(ticker, period="annual", limit=5)

        # --- Calculate Forecast Growth Rate ---
        forecast_growth = None
        if estimates and len(estimates) >= 2:
            with contextlib.suppress(Exception):
                # Estimate growth YoY from estimates
                rev_y1 = float(estimates[0].get("estimatedRevenueAvg") or 0)
                rev_y2 = float(estimates[1].get("estimatedRevenueAvg") or 0)
                if rev_y1 > 0 and rev_y2 > 0:
                    forecast_growth = (rev_y2 / rev_y1) - 1.0

        if forecast_growth is None and growth_history and len(growth_history) >= 1:
            with contextlib.suppress(Exception):
                # Fallback to historical growth YoY
                forecast_growth = float(growth_history[0].get("revenueGrowth") or 0.08)

        if forecast_growth is None:
            forecast_growth = 0.08  # Default baseline 8%

        growth_rate_used = growth_rate if growth_rate is not None else forecast_growth
        growth_rate_used = max(-0.25, min(0.40, growth_rate_used))  # Clamp to safe boundaries

        # --- Calculate WACC (Discount Rate) ---
        rf = 0.042  # 10-Yr US Treasury yield baseline (4.2%)
        erp = 0.055  # Equity Risk Premium baseline (5.5%)
        cost_of_equity = rf + beta * erp

        # Capital Structure / Net Debt
        net_debt = 0.0
        with contextlib.suppress(ValueError, TypeError):
            val = latest_metric.get("netDebt")
            if val is not None:
                net_debt = float(val)

        # Calculate WACC weights
        total_value = market_cap + max(0.0, net_debt)
        if total_value > 0 and net_debt > 0:
            weight_equity = market_cap / total_value
            weight_debt = net_debt / total_value
            cost_of_debt = 0.05  # Pre-tax debt rate default (5%)
            tax_rate = 0.21  # Standard US corporate tax (21%)
            after_tax_debt = cost_of_debt * (1 - tax_rate)
            calculated_wacc = (cost_of_equity * weight_equity) + (after_tax_debt * weight_debt)
        else:
            # Net Cash firm or no debt: WACC equals Cost of Equity
            calculated_wacc = cost_of_equity

        wacc_used = discount_rate if discount_rate is not None else calculated_wacc
        wacc_used = max(0.05, min(0.18, wacc_used))  # Clamp WACC to safe range (5% - 18%)

        # --- Cash Flow Discounting ---
        # Estimate recent Free Cash Flow
        fcf_yield = latest_metric.get("freeCashFlowYield")
        fcf_per_share = latest_metric.get("freeCashFlowPerShare")
        if fcf_yield is not None:
            base_fcf = float(fcf_yield) * market_cap
        elif fcf_per_share is not None:
            base_fcf = float(fcf_per_share) * shares_outstanding
        else:
            net_income_ps = latest_metric.get("netIncomePerShare")
            if net_income_ps is not None:
                base_fcf = float(net_income_ps) * shares_outstanding * 0.8
            else:
                base_fcf = market_cap * 0.05  # Default to 5% FCF Yield

        # Safely clamp terminal growth below WACC
        tg_used = terminal_growth
        if tg_used >= wacc_used:
            tg_used = wacc_used - 0.02

        # 5-Year forecast schedule
        projected_fcfs = []
        discount_factors = []
        pv_fcfs = []

        current_fcf = base_fcf
        for yr in range(1, 6):
            current_fcf = current_fcf * (1 + growth_rate_used)
            projected_fcfs.append(current_fcf)

            # Mid-year convention discounting: (yr - 0.5)
            df = 1.0 / ((1 + wacc_used) ** (yr - 0.5))
            discount_factors.append(df)
            pv_fcfs.append(current_fcf * df)

        sum_pv_fcfs = sum(pv_fcfs)

        # Terminal Value calculation
        terminal_fcf = projected_fcfs[-1] * (1 + tg_used)
        terminal_value = terminal_fcf / (wacc_used - tg_used)
        # Discount terminal value at year 5
        pv_terminal_value = terminal_value / ((1 + wacc_used) ** 5.0)

        # Valuation bridge
        implied_ev = sum_pv_fcfs + pv_terminal_value
        implied_equity_val = implied_ev - net_debt
        implied_price = implied_equity_val / shares_outstanding
        implied_upside = (implied_price / price - 1.0) * 100

        # --- Comparable Peer Comps Analysis ---
        # Fetch S&P 500 barometer aggregates (PE: ~22.5, Forward PE: ~18.5, P/FCF: ~20.0)
        # We fetch the latest health barometer from DB if available, otherwise fallback to defaults
        barometer_pe = 22.5
        barometer_pfcf = 20.0
        try:
            from core.db import get_supabase_client

            client_db = get_supabase_client()
            res = (
                client_db.table("market_barometer_history")
                .select("pe_ratio, pfcf_ratio")
                .order("date", desc=True)
                .limit(1)
                .execute()
            )
            if res.data:
                barometer_pe = float(res.data[0].get("pe_ratio") or 22.5)
                barometer_pfcf = float(res.data[0].get("pfcf_ratio") or 20.0)
        except Exception as e:
            # Don't silently swallow — log so future schema drift surfaces.
            logger.warning(f"market_barometer_history query failed (using defaults 22.5/20.0): {e}")

        pe_ratio = latest_metric.get("peRatio")
        pfcf_ratio = latest_metric.get("priceToFreeCashFlowsRatio")
        ev_ebitda = latest_metric.get("enterpriseValueOverEBITDA")

        pe_str = f"{pe_ratio:.2f}x" if pe_ratio else "N/A"
        pfcf_str = f"{pfcf_ratio:.2f}x" if pfcf_ratio else "N/A"
        ev_ebitda_str = f"{ev_ebitda:.2f}x" if ev_ebitda else "N/A"

        # Determine valuation status
        status = "FAIR VALUE"
        reasons = []
        if implied_upside > 15.0:
            status = "UNDERVALUED"
            reasons.append("DCF implied price suggests >15% upside")
        elif implied_upside < -10.0:
            status = "OVERVALUED"
            reasons.append("DCF implied price suggests >10% downside")

        if pe_ratio and pe_ratio > barometer_pe * 1.3:
            reasons.append(f"PE multiple ({pe_str}) trades at >30% premium to S&P 500 average ({barometer_pe:.1f}x)")
        elif pe_ratio and pe_ratio < barometer_pe * 0.7:
            reasons.append(f"PE multiple ({pe_str}) trades at >30% discount to S&P 500 average ({barometer_pe:.1f}x)")

        # Create the markdown audit report
        pe_premium = f"{((pe_ratio / barometer_pe - 1) * 100):+.1f}%" if pe_ratio else "N/A"
        pfcf_premium = f"{((pfcf_ratio / barometer_pfcf - 1) * 100):+.1f}%" if pfcf_ratio else "N/A"

        output = (
            f"### 📊 Valuation & Intrinsic Value Audit Report: {ticker} ({company_name})\n\n"
            f"**Valuation Status:** `{status}`\n"
            f"**Current Price:** ${price:.2f} | **Implied Intrinsic Price:** ${implied_price:.2f} ({implied_upside:+.1f}% upside/downside)\n"
            f"{metrics_degradation_note}\n"
            f"#### 1. DCF Model Assumptions & Inputs\n"
            f"- **Forecast Growth Rate:** {growth_rate_used * 100:.1f}% (Base: {'analyst estimates' if forecast_growth == estimates else 'historical growth'})\n"
            f"- **Discount Rate (WACC):** {wacc_used * 100:.1f}% (CAPM Beta: {beta:.2f}, Cost of Equity: {cost_of_equity * 100:.1f}%)\n"
            f"- **Terminal perpetuity Growth (g):** {tg_used * 100:.1f}%\n"
            f"- **Diluted Shares Outstanding:** {shares_outstanding:.1f}M\n"
            f"- **Net Debt (Debt - Cash):** ${net_debt / 1e6:.1f}M\n\n"
            f"#### 2. Discounted Cash Flow (DCF) Bridge\n"
            f"| Metric | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Terminal Value |\n"
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            f"| **FCF ($M)** | ${projected_fcfs[0] / 1e6:.1f} | ${projected_fcfs[1] / 1e6:.1f} | ${projected_fcfs[2] / 1e6:.1f} | ${projected_fcfs[3] / 1e6:.1f} | ${projected_fcfs[4] / 1e6:.1f} | ${terminal_value / 1e6:.1f} |\n"
            f"| **Discount Factor** | {discount_factors[0]:.4f} | {discount_factors[1]:.4f} | {discount_factors[2]:.4f} | {discount_factors[3]:.4f} | {discount_factors[4]:.4f} | {1.0 / ((1 + wacc_used) ** 5.0):.4f} |\n"
            f"| **PV ($M)** | ${pv_fcfs[0] / 1e6:.1f} | ${pv_fcfs[1] / 1e6:.1f} | ${pv_fcfs[2] / 1e6:.1f} | ${pv_fcfs[3] / 1e6:.1f} | ${pv_fcfs[4] / 1e6:.1f} | ${pv_terminal_value / 1e6:.1f} |\n\n"
            f"- **Sum of PV of Explicit Cash Flows:** ${sum_pv_fcfs / 1e6:.1f}M\n"
            f"- **PV of perpetuity Terminal Value:** ${pv_terminal_value / 1e6:.1f}M\n"
            f"- **Implied Enterprise Value (EV):** ${implied_ev / 1e6:.1f}M\n"
            f"- **Implied Equity Value (EV - Net Debt):** ${implied_equity_val / 1e6:.1f}M\n\n"
            f"#### 3. Comparable Multiple Analysis\n"
            f"| Valuation Multiple | Ticker Value | S&P 500 Average | Premium / Discount |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"| **P/E Ratio** | {pe_str} | {barometer_pe:.1f}x | {pe_premium} |\n"
            f"| **Price / FCF** | {pfcf_str} | {barometer_pfcf:.1f}x | {pfcf_premium} |\n"
            f"| **EV / EBITDA** | {ev_ebitda_str} | N/A | N/A |\n\n"
        )
        if reasons:
            output += "#### 4. Audit Observations & Key Concerns\n"
            for r in reasons:
                output += f"- {r}\n"

        return output.strip()

    except Exception as e:
        logger.exception(f"Error executing valuation audit for {ticker}: {str(e)}")
        return f"Error executing valuation audit for {ticker}: {str(e)}"


async def execute_fetch_daily_newsletter_tool(
    session: str = "latest",
    target_date: str | None = None,
    include_full_content: bool = True,
) -> str:
    """Retrieves the synthesized daily market newsletter from `generated_newsletters`.

    Args:
        session: 'open', 'close', or 'latest'.
        target_date: Optional YYYY-MM-DD string.
        include_full_content: Whether to include the full markdown content.

    Returns:
        Formatted string containing newsletter title, summary, bullets, and content.
    """
    try:
        client = get_supabase_client()
        query = client.table("generated_newsletters").select("*")
        if session in ("open", "close"):
            query = query.eq("session", session)
        if target_date:
            query = query.gte("created_at", f"{target_date}T00:00:00").lte("created_at", f"{target_date}T23:59:59")

        query = query.order("created_at", desc=True).limit(1)
        response = query.execute()

        record = None
        if response and hasattr(response, "data") and response.data:
            record = response.data[0]
        elif target_date:
            # Fallback to latest available newsletter if target_date query yielded no results
            fallback_query = client.table("generated_newsletters").select("*")
            if session in ("open", "close"):
                fallback_query = fallback_query.eq("session", session)
            fallback_resp = fallback_query.order("created_at", desc=True).limit(1).execute()
            if fallback_resp and hasattr(fallback_resp, "data") and fallback_resp.data:
                record = fallback_resp.data[0]
                logger.warning(
                    f"No generated newsletter found for target date {target_date}; "
                    f"fell back to latest available ({record.get('created_at')})"
                )

        if not record:
            return (
                f"No generated daily newsletters found in database "
                f"(session: {session}, target_date: {target_date or 'latest'})."
            )

        title = record.get("title", "Daily Newsletter Briefing")
        summary = record.get("summary", "")
        bullet_points = record.get("bullet_points") or []
        bullets_text = "\n".join([f"- {bp}" for bp in bullet_points])
        formatted_time = record.get("formatted_time", "")
        sess = record.get("session", session)
        created_at = str(record.get("created_at", ""))

        lines = [
            "=== AI WALL STREET SYNTHESIZED DAILY NEWSLETTER ===",
            f"Title: {title}",
            f"Session: {sess.upper()} ({formatted_time}) | Published: {created_at}",
            f"Executive Summary: {summary}",
        ]
        if bullets_text:
            lines.append(f"Key Takeaways:\n{bullets_text}")

        if include_full_content:
            content = record.get("content", "")
            if content:
                lines.append(f"\nFull Briefing Content:\n{content}")

        lines.append("==================================================")
        return "\n".join(lines)

    except Exception as e:
        logger.exception(f"Error executing fetch_daily_newsletter tool: {e}")
        return f"Error fetching daily newsletter: {str(e)}"


async def execute_fetch_newsletter_content_tool(source_ids: list[str]) -> str:
    """Retrieves the full text content of newsletters by their source IDs from the database.

    Args:
        source_ids: A list of source_id strings.

    Returns:
        A formatted string with the full content of requested newsletters.
    """
    if not source_ids:
        return "No source IDs specified."

    try:
        client = get_supabase_client()
        response = (
            client.table("newsletter_snapshots")
            .select("source_id, content, sender, subject, date")
            .in_("source_id", source_ids)
            .execute()
        )

        if not response.data:
            return f"No newsletters found matching IDs: {source_ids}"

        output = []
        for item in response.data:
            output.append(
                f"=========================================\n"
                f"Source ID: {item.get('source_id')}\n"
                f"Sender: {item.get('sender', 'Unknown')}\n"
                f"Subject: {item.get('subject', 'No Subject')}\n"
                f"Date: {item.get('date', 'Unknown')}\n"
                f"-----------------------------------------\n"
                f"{item.get('content', '')}\n"
                f"========================================="
            )

        return "\n\n".join(output)

    except Exception as e:
        logger.exception(f"Error executing fetch_newsletter_content tool: {e}")
        return f"Error fetching newsletter content: {str(e)}"


async def execute_search_past_memories_tool(query: str, limit: int = 5, model_name: str | None = None) -> str:
    """Performs a semantic pgvector search against past memories and model trade decisions.

    Args:
        query: Semantic query text.
        limit: Max context snippets to return.
        model_name: Optional model name to filter trade decisions by.

    Returns:
        Formatted context string of vector search results.
    """
    if not query:
        return "No query specified."

    try:
        from memory.store import retrieve_context

        # retrieve_context runs the embedding call and match_memories/match_decisions RPCs
        context = retrieve_context(query, model_name=model_name or "unknown_agent", limit=limit)
        if not context:
            return f"No relevant past memories or decisions found matching query: '{query}'."

        return context

    except Exception as e:
        logger.exception(f"Error executing search_past_memories tool: {e}")
        return f"Error performing historical RAG search: {str(e)}"


async def execute_get_thematic_flows_tool(limit: int = 5) -> str:
    """Fetch active THEMATIC_FLOW memories for LLM reasoning."""
    try:
        from memory.store import retrieve_thematic_flows

        context = retrieve_thematic_flows(limit=limit)
        if not context:
            return "No active thematic capital flows found."
        return context
    except Exception as e:
        logger.exception(f"Error executing get_thematic_flows tool: {e}")
        return f"Error retrieving thematic flows: {str(e)}"


async def execute_add_thematic_flow_tool(content: str, importance_score: int = 8, category: str | None = None) -> str:
    """Add a new THEMATIC_FLOW memory to Supabase."""
    if not content:
        return "Content cannot be empty."
    try:
        from memory.store import add_memory

        metadata = {"category": category} if category else {}
        memory_id = add_memory(
            content=content,
            memory_type="THEMATIC_FLOW",
            importance_score=importance_score,
            metadata=metadata,
            check_similarity=True,
        )
        if memory_id:
            return f"Successfully added thematic flow memory [ID: {memory_id}]."
        return "Thematic flow memory already exists (deduplicated)."
    except Exception as e:
        logger.exception(f"Error executing add_thematic_flow tool: {e}")
        return f"Error adding thematic flow memory: {str(e)}"


async def execute_get_portfolio_ledger_tool(owner_id: str) -> str:
    """Retrieves current cash, total equity, buying power (SMA), active positions, and recent trade thesis history."""
    try:
        client = get_supabase_client()

        # 1. Fetch general portfolio details
        p_res = client.table("portfolios").select("*").eq("owner_id", owner_id).execute()
        if not p_res.data:
            return f"No portfolio ledger found for owner: {owner_id}"

        p_data = p_res.data[0]
        cash = float(p_data.get("cash_balance", 0.0))
        sma = float(p_data.get("sma", 0.0))
        buying_power = float(p_data.get("buying_power", 0.0))
        total_equity = float(p_data.get("total_equity", 0.0))

        # 2. Fetch positions and PnL
        pos_res = client.table("position_pnl").select("*").eq("owner_id", owner_id).execute()
        positions_str = ""
        if pos_res.data:
            positions_str = "\nStock Holdings:\n"
            for pos in pos_res.data:
                qty = pos.get("quantity", 0)
                if float(qty) <= 0:
                    continue
                ticker = pos["ticker"]
                avg_cost = float(pos.get("average_cost_basis", 0.0))
                curr_price = float(pos.get("current_price", 0.0))
                pnl_usd = float(pos.get("unrealized_pnl_usd", 0.0))
                pnl_pct = float(pos.get("unrealized_pnl_pct", 0.0))
                positions_str += (
                    f"- {ticker}: {qty} shares | Avg Cost: ${avg_cost:.2f} | "
                    f"Current Price: ${curr_price:.2f} | Unrealized PnL: ${pnl_usd:+,.2f} ({pnl_pct:+.2f}%)\n"
                )
        else:
            positions_str = "\nStock Holdings: None (you have no active stock positions)\n"

        # 3. Fetch thesis history / ledger XML (reusing the function we already have)
        from attribution.service import get_active_ledger_xml

        ledger_xml = await get_active_ledger_xml(client, owner_id)
        ledger_str = f"\n{ledger_xml}" if ledger_xml else ""

        return (
            f"=== PORTFOLIO LEDGER ===\n"
            f"Account Owner: {owner_id}\n"
            f"Total Account Equity: ${total_equity:,.2f}\n"
            f"Cash Balance: ${cash:,.2f}\n"
            f"Buying Power (SMA): ${buying_power:,.2f}\n"
            f"SMA High Water Mark: ${sma:,.2f}\n"
            f"{positions_str}"
            f"{ledger_str}"
        )
    except Exception as e:
        logger.exception(f"Error in execute_get_portfolio_ledger_tool: {e}")
        return f"Error retrieving portfolio ledger: {str(e)}"


async def execute_get_todays_news_menu_tool() -> str:
    """Retrieves the pre-filtered summaries and subjects of today's newsletters."""
    try:
        summaries = active_news_summaries.get()
        chunks = active_news_chunks.get()

        if not chunks:
            return "No news chunks available for today."

        news_content_parts = []
        if summaries:
            for chunk in chunks:
                source_id = chunk["source_id"]
                summary_text = summaries.get(source_id, "No summary available.")
                sender = chunk.get("sender", "Unknown")
                subject = chunk.get("subject", "No Subject")
                news_content_parts.append(
                    f"- Source ID: {source_id}\n  Sender: {sender}\n  Subject: {subject}\n  Summary: {summary_text}"
                )
        else:
            for chunk in chunks:
                news_content_parts.append(
                    f"- Source ID: {chunk['source_id']}\n  Sender: {chunk.get('sender', 'Unknown')}\n  Subject: {chunk.get('subject', 'No Subject')}\n  (Full text available via fetch_newsletter_content)"
                )

        return "=== TODAY'S NEWSLETTER MENU ===\n" + "\n".join(news_content_parts)
    except Exception as e:
        logger.exception(f"Error in execute_get_todays_news_menu_tool: {e}")
        return f"Error retrieving newsletter menu: {str(e)}"


async def execute_get_market_feeling_tool() -> str:
    """Retrieves the latest generated market sentiment and feeling."""
    try:
        from analysis.market_feeling import get_latest_market_feeling

        feeling = await get_latest_market_feeling()
        if not feeling:
            return "No market feeling records found."

        return (
            f"=== LATEST MARKET FEELING ===\n"
            f"Sentiment: {feeling.get('sentiment_label')} {feeling.get('sentiment_emoji')}\n"
            f"Confidence: {feeling.get('confidence_score')}%\n"
            f"Feelings: {feeling.get('feeling_text')}\n"
            f"Causal Cues: {feeling.get('causal_cues')}\n"
            f"Timestamp: {feeling.get('created_at')}"
        )
    except Exception as e:
        logger.exception(f"Error in execute_get_market_feeling_tool: {e}")
        return f"Error retrieving market feeling: {str(e)}"


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
    """Retrieves high-fidelity historical stats, percentiles, trends, and curve structure for VIXY/VIXM."""
    try:
        manager = MarketDataManager()
        # Fetch histories
        vixy_data = await manager.get_history("VIXY", days=lookback_days)
        vixm_data = await manager.get_history("VIXM", days=lookback_days)
        spy_data = await manager.get_history("SPY", days=lookback_days)

        if not vixy_data or not vixm_data or not spy_data:
            return "Error: Could not retrieve price history for VIXY, VIXM, or SPY."

        # Map to dates
        vixy_by_date = {row["fetched_at"][:10]: float(row["price"]) for row in vixy_data}
        vixm_by_date = {row["fetched_at"][:10]: float(row["price"]) for row in vixm_data}
        spy_by_date = {row["fetched_at"][:10]: float(row["price"]) for row in spy_data}

        # Align on overlapping dates
        common_dates = sorted(list(set(vixy_by_date.keys()) & set(vixm_by_date.keys()) & set(spy_by_date.keys())))

        if len(common_dates) < 5:
            return f"Insufficient overlapping price history (found only {len(common_dates)} days) to compute volatility metrics."

        # Build chronological price lists
        vixy_prices = [vixy_by_date[d] for d in common_dates]
        vixm_prices = [vixm_by_date[d] for d in common_dates]
        spy_prices = [spy_by_date[d] for d in common_dates]

        # Calculate daily returns
        vixy_returns = []
        vixm_returns = []
        spy_returns = []
        for i in range(1, len(common_dates)):
            vixy_returns.append((vixy_prices[i] - vixy_prices[i - 1]) / vixy_prices[i - 1])
            vixm_returns.append((vixm_prices[i] - vixm_prices[i - 1]) / vixm_prices[i - 1])
            spy_returns.append((spy_prices[i] - spy_prices[i - 1]) / spy_prices[i - 1])

        import statistics

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

        # 1. Current Stats & Daily Change
        curr_vixy = vixy_prices[-1]
        curr_vixm = vixm_prices[-1]
        vixy_1d_return = vixy_returns[-1] * 100 if vixy_returns else 0.0
        vixm_1d_return = vixm_returns[-1] * 100 if vixm_returns else 0.0

        # 2. realized Volatilities (Annualized Standard Deviation)
        # Using up to last 30 daily returns
        sub_returns_vixy = vixy_returns[-30:]
        vixy_realized_vol = statistics.stdev(sub_returns_vixy) * (252**0.5) * 100 if len(sub_returns_vixy) >= 2 else 0.0

        # 3. Volatility of Volatility (VVIX proxy - 10-day realized volatility of VIXY)
        sub_returns_10d = vixy_returns[-10:]
        vix_vol_of_vol = statistics.stdev(sub_returns_10d) * (252**0.5) * 100 if len(sub_returns_10d) >= 2 else 0.0

        # 4. Percentiles over lookback window
        smaller_vixy = sum(1 for p in vixy_prices if p < curr_vixy)
        vixy_price_percentile = (smaller_vixy / len(vixy_prices)) * 100

        # 5. Moving Average Trends
        sma_10 = sum(vixy_prices[-10:]) / min(10, len(vixy_prices))
        sma_30 = sum(vixy_prices[-30:]) / min(30, len(vixy_prices))
        if curr_vixy > sma_10 > sma_30:
            trend_state = "STRONG VOLATILITY EXPANSION (VIXY > SMA_10 > SMA_30)"
        elif curr_vixy < sma_10 < sma_30:
            trend_state = "STRONG VOLATILITY CONTRACTION (VIXY < SMA_10 < SMA_30)"
        elif curr_vixy > sma_30:
            trend_state = "MODERATE VOLATILITY EXPANSION (VIXY > SMA_30)"
        else:
            trend_state = "CONSOLIDATION / MEAN REVERSION"

        # 6. Term Structure (VIXY/VIXM ratio)
        ratios = [vixy_prices[idx] / vixm_prices[idx] for idx in range(len(vixy_prices))]
        curr_ratio = ratios[-1]
        smaller_ratio = sum(1 for r in ratios if r < curr_ratio)
        ratio_percentile = (smaller_ratio / len(ratios)) * 100

        if curr_ratio > 0.95 or ratio_percentile > 85:
            curve_state = (
                f"BACKWARDATION / MARKET STRESS (Ratio: {curr_ratio:.3f}, Percentile: {ratio_percentile:.1f}%)"
            )
        elif curr_ratio < 0.78 or ratio_percentile < 15:
            curve_state = (
                f"STRONG CONTANGO / COMPLACENCY (Ratio: {curr_ratio:.3f}, Percentile: {ratio_percentile:.1f}%)"
            )
        else:
            curve_state = f"NORMAL CONTANGO (Ratio: {curr_ratio:.3f}, Percentile: {ratio_percentile:.1f}%)"

        # 7. Pearson Correlation with SPY
        sub_returns_spy = spy_returns[-30:]
        spy_correlation_30d = pearson_correlation(sub_returns_vixy, sub_returns_spy)

        # 8. Overall Volatility Regime
        if vixy_price_percentile >= 85:
            regime = "⚠️ PANIC ZONE / EXTREME FEAR (VIXY price at upper 15% range)"
        elif vixy_price_percentile <= 15:
            regime = "🟢 COMPLACENCY ZONE / LOW VOLATILITY (VIXY price at lower 15% range)"
        else:
            regime = "NORMAL VOLATILITY / REGULAR REGIME"

        return (
            f"=== Volatility Index (VIX) Proxy Details ===\n"
            f"- VIXY (Short-Term Volatility ETF): ${curr_vixy:.2f} [{vixy_1d_return:+.2f}% today]\n"
            f"- VIXM (Mid-Term Volatility ETF):   ${curr_vixm:.2f} [{vixm_1d_return:+.2f}% today]\n"
            f"- VIXY 30d Realized Volatility:     {vixy_realized_vol:.2f}%\n"
            f"- Volatility of Volatility (VVIX Proxy): {vix_vol_of_vol:.2f}%\n"
            f"- VIXY Price Percentile ({len(vixy_prices)} trading days): {vixy_price_percentile:.1f}%\n"
            f"- Volatility Regime:                {regime}\n"
            f"- Moving Average Trend:             {trend_state}\n"
            f"- Volatility Curve Structure:       {curve_state}\n"
            f"- Correlation with SPY (30d):       {spy_correlation_30d:+.3f}"
        )
    except Exception as e:
        logger.exception(f"Error in execute_get_volatility_index_details_tool: {e}")
        return f"Error retrieving volatility index details: {str(e)}"


async def execute_get_verifier_rejections_tool(
    ticker: str | None = None, limit: int = 5, model_name: str | None = None
) -> str:
    """Retrieve recent trade rejection logs and verifier feedback reasons from the database."""
    import inspect
    import json

    try:
        sb_client = await get_async_supabase_client()
        query = (
            sb_client.table("decisions")
            .select("id, ticker, signal, status, reasoning, model_name, metadata, created_at")
            .order("created_at", desc=True)
            .limit(limit * 2)
        )
        if ticker:
            query = query.eq("ticker", ticker.upper())

        res = query.execute()
        if inspect.isawaitable(res):
            res = await res
        rows = res.data or []

        rejected_rows = [r for r in rows if str(r.get("status", "")).startswith("REJECTED_")][:limit]
        if not rejected_rows:
            return "No trade rejections found matching the criteria."

        lines = [f"=== Recent Trade Rejections & Verifier Feedback (Count: {len(rejected_rows)}) ==="]
        for r in rejected_rows:
            meta = r.get("metadata")
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            elif not isinstance(meta, dict):
                meta = {}

            reason = meta.get("reason") or meta.get("info") or "No explicit verifier reason recorded"
            agent_thesis = r.get("reasoning", "") or ""
            if len(agent_thesis) > 150:
                agent_thesis = agent_thesis[:150] + "..."

            lines.append(
                f"- [{r.get('status')}] {r.get('signal')} {r.get('ticker')} (Model: {r.get('model_name') or 'N/A'})\n"
                f"  • Verifier Reason: {reason}\n"
                f"  • Agent Thesis: {agent_thesis}"
            )

        return "\n".join(lines)
    except Exception as e:
        logger.exception(f"Error in execute_get_verifier_rejections_tool: {e}")
        return f"Error retrieving verifier rejections: {str(e)}"


async def execute_web_search_tool(query: str, max_results: int = 5) -> str:
    """Performs a live web search for financial news, market reports, and catalysts.

    Args:
        query: The search query string.
        max_results: Max number of search snippets to return.

    Returns:
        Formatted markdown string containing search results.
    """
    if not query or not query.strip():
        return "Error: Empty search query provided."

    query_str = query.strip()
    logger.info(f"Executing web_search tool for query: '{query_str}'")

    results = []

    # 1. Primary: DuckDuckGo HTML search
    try:
        import httpx
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query_str},
                headers=headers,
            )

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                result_blocks = soup.find_all("div", class_=lambda c: c and "result" in c)
                for block in result_blocks:
                    title_elem = block.find("a", class_=lambda c: c and "title" in c) or block.find(
                        "a", class_="result__url"
                    )
                    snippet_elem = block.find("div", class_=lambda c: c and "snippet" in c) or block.find(
                        "a", class_="result__snippet"
                    )
                    url_elem = block.find("a", class_=lambda c: c and "url" in c) or title_elem

                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)
                        href = url_elem.get("href", "") if url_elem else ""
                        if title and snippet:
                            results.append({"title": title, "snippet": snippet, "url": href})
                            if len(results) >= max_results:
                                break

    except Exception as e:
        logger.warning(f"DuckDuckGo web search encountered error: {e}")

    # 2. Fallback: FMP Stock News Search if ticker is present in query or general search had no hits
    if not results:
        try:
            import httpx

            from execution.providers.fmp import FMPProvider

            fmp = FMPProvider()
            if fmp.api_key:
                words = query_str.split()
                candidate_tickers = [
                    w.strip("$,.:;\"'()")
                    for w in words
                    if w.strip("$,.:;\"'()").isupper() and 1 <= len(w.strip("$,.:;\"'()")) <= 5
                ]
                ticker_to_search = candidate_tickers[0] if candidate_tickers else "LIN"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    fmp_resp = await client.get(
                        "https://financialmodelingprep.com/api/v3/stock_news",
                        params={"tickers": ticker_to_search, "limit": max_results, "apikey": fmp.api_key},
                    )
                    if fmp_resp.status_code == 200:
                        news_items = fmp_resp.json()
                        if isinstance(news_items, list):
                            for item in news_items[:max_results]:
                                results.append(
                                    {
                                        "title": item.get("title", ""),
                                        "snippet": item.get("text", "")[:250] + "...",
                                        "url": item.get("url", ""),
                                    }
                                )
        except Exception as e:
            logger.warning(f"FMP news search fallback failed: {e}")

    if not results:
        return f"No relevant web search results found for '{query_str}'."

    lines = [f"=== WEB SEARCH RESULTS FOR '{query_str}' ==="]
    for i, r in enumerate(results, 1):
        url_part = f" ({r['url']})" if r.get("url") else ""
        lines.append(f"{i}. {r['title']}{url_part}\n   {r['snippet']}")

    return "\n\n".join(lines)


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
