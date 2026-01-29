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
    client = get_supabase_client()
    try:
        ticker = ticker.upper()
        # Query price_history for the ticker
        res = client.table("price_history") \
            .select("price, fetched_at") \
            .eq("ticker", ticker) \
            .order("fetched_at", desc=True) \
            .limit(days * 2) \
            .execute()
        
        if not res.data:
            return f"No historical price data found for {ticker}."
        
        history_str = f"Historical Price Data for {ticker} (Recent first):\n"
        for entry in res.data:
            history_str += f"- {entry['fetched_at']}: ${float(entry['price']):.2f}\n"
        
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
