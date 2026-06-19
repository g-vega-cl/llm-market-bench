"""Base logic for tool execution in LLM handlers."""

from core.llm import tools


async def execute_tool(name: str, args: dict, model_name: str) -> str:
    """Dispatches tool execution to the correct tool implementation.

    Args:
        name: Name of the tool to execute.
        args: Arguments dictionary for the tool.
        model_name: Name of the model (used as owner_id for some tools).

    Returns:
        The tool's result as a string.
    """
    if name == "get_stock_quote":
        return await tools.execute_stock_tool(args["ticker"])
    elif name == "get_price_history":
        return await tools.execute_price_history_tool(args["ticker"], args.get("days", 7))
    elif name == "get_position_pnl":
        return await tools.execute_position_pnl_tool(args["ticker"], owner_id=model_name)
    elif name == "get_volatility_metrics":
        return await tools.execute_volatility_metrics_tool(args["ticker"], args.get("days", 14))
    elif name == "get_sector_alternatives":
        return await tools.execute_sector_alternatives_tool(args["ticker"])
    elif name == "calculate_buy_quantity":
        return await tools.execute_buy_quantity_tool(args["ticker"], owner_id=model_name, percentage=args["percentage"])
    elif name == "calculate_sell_quantity":
        return await tools.execute_sell_quantity_tool(
            args["ticker"], owner_id=model_name, percentage=args["percentage"]
        )
    elif name == "search_related_tickers":
        return await tools.execute_search_related_tickers_tool(args["theme"])
    elif name == "run_stock_screener":
        return await tools.execute_stock_screener_tool(**args)
    elif name == "find_uncorrelated_assets":
        return await tools.execute_find_uncorrelated_assets_tool(
            max_correlation=args.get("max_correlation", 0.3),
            min_return=args.get("min_return", 0.0),
            method=args.get("method", "pearson"),
        )
    elif name == "get_key_metrics":
        return await tools.execute_key_metrics_tool(
            args["ticker"],
            period=args.get("period", "annual"),
            limit=args.get("limit", 2),
        )
    elif name == "get_market_health_barometer":
        return await tools.execute_market_health_barometer_tool(
            limit=args.get("limit", 5),
        )
    elif name == "get_earnings_history":
        return await tools.execute_earnings_history_tool(
            args["ticker"],
            limit=args.get("limit", 8),
        )
    elif name == "search_prediction_markets":
        return await tools.execute_search_prediction_markets_tool(
            args["query"],
            platform=args.get("platform"),
        )
    elif name == "get_prediction_market_odds":
        return await tools.execute_get_prediction_market_odds_tool(
            args["market_id"],
            platform=args["platform"],
        )
    elif name == "audit_financial_valuation":
        return await tools.execute_financial_valuation_tool(
            ticker=args["ticker"],
            growth_rate=args.get("growth_rate"),
            discount_rate=args.get("discount_rate"),
            terminal_growth=args.get("terminal_growth", 0.025),
        )
    return "Unknown tool"
