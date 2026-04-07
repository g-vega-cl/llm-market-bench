"""Tool definitions and execution logic for LLMs."""

import httpx
from typing import Optional
from execution.market_data import MarketDataManager
from core.db import get_supabase_client

# =============================================================================
# WEB SEARCH TOOL DEFINITIONS
# =============================================================================

# OpenAI does not support native web search as a function tool.
# Web search is enabled via the 'web_search' tool in the tools array,
# not as a function call. See handlers/openai.py for implementation.

# Anthropic Web Search Tool (basic version - ZDR eligible)
WEB_SEARCH_TOOL_DEFINITION_ANTHROPIC = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,  # Limit searches per request
}

# Anthropic Web Search Tool with dynamic filtering (Opus 4.6 / Sonnet 4.6 only)
# Not ZDR eligible by default
WEB_SEARCH_TOOL_DYNAMIC_ANTHROPIC = {
    "type": "web_search_20260209",
    "name": "web_search",
}

# Gemini Google Search Tool
GEMINI_GOOGLE_SEARCH_TOOL = {
    "name": "google_search",
    "googleSearch": {},
}

# =============================================================================
# EXISTING TOOL DEFINITIONS
# =============================================================================

SEARCH_RELATED_TICKERS_TOOL_DEFINITION_OPENAI = {
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
                }
            },
            "required": ["theme"],
        },
    },
}

STOCK_TOOL_DEFINITION_OPENAI = {
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
                }
            },
            "required": ["ticker"],
        },
    },
}

SEARCH_RELATED_TICKERS_TOOL_DEFINITION_ANTHROPIC = {
    "name": "search_related_tickers",
    "description": (
        "Given a market theme or event, identify relevant stock tickers or ETFs "
        "that would be most impacted."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "theme": {
                "type": "string",
                "description": "The market theme, concept, or event (e.g., 'Private Credit', 'AI demand surge').",
            }
        },
        "required": ["theme"],
    },
}

STOCK_TOOL_DEFINITION_ANTHROPIC = {
    "name": "get_stock_quote",
    "description": (
        "Get real-time price and market cap for a stock ticker to verify "
        "its existence and liquidity."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol (e.g., AAPL, TSLA, NVDA)",
            }
        },
        "required": ["ticker"],
    },
}

PRICE_HISTORY_TOOL_DEFINITION_OPENAI = {
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
                }
            },
            "required": ["ticker"],
        },
    },
}

PRICE_HISTORY_TOOL_DEFINITION_ANTHROPIC = {
    "name": "get_price_history",
    "description": "Get historical price data for a stock ticker to see if news is priced in.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol.",
            },
            "days": {
                "type": "integer",
                "description": "Number of days of history to retrieve (default 7).",
            }
        },
        "required": ["ticker"],
    },
}

POSITION_PNL_TOOL_DEFINITION_OPENAI = {
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
                }
            },
            "required": ["ticker"],
        },
    },
}

POSITION_PNL_TOOL_DEFINITION_ANTHROPIC = {
    "name": "get_position_pnl",
    "description": "Get current unrealized P&L and cost basis for a stock you already own.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol.",
            }
        },
        "required": ["ticker"],
    },
}

VOLATILITY_METRICS_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "get_volatility_metrics",
        "description": "Calculate price standard deviation and range to assess if a stock is over-extended.",
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
                }
            },
            "required": ["ticker"],
        },
    },
}

VOLATILITY_METRICS_TOOL_DEFINITION_ANTHROPIC = {
    "name": "get_volatility_metrics",
    "description": "Calculate price standard deviation and range to assess if a stock is over-extended.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol.",
            },
            "days": {
                "type": "integer",
                "description": "Number of days of history to retrieve (default 14).",
            }
        },
        "required": ["ticker"],
    },
}

SECTOR_ALTERNATIVES_TOOL_DEFINITION_OPENAI = {
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
                }
            },
            "required": ["ticker"],
        },
    },
}

SECTOR_ALTERNATIVES_TOOL_DEFINITION_ANTHROPIC = {
    "name": "get_sector_alternatives",
    "description": "Identify correlated stocks or competitors in the same sector to find less crowded plays.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol.",
            }
        },
        "required": ["ticker"],
    },
}

RUN_STOCK_SCREENER_TOOL_DEFINITION_OPENAI = {
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
                "limit": {"type": "integer", "description": "Maximum number of results (default 10, max 15)."}
            }
        },
    },
}

RUN_STOCK_SCREENER_TOOL_DEFINITION_ANTHROPIC = {
    "name": "run_stock_screener",
    "description": (
        "Screen for stocks using various financial filters. Use this to identify "
        "investable assets when you have a market theme but no specific tickers."
    ),
    "input_schema": {
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
            "limit": {"type": "integer", "description": "Maximum number of results (default 10, max 15)."}
        }
    },
}

# =============================================================================
# CONSOLIDATED QUANTITY CALCULATION TOOLS
# =============================================================================

CALCULATE_BUY_QUANTITY_TOOL_DEFINITION_OPENAI = {
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
                    "maximum": 100
                }
            },
            "required": ["ticker", "percentage"],
        },
    },
}

CALCULATE_SELL_QUANTITY_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "calculate_sell_quantity",
        "description": (
            "Calculate how many shares to SELL based on a percentage of your current "
            "position (1-100%). If the remaining balance would fall below 10% of "
            "total equity, it will recommend a 100% (FULL) sell to avoid dust positions."
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
                    "maximum": 100
                }
            },
            "required": ["ticker", "percentage"],
        },
    },
}

CALCULATE_BUY_QUANTITY_TOOL_DEFINITION_ANTHROPIC = {
    "name": "calculate_buy_quantity",
    "description": (
        "Calculate how many shares to BUY based on a percentage of your available "
        "buying power (1-100%). This tool automatically enforces the mandatory "
        "10% total equity minimum position size."
    ),
    "input_schema": {
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
                "maximum": 100
            }
        },
        "required": ["ticker", "percentage"],
    },
}

CALCULATE_SELL_QUANTITY_TOOL_DEFINITION_ANTHROPIC = {
    "name": "calculate_sell_quantity",
    "description": (
        "Calculate how many shares to SELL based on a percentage of your current "
        "position (1-100%). If the remaining balance would fall below 10% of "
        "total equity, it will recommend a 100% (FULL) sell to avoid dust positions."
    ),
    "input_schema": {
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
                "maximum": 100
            }
        },
        "required": ["ticker", "percentage"],
    },
}

# =============================================================================
# GEMINI TOOL DEFINITIONS (for core market data tools)
# =============================================================================

STOCK_TOOL_DEFINITION_GEMINI = {
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
            }
        },
        "required": ["ticker"],
    },
}

PRICE_HISTORY_TOOL_DEFINITION_GEMINI = {
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
            }
        },
        "required": ["ticker"],
    },
}

POSITION_PNL_TOOL_DEFINITION_GEMINI = {
    "name": "get_position_pnl",
    "description": "Get current unrealized P&L and cost basis for a stock you already own.",
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol.",
            }
        },
        "required": ["ticker"],
    },
}

VOLATILITY_METRICS_TOOL_DEFINITION_GEMINI = {
    "name": "get_volatility_metrics",
    "description": "Calculate price standard deviation and range to assess if a stock is over-extended.",
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
            }
        },
        "required": ["ticker"],
    },
}

SECTOR_ALTERNATIVES_TOOL_DEFINITION_GEMINI = {
    "name": "get_sector_alternatives",
    "description": "Identify correlated stocks or competitors in the same sector to find less crowded plays.",
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol.",
            }
        },
        "required": ["ticker"],
    },
}

CALCULATE_BUY_QUANTITY_TOOL_DEFINITION_GEMINI = {
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
            }
        },
        "required": ["ticker", "percentage"],
    },
}

CALCULATE_SELL_QUANTITY_TOOL_DEFINITION_GEMINI = {
    "name": "calculate_sell_quantity",
    "description": (
        "Calculate how many shares to SELL based on a percentage of your current "
        "position (1-100%). If the remaining balance would fall below 10% of "
        "total equity, it will recommend a 100% (FULL) sell to avoid dust positions."
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
            }
        },
        "required": ["ticker", "percentage"],
    },
}

RUN_STOCK_SCREENER_TOOL_DEFINITION_GEMINI = {
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
            "sector": {"type": "string", "description": "Filter by sector (e.g., 'Technology', 'Healthcare')."},
            "industry": {"type": "string", "description": "Filter by specific industry."},
            "exchange": {"type": "string", "description": "Filter by exchange (default: 'NYSE,NASDAQ')."},
            "limit": {"type": "integer", "description": "Maximum number of results (max 15)."}
        }
    },
}



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
    """Calculates volatility metrics for a ticker."""
    manager = MarketDataManager()
    try:
        data = await manager.get_history(ticker, days)
        
        if not data or len(data) < 2:
            return f"Insufficient historical data for {ticker} to calculate volatility."
        
        # Data is latest first
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
            f"- Distance from Mean: {((curr - avg) / stdev):.2f} standard deviations"
        )
    except Exception as e:
        return f"Error calculating volatility for {ticker}: {str(e)}"


async def execute_stock_screener_tool(
    market_cap_more_than: Optional[float] = None,
    market_cap_lower_than: Optional[float] = None,
    price_more_than: Optional[float] = None,
    price_lower_than: Optional[float] = None,
    beta_more_than: Optional[float] = None,
    beta_lower_than: Optional[float] = None,
    volume_more_than: Optional[float] = None,
    volume_lower_than: Optional[float] = None,
    dividend_more_than: Optional[float] = None,
    dividend_lower_than: Optional[float] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    exchange: Optional[str] = "NYSE,NASDAQ",
    limit: int = 10,
    is_actively_trading: bool = True
) -> str:
    """Executes the stock screener tool and returns a formatted list of candidates."""
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

        output = f"Stock Screening Results (Top {len(results)}):\n"
        for item in results:
            output += (
                f"- ${item.get('symbol')} ({item.get('companyName')}): "
                f"Price: ${item.get('price', 0):.2f}, "
                f"Market Cap: ${item.get('marketCap', 0) / 1e9:.2f}B, "
                f"Sector: {item.get('sector')}\n"
            )
        
        return output
    except Exception as e:
        return f"Error executing stock screener: {str(e)}"

from memory.embeddings import get_embedding

# ... (rest of imports)

async def execute_sector_alternatives_tool(ticker: str) -> str:
    """Identifies sector alternatives for a ticker using vector search on past decisions."""
    client = get_supabase_client()
    try:
        ticker = ticker.upper()
        
        # 1. Generate an embedding for the sector context
        # We frame the query to find decisions about similar companies/sectors
        query_text = f"Market analysis and trading decision for {ticker} stock in this sector"
        embedding = get_embedding(query_text)
        
        if not embedding:
             return f"Could not generate embedding for {ticker} to find alternatives."

        # 2. Find conceptually similar past decisions
        # This helps us find tickers that appear in similar decision contexts (sectors)
        res = client.rpc(
            "match_decisions",
            {
                "query_embedding": embedding,
                "match_threshold": 0.5, # Moderate threshold to capture sector peers
                "match_count": 10,
            }
        ).execute()
        
        # 3. Extract unique tickers, excluding the target ticker
        related_tickers = set()
        if res.data:
            for item in res.data:
                t = item.get("ticker")
                if t and t != ticker:
                    related_tickers.add(t)
        
        # 4. Fallback if vector search yields nothing (e.g. cold start or only self-matches)
        if not related_tickers:
             # Try simple text search in memories as fallback
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
        
        # 1. Fetch current prices for all held positions to get accurate equity
        current_prices = {t: p.average_cost_basis for t, p in portfolio.positions.items()}
        current_prices[ticker] = price
        
        metrics = portfolio.calculate_reg_t_metrics(current_prices)
        
        # 2. Calculate Floor (10% of total equity)
        equity_floor_usd = metrics.total_equity * 0.10
        
        # 3. Calculate target value based on requested percentage of buying power
        target_value_usd = metrics.buying_power * (percentage / 100.0)
        
        # 4. Enforce Floor: Every trade must be >= Floor
        final_target_usd = target_value_usd
        compliance_note = ""
        
        if target_value_usd < equity_floor_usd:
            final_target_usd = equity_floor_usd
            compliance_note = (
                f"\nNOTE: Your requested {percentage}% allocation (${target_value_usd:,.2f}) was below the "
                f"10% Total Equity Floor (${equity_floor_usd:,.2f}). This tool has automatically "
                f"upsized your request to meet the minimum required position size."
            )
            
        # 5. Cap at available Buying Power
        if final_target_usd > metrics.buying_power:
             final_target_usd = metrics.buying_power
             compliance_note += f"\nWARNING: Insufficient Buying Power to meet the preferred allocation. Capped at ${metrics.buying_power:,.2f}."

        quantity = int(final_target_usd / price)
        
        if quantity == 0 and final_target_usd > 0:
             quantity = 1 # Buy at least 1 share if we have any BP

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
    
    manager = MarketDataManager()
    
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
        
        # Fetch equity context
        current_prices = {t: p.average_cost_basis for t, p in portfolio.positions.items()}
        current_prices[ticker] = price
        metrics = portfolio.calculate_reg_t_metrics(current_prices)
        equity_floor_usd = metrics.total_equity * 0.10
        
        # 1. Calculate requested sell
        sell_shares = int(total_shares * (percentage / 100.0))
        remaining_shares = total_shares - sell_shares
        remaining_value = remaining_shares * price
        
        # 2. Enforce Dust Rule: If remaining value < 10% equity, sell ALL
        compliance_note = ""
        if remaining_shares > 0 and remaining_value < equity_floor_usd:
             sell_shares = total_shares
             remaining_shares = 0
             compliance_note = (
                 f"\nWARNING: Selling {percentage}% would leave a position worth ${remaining_value:,.2f}, "
                 f"which is below your 10% Equity Floor (${equity_floor_usd:,.2f}). "
                 f"To prevent 'dust' positions, this tool has mandated a 100% (FULL) sell."
             )
        
        # Ensure we sell at least 1 share if percentage > 0
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


# Remove old sell helpers


async def execute_search_related_tickers_tool(theme: str) -> str:
    """Uses LLM to search for tickers related to a theme."""
    from core.llm.prompt_factory import PromptFactory
    from core.config import GEMINI_MODEL
    from core.models import TickerSuggestion
    
    client = get_gemini_client()
    try:
        # Use centralized PromptFactory for ticker suggestions
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


# =============================================================================
# WEB SEARCH EXECUTION
# =============================================================================

async def execute_web_search_tool(query: str) -> str:
    """Executes a web search and returns formatted results.
    
    This is a fallback implementation for providers that don't have native
    web search tool support. For Anthropic and Gemini, use their native
    web search tools instead.
    
    Args:
        query: The search query string.
        
    Returns:
        Formatted search results or error message.
    """
    # This function is a fallback - native providers use their own search
    return "Web search is handled natively by your provider. Use the web_search tool directly."
