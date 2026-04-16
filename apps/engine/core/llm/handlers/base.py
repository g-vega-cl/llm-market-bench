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
        return await tools.execute_price_history_tool(
            args["ticker"], 
            args.get("days", 7)
        )
    elif name == "get_position_pnl":
        return await tools.execute_position_pnl_tool(
            args["ticker"], 
            owner_id=model_name
        )
    elif name == "get_volatility_metrics":
        return await tools.execute_volatility_metrics_tool(
            args["ticker"],
            args.get("days", 14)
        )
    elif name == "get_sector_alternatives":
        return await tools.execute_sector_alternatives_tool(args["ticker"])
    elif name == "calculate_buy_quantity":
        return await tools.execute_buy_quantity_tool(
            args["ticker"], 
            owner_id=model_name,
            percentage=args["percentage"]
        )
    elif name == "calculate_sell_quantity":
        return await tools.execute_sell_quantity_tool(
            args["ticker"], 
            owner_id=model_name,
            percentage=args["percentage"]
        )
    elif name == "search_related_tickers":
        return await tools.execute_search_related_tickers_tool(args["theme"])
    elif name == "run_stock_screener":
        return await tools.execute_stock_screener_tool(**args)
    elif name == "find_uncorrelated_assets":
        return await tools.execute_find_uncorrelated_assets_tool(
            max_correlation=args.get("max_correlation", 0.3),
            min_return=args.get("min_return", 0.0),
            method=args.get("method", "pearson")
        )
    return "Unknown tool"
