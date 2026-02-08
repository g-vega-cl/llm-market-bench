"""Tool definitions and execution logic for LLMs."""

from execution.market_data import MarketDataManager
from core.db import get_supabase_client

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

# --- Gemini Tool Definitions (Google GenAI SDK) ---
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
