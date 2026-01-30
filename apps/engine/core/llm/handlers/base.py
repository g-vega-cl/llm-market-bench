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
    return "Unknown tool"
