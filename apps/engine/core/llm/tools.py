"""Tool definitions and execution logic for LLMs."""

import httpx
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

SELL_10_PERCENT_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "sell_10_percent",
        "description": "Calculate how many shares equal 10% of your current position for a ticker. Use this when you want to take small profits or reduce exposure.",
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

SELL_25_PERCENT_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "sell_25_percent",
        "description": "Calculate how many shares equal 25% of your current position for a ticker. Use this when you want to take profits or reduce exposure.",
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

SELL_33_PERCENT_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "sell_33_percent",
        "description": "Calculate how many shares equal 33% (one third) of your current position for a ticker.",
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

SELL_50_PERCENT_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "sell_50_percent",
        "description": "Calculate how many shares equal 50% of your current position for a ticker. Use this when you want to rebalance or significantly reduce exposure.",
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

SELL_75_PERCENT_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "sell_75_percent",
        "description": "Calculate how many shares equal 75% of your current position for a ticker. Use this when you want to exit most of your position.",
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

SELL_100_PERCENT_TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "sell_100_percent",
        "description": "Calculate exactly how many shares you currently own for a ticker to exit the position completely.",
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



SELL_10_PERCENT_TOOL_DEFINITION_ANTHROPIC = {
    "name": "sell_10_percent",
    "description": "Calculate how many shares equal 10% of your current position for a ticker. Use this when you want to take small profits or reduce exposure.",
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

SELL_25_PERCENT_TOOL_DEFINITION_ANTHROPIC = {
    "name": "sell_25_percent",
    "description": "Calculate how many shares equal 25% of your current position for a ticker. Use this when you want to take profits or reduce exposure.",
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

SELL_33_PERCENT_TOOL_DEFINITION_ANTHROPIC = {
    "name": "sell_33_percent",
    "description": "Calculate how many shares equal 33% (one third) of your current position for a ticker.",
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

SELL_50_PERCENT_TOOL_DEFINITION_ANTHROPIC = {
    "name": "sell_50_percent",
    "description": "Calculate how many shares equal 50% of your current position for a ticker. Use this when you want to rebalance or significantly reduce exposure.",
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

SELL_75_PERCENT_TOOL_DEFINITION_ANTHROPIC = {
    "name": "sell_75_percent",
    "description": "Calculate how many shares equal 75% of your current position for a ticker. Use this when you want to exit most of your position.",
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

SELL_100_PERCENT_TOOL_DEFINITION_ANTHROPIC = {
    "name": "sell_100_percent",
    "description": "Calculate exactly how many shares you currently own for a ticker to exit the position completely.",
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


SEARCH_RELATED_TICKERS_TOOL_DEFINITION_GEMINI = {
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
}

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

SELL_10_PERCENT_TOOL_DEFINITION_GEMINI = {
    "name": "sell_10_percent",
    "description": "Calculate how many shares equal 10% of your current position for a ticker. Use this when you want to take small profits or reduce exposure.",
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

SELL_25_PERCENT_TOOL_DEFINITION_GEMINI = {
    "name": "sell_25_percent",
    "description": "Calculate how many shares equal 25% of your current position for a ticker. Use this when you want to take profits or reduce exposure.",
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

SELL_33_PERCENT_TOOL_DEFINITION_GEMINI = {
    "name": "sell_33_percent",
    "description": "Calculate how many shares equal 33% (one third) of your current position for a ticker.",
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

SELL_50_PERCENT_TOOL_DEFINITION_GEMINI = {
    "name": "sell_50_percent",
    "description": "Calculate how many shares equal 50% of your current position for a ticker. Use this when you want to rebalance or significantly reduce exposure.",
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

SELL_75_PERCENT_TOOL_DEFINITION_GEMINI = {
    "name": "sell_75_percent",
    "description": "Calculate how many shares equal 75% of your current position for a ticker. Use this when you want to exit most of your position.",
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

SELL_100_PERCENT_TOOL_DEFINITION_GEMINI = {
    "name": "sell_100_percent",
    "description": "Calculate exactly how many shares you currently own for a ticker to exit the position completely.",
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

async def _execute_sell_percentage_tool(ticker: str, owner_id: str, percentage: float) -> str:
    """Helper to calculate sell quantity for a given percentage of a position."""
    client = get_supabase_client()
    try:
        ticker = ticker.upper()
        res = client.table("position_pnl") \
            .select("quantity") \
            .eq("ticker", ticker) \
            .eq("owner_id", owner_id) \
            .execute()
        
        if not res.data:
            return f"Error: You do not currently own a position in {ticker}. You cannot sell it."
        
        total_quantity = res.data[0]['quantity']
        if total_quantity <= 0:
            return f"Error: Your position in {ticker} is zero. You cannot sell it."
            
        sell_quantity = int(total_quantity * percentage)
        
        # Ensure we sell at least 1 share if percentage > 0 and position exists
        if sell_quantity == 0 and percentage > 0:
            sell_quantity = 1
            
        # Ensure we don't sell more than we have
        sell_quantity = min(sell_quantity, total_quantity)
        
        pct_label = f"{int(percentage * 100)}%"
        return (
            f"CALCULATION COMPLETE for {ticker}:\n"
            f"- Current Holdings: {total_quantity} shares\n"
            f"- Recommended SELL Quantity ({pct_label}): {sell_quantity} shares\n"
            f"MANDATORY ACTION: Set your decision to 'SELL' for ticker '{ticker}' with quantity: {sell_quantity}. "
            f"You MUST include 'sell_tool_called': true in your final JSON decision."
        )
    except Exception as e:
        return f"Error calculating sell quantity for {ticker}: {str(e)}"

async def execute_sell_10_percent_tool(ticker: str, owner_id: str) -> str:
    return await _execute_sell_percentage_tool(ticker, owner_id, 0.10)

async def execute_sell_25_percent_tool(ticker: str, owner_id: str) -> str:
    return await _execute_sell_percentage_tool(ticker, owner_id, 0.25)

async def execute_sell_33_percent_tool(ticker: str, owner_id: str) -> str:
    return await _execute_sell_percentage_tool(ticker, owner_id, 0.33)

async def execute_sell_50_percent_tool(ticker: str, owner_id: str) -> str:
    return await _execute_sell_percentage_tool(ticker, owner_id, 0.50)

async def execute_sell_75_percent_tool(ticker: str, owner_id: str) -> str:
    return await _execute_sell_percentage_tool(ticker, owner_id, 0.75)

async def execute_sell_100_percent_tool(ticker: str, owner_id: str) -> str:
    return await _execute_sell_percentage_tool(ticker, owner_id, 1.0)


async def execute_search_related_tickers_tool(theme: str) -> str:
    """Uses LLM to search for tickers related to a theme."""
    from core.llm import get_gemini_client, prompts
    from core.config import GEMINI_MODEL
    from core.models import TickerSuggestion
    
    client = get_gemini_client()
    try:
        prompt = prompts.TICKER_SUGGESTION_PROMPT.format(event_summary=theme)
        resp = client.chat.completions.create(
            model=GEMINI_MODEL,
            response_model=TickerSuggestion,
            messages=[{"role": "user", "content": prompt}]
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
