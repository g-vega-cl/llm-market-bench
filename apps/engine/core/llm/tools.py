"""Tool definitions and execution logic for LLMs.

Tool definitions are stored in a single canonical format (OpenAI Chat Completions
function-tool schema). Handlers translate to provider-specific formats via
``to_anthropic`` / ``to_gemini`` at the boundary.
"""

from typing import Any

from core.db import (
    get_async_supabase_client as get_async_supabase_client,
)
from core.db import (
    get_supabase_client as get_supabase_client,
)
from execution.market_data import MarketDataManager as MarketDataManager
from memory.embeddings import get_embedding as get_embedding
from tools.analyst_personas import (
    execute_analyze_thematic_beneficiaries_tool as execute_analyze_thematic_beneficiaries_tool,
)
from tools.analyst_personas import (
    execute_call_warren_buffett_tool as execute_call_warren_buffett_tool,
)
from tools.analyst_personas import (
    execute_get_future_forces_tool as execute_get_future_forces_tool,
)
from tools.analyst_personas import (
    execute_research_future_force_tool as execute_research_future_force_tool,
)
from tools.analyst_personas import (
    execute_research_historical_market_analog_tool as execute_research_historical_market_analog_tool,
)
from tools.compliance import (
    execute_get_calendar_scenario_analysis_tool as execute_get_calendar_scenario_analysis_tool,
)
from tools.compliance import (
    execute_get_catalyst_radar_tool as execute_get_catalyst_radar_tool,
)
from tools.compliance import (
    execute_get_congress_trades_tool as execute_get_congress_trades_tool,
)
from tools.compliance import (
    execute_get_insider_trades_tool as execute_get_insider_trades_tool,
)
from tools.compliance import (
    execute_get_verifier_rejections_tool as execute_get_verifier_rejections_tool,
)
from tools.compliance import (
    execute_get_whale_holdings_tool as execute_get_whale_holdings_tool,
)
from tools.compliance import (
    execute_inspect_verifier_rules_tool as execute_inspect_verifier_rules_tool,
)
from tools.compliance import (
    execute_track_thesis_pillars_tool as execute_track_thesis_pillars_tool,
)
from tools.earnings import (
    execute_earnings_history_tool as execute_earnings_history_tool,
)
from tools.earnings import (
    execute_earnings_revisions_tool as execute_earnings_revisions_tool,
)
from tools.earnings import (
    execute_pead_candidates_tool as execute_pead_candidates_tool,
)
from tools.earnings import (
    execute_search_related_tickers_tool as execute_search_related_tickers_tool,
)
from tools.earnings import (
    execute_sector_alternatives_tool as execute_sector_alternatives_tool,
)
from tools.earnings import (
    execute_sector_bellwethers_tool as execute_sector_bellwethers_tool,
)
from tools.macro import (
    execute_get_global_macro_context_tool as execute_get_global_macro_context_tool,
)
from tools.macro import (
    execute_get_today_economic_releases_tool as execute_get_today_economic_releases_tool,
)
from tools.macro import (
    execute_get_treasury_yield_curve_tool as execute_get_treasury_yield_curve_tool,
)
from tools.macro import (
    execute_get_volatility_index_details_tool as execute_get_volatility_index_details_tool,
)
from tools.macro import (
    execute_macro_economic_series_tool as execute_macro_economic_series_tool,
)
from tools.macro import (
    execute_yield_curve_regime_tool as execute_yield_curve_regime_tool,
)
from tools.market_data import (
    compute_volume_context as compute_volume_context,
)
from tools.market_data import (
    execute_get_intraday_movement_profile_tool as execute_get_intraday_movement_profile_tool,
)
from tools.market_data import (
    execute_get_ticker_news_tool as execute_get_ticker_news_tool,
)
from tools.market_data import (
    execute_price_history_tool as execute_price_history_tool,
)
from tools.market_data import (
    execute_stock_tool as execute_stock_tool,
)
from tools.news_memories import (
    active_news_chunks as active_news_chunks,
)
from tools.news_memories import (
    active_news_summaries as active_news_summaries,
)
from tools.news_memories import (
    execute_add_thematic_flow_tool as execute_add_thematic_flow_tool,
)
from tools.news_memories import (
    execute_fetch_daily_newsletter_tool as execute_fetch_daily_newsletter_tool,
)
from tools.news_memories import (
    execute_fetch_newsletter_content_tool as execute_fetch_newsletter_content_tool,
)
from tools.news_memories import (
    execute_get_market_feeling_tool as execute_get_market_feeling_tool,
)
from tools.news_memories import (
    execute_get_market_moving_news_tool as execute_get_market_moving_news_tool,
)
from tools.news_memories import (
    execute_get_thematic_flows_tool as execute_get_thematic_flows_tool,
)
from tools.news_memories import (
    execute_get_todays_news_menu_tool as execute_get_todays_news_menu_tool,
)
from tools.news_memories import (
    execute_search_past_memories_tool as execute_search_past_memories_tool,
)
from tools.news_memories import (
    execute_web_search_tool as execute_web_search_tool,
)
from tools.portfolio import (
    execute_buy_quantity_tool as execute_buy_quantity_tool,
)
from tools.portfolio import (
    execute_get_portfolio_ledger_tool as execute_get_portfolio_ledger_tool,
)
from tools.portfolio import (
    execute_get_system_portfolios_tool as execute_get_system_portfolios_tool,
)
from tools.portfolio import (
    execute_position_pnl_tool as execute_position_pnl_tool,
)
from tools.portfolio import (
    execute_sell_quantity_tool as execute_sell_quantity_tool,
)
from tools.prediction_markets import (
    execute_get_prediction_market_odds_tool as execute_get_prediction_market_odds_tool,
)
from tools.prediction_markets import (
    execute_search_prediction_markets_tool as execute_search_prediction_markets_tool,
)
from tools.technicals_options import (
    execute_barrier_touch_probabilities_tool as execute_barrier_touch_probabilities_tool,
)
from tools.technicals_options import (
    execute_find_uncorrelated_assets_tool as execute_find_uncorrelated_assets_tool,
)
from tools.technicals_options import (
    execute_get_macro_options_sentiment_tool as execute_get_macro_options_sentiment_tool,
)
from tools.technicals_options import (
    execute_get_option_chain_tool as execute_get_option_chain_tool,
)
from tools.technicals_options import (
    execute_get_options_sentiment_tool as execute_get_options_sentiment_tool,
)
from tools.technicals_options import (
    execute_options_vol_surface_tool as execute_options_vol_surface_tool,
)
from tools.technicals_options import (
    execute_stock_screener_tool as execute_stock_screener_tool,
)
from tools.technicals_options import (
    execute_volatility_metrics_tool as execute_volatility_metrics_tool,
)
from tools.valuation import (
    GICS_TO_SECTOR_ETF as GICS_TO_SECTOR_ETF,
)
from tools.valuation import (
    TICKER_TO_SECTOR_ETF as TICKER_TO_SECTOR_ETF,
)
from tools.valuation import (
    execute_financial_valuation_tool as execute_financial_valuation_tool,
)
from tools.valuation import (
    execute_key_metrics_tool as execute_key_metrics_tool,
)
from tools.valuation import (
    execute_market_health_barometer_tool as execute_market_health_barometer_tool,
)
from tools.valuation import (
    execute_sector_fundamentals_tool as execute_sector_fundamentals_tool,
)

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

GET_SECTOR_FUNDAMENTALS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_sector_fundamentals",
        "description": (
            "Retrieve aggregated sector-level fundamentals across US Sector ETFs (XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLU, XLRE, XLB, XLC), "
            "including cap-weighted Trailing P/E, Forward P/E, and quarterly Earnings Beat Rates computed from S&P 500 constituents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of top sectors to return (default: 11 for all major sectors).",
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


GET_PEAD_CANDIDATES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_pead_candidates",
        "description": (
            "Retrieve top-decile Post-Earnings Announcement Drift (PEAD) candidates with calculated "
            "Standardized Unexpected Earnings (SUE) scores, revenue surprises, Sloan accrual quality checks, and drift returns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "Optional sector ETF filter (e.g., XLK, XLF, XLE).",
                },
                "min_sue": {
                    "type": "number",
                    "description": "Minimum SUE score threshold (default: 2.0 for top-decile surprise).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of candidates to return (default: 15).",
                },
            },
            "required": [],
        },
    },
}


GET_EARNINGS_REVISIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_earnings_revisions",
        "description": (
            "Retrieve analyst consensus ratings, buy/hold/sell distribution, and consensus price target "
            "upside for a specific stock ticker."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., NVDA, AAPL, MSFT)",
                },
            },
            "required": ["ticker"],
        },
    },
}


GET_SECTOR_BELLWETHERS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_sector_bellwethers",
        "description": (
            "Retrieve reported earnings signals from sector bellwethers and view the upcoming unannounced "
            "peers for a specific sector ETF."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "The US Sector ETF symbol (e.g., XLK, XLF, XLE, XLI, XLY, XLP, XLV, XLC).",
                },
            },
            "required": ["sector"],
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
        "description": "Fetch canonical Cboe Volatility Index (spot VIX: ^VIX) historical levels, percentiles, and volatility regimes, alongside VIX futures ETF term structure (VIXY vs VIXM ratio, contango/backwardation, and roll decay metrics).",
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

INSPECT_VERIFIER_RULES_TOOL = {
    "type": "function",
    "function": {
        "name": "inspect_verifier_rules_and_rejections",
        "description": (
            "Inspect the skeptical verifier system prompt (SOP rules, DCF intrinsic valuation checks, "
            "and volatility hurdles) and retrieve recent verifier-rejected trades for track_claude. "
            "Only available for track_claude portfolios."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent rejection records to retrieve (default: 5).",
                },
                "ticker": {
                    "type": "string",
                    "description": "Optional ticker symbol to filter rejections by.",
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

GET_TREASURY_YIELD_CURVE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_treasury_yield_curve",
        "description": (
            "Fetch live US Treasury benchmark yields across the curve (3M, 2Y, 5Y, 10Y, 30Y) with 1-day basis-point "
            "changes and key slope spreads (10Y-2Y, 10Y-3M, 30Y-10Y). Indispensable for assessing interest rate "
            "expectations, bond market direction, and duration risk."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_YIELD_CURVE_REGIME_TOOL = {
    "type": "function",
    "function": {
        "name": "get_yield_curve_regime",
        "description": (
            "Analyze the US Treasury yield curve slope (10Y-2Y, 10Y-3M, 30Y-5Y) and 5-day delta to classify "
            "the macroeconomic monetary flow regime into: BULL_STEEPENER, BULL_FLATTENER, BEAR_STEEPENER, or BEAR_FLATTENER, "
            "with historical factor tailwinds (e.g. Mega-Cap Tech vs Small-Caps vs Energy)."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_OPTIONS_VOL_SURFACE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_options_vol_surface",
        "description": (
            "Calculates options implied volatility surface, trailing 20-day realized volatility, "
            "the options-implied daily move price cone (Spot * IV / sqrt(252)), 25-delta skew, "
            "and implied volatility premium (IV - RV) to classify rich vs cheap options regimes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock or ETF ticker symbol (e.g., SPY, QQQ, AAPL, NVDA). Default 'SPY'.",
                },
            },
            "required": ["ticker"],
        },
    },
}

TRACK_THESIS_PILLARS_TOOL = {
    "type": "function",
    "function": {
        "name": "track_thesis_pillars",
        "description": (
            "Query, create, or update structured multi-day falsifiable investment theses with explicit "
            "supporting pillars, invalidation risks, price targets, stop-losses, and a disconfirming evidence ledger. "
            "Registering disconfirming evidence dynamically transitions conviction states (HIGH -> WEAKENED -> INVALIDATED)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock or asset ticker symbol.",
                },
                "action": {
                    "type": "string",
                    "enum": ["get", "create", "disconfirm", "invalidate"],
                    "description": "Operation: 'get' (retrieve active thesis), 'create' (establish new thesis), 'disconfirm' (record disconfirming signal), or 'invalidate'.",
                },
                "thesis_statement": {
                    "type": "string",
                    "description": "Core 1-2 sentence thesis rationale (for 'create').",
                },
                "pillars": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-5 key supporting arguments (for 'create').",
                },
                "risks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key invalidation risks to monitor (for 'create').",
                },
                "disconfirming_factor": {
                    "type": "string",
                    "description": "Observed market signal, data point, or event contradicting the thesis (for 'disconfirm').",
                },
                "pillar_impacted": {
                    "type": "string",
                    "description": "Specific pillar weakened by the disconfirming signal (for 'disconfirm').",
                },
                "price_target": {
                    "type": "number",
                    "description": "Target price for thesis resolution.",
                },
                "stop_loss": {
                    "type": "number",
                    "description": "Stop-loss price level.",
                },
                "conviction": {
                    "type": "string",
                    "enum": ["HIGH", "MEDIUM", "LOW"],
                    "description": "Initial conviction level (for 'create').",
                },
            },
            "required": ["ticker", "action"],
        },
    },
}


GET_CATALYST_RADAR_TOOL = {
    "type": "function",
    "function": {
        "name": "get_catalyst_radar",
        "description": "Retrieve high-velocity market concepts paired with upcoming or digesting calendar triggers (CPI, earnings, FOMC, deadlines).",
        "parameters": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Forward-looking window in calendar days (e.g. 7 for '1 week from now', 14 for 2 weeks). Defaults to 7.",
                },
                "include_digesting": {
                    "type": "boolean",
                    "description": "Include events from the past 1-3 days currently in market digestion. Defaults to true.",
                },
                "min_velocity": {
                    "type": "number",
                    "description": "Minimum concept velocity score (higher = faster accelerating mentions). Defaults to 1.2.",
                },
                "detail": {
                    "type": "boolean",
                    "description": "If true, returns full excerpts and scenario details; if false, returns a compact at-a-glance table. Defaults to false.",
                },
            },
        },
    },
}


GET_CALENDAR_SCENARIO_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_calendar_scenario_analysis",
        "description": "Retrieve upcoming economic and corporate calendar triggers paired with probability-weighted scenario analyses, conditional trading plans, and affected assets for tomorrow, next week, or custom forward horizons.",
        "parameters": {
            "type": "object",
            "properties": {
                "timeframe": {
                    "type": "string",
                    "enum": ["today", "tomorrow", "next_week", "next_14_days", "all_upcoming"],
                    "description": "Forward-looking time horizon: 'today' (current trading day), 'tomorrow' (next trading day), 'next_week' (next 7 days, default), 'next_14_days', or 'all_upcoming'.",
                },
                "ticker": {
                    "type": "string",
                    "description": "Optional ticker symbol (e.g. SPY, NVDA, AAPL) to filter for events, scenarios, or assets relevant to a specific company.",
                },
                "min_importance": {
                    "type": "integer",
                    "description": "Minimum importance score (1-10) for calendar triggers. Defaults to 5.",
                },
                "detail": {
                    "type": "boolean",
                    "description": "If true, returns full multi-scenario breakdowns, conditional execution plans, and discovered assets. Defaults to true.",
                },
                "include_historical_memories": {
                    "type": "boolean",
                    "description": "If true, cross-references historical precedents and past lessons learned for matched catalysts. Defaults to true.",
                },
            },
        },
    },
}


GET_BARRIER_TOUCH_PROBABILITIES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_barrier_touch_probabilities",
        "description": "Empirical Triple Barrier Method touch probabilities conditional on market regime. Calculates the historical percentage of times price touched the profit target (+X%) before the stop loss (-Y%), or expired at the vertical time stop, within the current trend and volatility state.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock or ETF ticker symbol (e.g. SPY, QQQ, NVDA).",
                },
                "target_pct": {
                    "type": "number",
                    "description": "Optional upper profit-take barrier percentage (e.g. 2.0 for +2.0%). Defaults to 1.5x local ATR.",
                },
                "stop_pct": {
                    "type": "number",
                    "description": "Optional lower stop-loss barrier percentage (e.g. 1.5 for -1.5%). Defaults to 1.0x local ATR.",
                },
                "horizon_bars": {
                    "type": "integer",
                    "description": "Vertical time barrier (holding period in daily bars, default 5).",
                },
                "lookback_days": {
                    "type": "integer",
                    "description": "Historical days of lookback for regime matching (default 252).",
                },
            },
            "required": ["ticker"],
        },
    },
}

GET_TICKER_NEWS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_ticker_news",
        "description": "Real-time stock news headlines, publisher sources, and summaries for a specific stock ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g. 'AAPL', 'NVDA', 'SPY').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent news articles to return (1-20, default 5).",
                },
            },
            "required": ["ticker"],
        },
    },
}

GET_MARKET_MOVING_NEWS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_market_moving_news",
        "description": "Real-time intraday market-moving events, macro surprises (ISM PMI, Jobs, CPI), Fed remarks, and breaking catalysts vetted by TypeSafe Jev.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of market-moving catalysts to return (1-20, default 8).",
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Whether to force an on-demand re-sync of the news feed bypassing the 15-minute cache (default false).",
                },
            },
        },
    },
}

GET_CONGRESS_TRADES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_congress_trades",
        "description": "Retrieve stock trading disclosures by US Congress members (Senate and House) under the STOCK Act.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional stock ticker symbol (e.g. 'NVDA', 'AAPL'). Omit to get broad recent trades across all tickers.",
                },
                "chamber": {
                    "type": "string",
                    "description": "Optional chamber filter: 'senate' or 'house'. Omit for both.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of disclosures to look back (default 45).",
                },
                "transaction_type": {
                    "type": "string",
                    "description": "Optional transaction type filter: 'purchase' or 'sale'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of records to return (default 20).",
                },
            },
            "required": [],
        },
    },
}

GET_INSIDER_TRADES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_insider_trades",
        "description": "Retrieve corporate insider trading disclosures (SEC Form 4) for C-suite executives, directors, and 10%+ owners.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. 'NVDA', 'AAPL').",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of disclosures to look back (default 90).",
                },
                "transaction_type": {
                    "type": "string",
                    "description": "Optional transaction type filter: 'purchase', 'sale', or 'all' (default 'all').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of records to return (default 15).",
                },
            },
            "required": ["ticker"],
        },
    },
}

GET_WHALE_HOLDINGS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_whale_holdings",
        "description": "Retrieve institutional whale holdings and blockholders: Schedule 13D/13G (>5% owners) for a stock, or Form 13F portfolio holdings for a major fund.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional stock ticker symbol (e.g. 'NVDA') to view top institutional blockholders and 13D/13G whale positions.",
                },
                "fund_name": {
                    "type": "string",
                    "description": "Optional curated whale fund name (e.g. 'BERKSHIRE_HATHAWAY', 'COATUE', 'APPALOOSA', 'WHALE_ROCK', 'DUQUESNE') to inspect 13F portfolio.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of holdings/filers to return (default 15).",
                },
            },
            "required": [],
        },
    },
}

ANALYZE_THEMATIC_BENEFICIARIES_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_thematic_beneficiaries",
        "description": "Screens second-order winners and thematic beneficiaries via factor correlation, beta sensitivity, and options positioning relative to an anchor ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "anchor_ticker": {
                    "type": "string",
                    "description": "The primary anchor ticker driving the theme (e.g. 'NVDA' for AI, 'LLY' for GLP-1).",
                },
                "theme": {
                    "type": "string",
                    "description": "Optional human-readable theme name or hypothesis (e.g. 'AI Power & Memory', 'GLP-1 Apparel Shift').",
                },
                "candidate_tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional explicit list of candidate peer tickers to evaluate against the anchor.",
                },
                "candidate_industries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of FMP industries to screen candidates from (e.g. ['Regulated Electric', 'Electrical Equipment & Parts']).",
                },
                "candidate_sectors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of FMP sectors to screen candidates from (e.g. ['Utilities', 'Industrials']).",
                },
                "lookback_days": {
                    "type": "integer",
                    "description": "Lookback window in trading days for calculating correlation, beta, and momentum (default 60).",
                },
                "include_institutional": {
                    "type": "boolean",
                    "description": "Whether to cluster SEC Form 13F institutional co-ownership across top funds (default false).",
                },
            },
            "required": ["anchor_ticker"],
        },
    },
}


GET_TODAY_ECONOMIC_RELEASES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_today_economic_releases",
        "description": "Retrieve scheduled and released economic indicators (CPI, PPI, Nonfarm Payrolls, Retail Sales, Unemployment Rate, GDP, Initial Claims) for today or a target date with live actual vs. consensus prints, economic surprises, and release status.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {
                    "type": "string",
                    "description": "Optional target date (YYYY-MM-DD). Defaults to current date in Eastern Time.",
                },
                "country": {
                    "type": "string",
                    "description": "Optional country filter (defaults to 'US'). Pass empty string or null for global releases.",
                },
            },
        },
    },
}

CALL_WARREN_BUFFETT_TOOL = {
    "type": "function",
    "function": {
        "name": "call_warren_buffett",
        "description": (
            "Consult the Oracle of Omaha. Evaluates a ticker or broad market trade through Warren Buffett and Charlie Munger "
            "value investing principles, margin of safety, economic moat (ROIC/ROE), debt sanity ('swimming naked' check), "
            "and the Munger Inversion test ('Would a stupid person do this?')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional ticker symbol to evaluate (e.g. 'AAPL', 'NVDA'). If omitted, audits broad market valuation and cash allocation.",
                },
                "action": {
                    "type": "string",
                    "enum": ["BUY", "SELL", "HOLD"],
                    "description": "Optional proposed action to stress-test against the Munger Inversion test.",
                },
                "proposed_thesis": {
                    "type": "string",
                    "description": "Optional brief rationale or catalyst for the proposed trade to be audited.",
                },
            },
            "required": [],
        },
    },
}

GET_INTRADAY_MOVEMENT_PROFILE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_intraday_movement_profile",
        "description": (
            "Deterministic quantitative profile and hourly price-action tape matrix of a stock's regular "
            "trading session (09:30-16:00 ET). Analyzes Initial Balance (IB 09:30-10:30 ET) breakout, VWAP, "
            "Close Location Value (CLV in [-1.0, +1.0]), session range vs ATR, and classifies session archetype "
            "(TREND_DAY_UP, TREND_DAY_DOWN, MORNING_DIP_AND_RIP, GAP_AND_CRAP, RANGE_BOUND_CHURN)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock or ETF ticker symbol (e.g. 'SPY', 'QQQ', 'NVDA'). Defaults to 'SPY'.",
                },
                "date": {
                    "type": "string",
                    "description": (
                        "Target date to analyze in ISO format ('YYYY-MM-DD') or 'latest_completed' / 'yesterday'. "
                        "Defaults to 'latest_completed'."
                    ),
                },
                "include_hourly_tape": {
                    "type": "boolean",
                    "description": "If true, includes the hourly progression tape matrix with ASCII range brackets. Defaults to true.",
                },
            },
            "required": [],
        },
    },
}

RESEARCH_HISTORICAL_MARKET_ANALOG_TOOL = {
    "type": "function",
    "function": {
        "name": "research_historical_market_analog",
        "description": (
            "Research historical market precedent episodes, cross-asset reaction tapes (stocks, bonds, gold, crypto, dollar), "
            "and actionable profit playbooks. Uses ChatGPT Luna with thinking to identify the most structurally similar "
            "historical analog episode, pulls empirical historical price performance across major benchmarks, and synthesizes "
            "key macro divergences, asymmetric long/short expressions, and falsification triggers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "situation": {
                    "type": "string",
                    "description": "Natural language description of current market setup or catalyst (e.g. 'Bond prices rising sharply amidst Middle East tensions').",
                },
                "focus_assets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific tickers to measure alongside core macro benchmarks.",
                },
                "horizon": {
                    "type": "string",
                    "description": "Reaction horizon to evaluate (e.g. '1w', '1m', '3m'). Defaults to '1m'.",
                },
            },
            "required": ["situation"],
        },
    },
}

GET_FUTURE_FORCES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_future_forces",
        "description": (
            "Retrieve active multi-horizon market forces (2 to 24 months), catalyst milestones, "
            "and falsification criteria across 7 canonical archetypes (geopolitical chokepoints, "
            "government agendas, sleeping giants, latent distribution turn-ons, AI threat surface toll roads, "
            "clinical TAM explosions, and mega-events)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "archetype": {
                    "type": "string",
                    "description": (
                        "Optional filter by archetype: 'geopolitical_chokepoint', 'government_agenda', "
                        "'sleeping_giant', 'distribution_turnon', 'secular_tollroad', 'tam_explosion', "
                        "'mega_event', 'deep_value_turnaround'."
                    ),
                },
                "max_horizon_months": {
                    "type": "integer",
                    "description": "Optional upper ceiling for horizon in months (e.g. 3, 6, 12, 24). Defaults to 24.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of active forces to return (default: 5).",
                },
            },
            "required": [],
        },
    },
}

RESEARCH_FUTURE_FORCE_TOOL = {
    "type": "function",
    "function": {
        "name": "research_future_force",
        "description": (
            "Stress-tests a forward-looking catalyst or thematic thesis using OpenAI Luna (with thinking). "
            "Audits whether the move is already priced in, verifies the economic transmission mechanism to GAAP EPS, "
            "and formalizes testable falsification criteria (Thesis Death)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "force_title": {
                    "type": "string",
                    "description": "Short, descriptive title of the force (e.g. 'Hormuz Tanker Squeeze', 'World Cup Travel Squeeze').",
                },
                "archetype": {
                    "type": "string",
                    "description": "Archetype: 'geopolitical_chokepoint', 'government_agenda', 'sleeping_giant', 'distribution_turnon', 'secular_tollroad', 'tam_explosion', 'mega_event', 'deep_value_turnaround'.",
                },
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Primary beneficiary or expression tickers (e.g. ['FRO', 'STNG'] or ['ABNB']).",
                },
                "thesis": {
                    "type": "string",
                    "description": "Causal thesis explaining why this move is underappreciated by the market.",
                },
                "catalyst_event": {
                    "type": "string",
                    "description": "Upcoming milestone or event that forces market recognition.",
                },
                "horizon_months": {
                    "type": "integer",
                    "description": "Estimated timeframe in months (must be between 2 and 24). Defaults to 3.",
                },
                "invalidation_triggers": {
                    "type": "string",
                    "description": "Explicit falsification conditions that would immediately kill the thesis.",
                },
                "transmission_mechanism": {
                    "type": "string",
                    "description": "Financial mechanism converting the force into GAAP EPS or multiple re-rating.",
                },
            },
            "required": [
                "force_title",
                "archetype",
                "thesis",
                "catalyst_event",
                "invalidation_triggers",
                "transmission_mechanism",
            ],
        },
    },
}

GET_SYSTEM_PORTFOLIOS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_system_portfolios",
        "description": "Inspect mechanical system portfolios (mean reversion, momentum trends, sector long/short, intraday SPY) for positions, signals, and benchmark returns.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["all", "mean_reversion", "momentum", "sector_ls", "daily_spy", "thematic"],
                    "description": "Strategy filter: 'all', 'mean_reversion' (7d oversold bounce), 'momentum' (20d unconstrained and uncorrelated trend), 'sector_ls' (consensus long/short), 'daily_spy' (intraday SPY target/close), or 'thematic' (future forces & frontier tech). Defaults to 'all'.",
                },
                "include_positions": {
                    "type": "boolean",
                    "description": "Whether to include detailed stock/ETF holdings, entry prices, and unrealized PnL. Defaults to true.",
                },
                "lookback_days": {
                    "type": "integer",
                    "description": "Trailing window in days to evaluate portfolio return and equity drift. Defaults to 7.",
                },
            },
            "required": [],
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
    "get_sector_fundamentals": GET_SECTOR_FUNDAMENTALS_TOOL,
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
    "get_pead_candidates": GET_PEAD_CANDIDATES_TOOL,
    "get_earnings_revisions": GET_EARNINGS_REVISIONS_TOOL,
    "get_sector_bellwethers": GET_SECTOR_BELLWETHERS_TOOL,
    "get_treasury_yield_curve": GET_TREASURY_YIELD_CURVE_TOOL,
    "get_yield_curve_regime": GET_YIELD_CURVE_REGIME_TOOL,
    "get_options_vol_surface": GET_OPTIONS_VOL_SURFACE_TOOL,
    "track_thesis_pillars": TRACK_THESIS_PILLARS_TOOL,
    "get_catalyst_radar": GET_CATALYST_RADAR_TOOL,
    "get_calendar_scenario_analysis": GET_CALENDAR_SCENARIO_ANALYSIS_TOOL,
    "get_barrier_touch_probabilities": GET_BARRIER_TOUCH_PROBABILITIES_TOOL,
    "get_ticker_news": GET_TICKER_NEWS_TOOL,
    "get_congress_trades": GET_CONGRESS_TRADES_TOOL,
    "get_insider_trades": GET_INSIDER_TRADES_TOOL,
    "get_whale_holdings": GET_WHALE_HOLDINGS_TOOL,
    "analyze_thematic_beneficiaries": ANALYZE_THEMATIC_BENEFICIARIES_TOOL,
    "get_today_economic_releases": GET_TODAY_ECONOMIC_RELEASES_TOOL,
    "call_warren_buffett": CALL_WARREN_BUFFETT_TOOL,
    "get_intraday_movement_profile": GET_INTRADAY_MOVEMENT_PROFILE_TOOL,
    "research_historical_market_analog": RESEARCH_HISTORICAL_MARKET_ANALOG_TOOL,
    "get_future_forces": GET_FUTURE_FORCES_TOOL,
    "research_future_force": RESEARCH_FUTURE_FORCE_TOOL,
    "get_system_portfolios": GET_SYSTEM_PORTFOLIOS_TOOL,
    "get_market_moving_news": GET_MARKET_MOVING_NEWS_TOOL,
    "web_search": WEB_SEARCH_TOOL,
    "inspect_verifier_rules_and_rejections": INSPECT_VERIFIER_RULES_TOOL,
}


# =============================================================================
# TOOL EXECUTION
# =============================================================================


async def execute_tool(name: str, args: dict[str, Any], model_name: str = "") -> str:
    """Convenience tool execution dispatcher."""
    from core.llm.handlers.base import execute_tool as _exec

    return await _exec(name, args, model_name=model_name)
