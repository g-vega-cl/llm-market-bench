"""LLM package for multi-provider analysis and event synthesis."""

from core.llm import analysis, clients, events, minimax, prompts, tools
from execution.market_data import MarketDataManager

# Primary functions
analyze_with_provider = analysis.analyze_with_provider
synthesize_event = events.synthesize_event
analyze_event_relationship = events.analyze_event_relationship

# Client functions
get_openai_client = clients.get_openai_client
get_anthropic_client = clients.get_anthropic_client
get_deepseek_client = clients.get_deepseek_client
get_gemini_client = clients.get_gemini_client
_close_client = clients.close_client

# MiniMax client
MiniMaxClient = minimax.MiniMaxClient

# Constants and definitions
_CLIENT_FACTORIES = clients.CLIENT_FACTORIES
execute_stock_tool = tools.execute_stock_tool
execute_search_prediction_markets_tool = tools.execute_search_prediction_markets_tool
execute_get_prediction_market_odds_tool = tools.execute_get_prediction_market_odds_tool

__all__ = [
    "analysis",
    "clients",
    "events",
    "minimax",
    "prompts",
    "tools",
    "analyze_with_provider",
    "synthesize_event",
    "analyze_event_relationship",
    "get_openai_client",
    "get_anthropic_client",
    "get_deepseek_client",
    "get_gemini_client",
    "_close_client",
    "MiniMaxClient",
    "_CLIENT_FACTORIES",
    "execute_stock_tool",
    "execute_search_prediction_markets_tool",
    "execute_get_prediction_market_odds_tool",
    "MarketDataManager",
]
