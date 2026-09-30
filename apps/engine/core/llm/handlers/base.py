import logging
import re
import time

from core.llm import tools
from core.tool_audit import async_record_tool_audit

logger = logging.getLogger("engine.tool_audit")


def _is_valid_ticker(ticker: str) -> bool:
    """Basic validation for US stock tickers (1-5 alphanumeric characters, optionally containing a single . or -)."""
    if not ticker or not isinstance(ticker, str):
        return False
    ticker_clean = ticker.upper().strip()
    return bool(re.match(r"^[A-Z0-9.\-]{1,5}$", ticker_clean))


def _get_ticker(args: dict) -> str:
    """Extract and sanitize ticker argument, supporting 'ticker' and 'symbol' keys."""
    if not isinstance(args, dict):
        return ""
    val = args.get("ticker") or args.get("symbol") or ""
    return str(val).strip().upper()


async def execute_tool(name: str, args: dict, model_name: str, **kwargs) -> str:
    """Executes a tool with defensive parameter checking, timing audit, and error boundary.

    Args:
        name: Name of the tool to execute.
        args: Arguments dictionary for the tool.
        model_name: Name of the model initiating the tool call.
        **kwargs: Optional additional context (e.g. track_id).

    Returns:
        The tool's result as a string.
    """
    start_t = time.perf_counter()
    status = "success"
    try:
        result = await _dispatch_tool(name, args, model_name, **kwargs)
    except Exception as exc:
        status = "error"
        logger.exception("Error executing tool %s: %s", name, exc)
        result = f"Error executing {name}: {exc}"

    duration_ms = int((time.perf_counter() - start_t) * 1000)
    ticker_str = _get_ticker(args) if isinstance(args, dict) else ""
    ticker_tag = f" ({ticker_str})" if ticker_str else ""

    if duration_ms >= 5000:
        logger.warning(
            "[tool_audit] Slow tool: %s%s took %dms (%.2fs)",
            name,
            ticker_tag,
            duration_ms,
            duration_ms / 1000.0,
        )
    else:
        logger.info("[tool_audit] %s%s completed in %dms", name, ticker_tag, duration_ms)

    async_record_tool_audit(
        tool_name=name,
        tool_args=args,
        tool_result=result,
        duration_ms=duration_ms,
        model_name=model_name,
        status=status,
    )
    return result


TICKER_REQUIRED_TOOLS = {
    "get_stock_quote",
    "get_price_history",
    "get_position_pnl",
    "get_volatility_metrics",
    "get_sector_alternatives",
    "calculate_buy_quantity",
    "calculate_sell_quantity",
    "get_key_metrics",
    "get_earnings_history",
    "get_earnings_revisions",
    "audit_financial_valuation",
    "get_options_sentiment",
    "get_option_chain",
    "track_thesis_pillars",
    "get_barrier_touch_probabilities",
    "get_ticker_news",
}

TOOL_DISPATCH_TABLE = {
    "get_stock_quote": lambda ticker, args, mn, kw: tools.execute_stock_tool(ticker),
    "get_price_history": lambda ticker, args, mn, kw: tools.execute_price_history_tool(ticker, args.get("days", 7)),
    "get_position_pnl": lambda ticker, args, mn, kw: tools.execute_position_pnl_tool(ticker, owner_id=mn),
    "get_volatility_metrics": lambda ticker, args, mn, kw: tools.execute_volatility_metrics_tool(
        ticker, args.get("days", 14)
    ),
    "get_sector_alternatives": lambda ticker, args, mn, kw: tools.execute_sector_alternatives_tool(ticker),
    "calculate_buy_quantity": lambda ticker, args, mn, kw: tools.execute_buy_quantity_tool(
        ticker, owner_id=mn, percentage=args.get("percentage", 20)
    ),
    "calculate_sell_quantity": lambda ticker, args, mn, kw: tools.execute_sell_quantity_tool(
        ticker, owner_id=mn, percentage=args.get("percentage", 100)
    ),
    "search_related_tickers": lambda ticker, args, mn, kw: tools.execute_search_related_tickers_tool(args["theme"]),
    "run_stock_screener": lambda ticker, args, mn, kw: tools.execute_stock_screener_tool(**args),
    "find_uncorrelated_assets": lambda ticker, args, mn, kw: tools.execute_find_uncorrelated_assets_tool(
        max_correlation=args.get("max_correlation", 0.3),
        min_return=args.get("min_return", 0.0),
        method=args.get("method", "pearson"),
    ),
    "get_key_metrics": lambda ticker, args, mn, kw: tools.execute_key_metrics_tool(
        ticker, period=args.get("period", "annual"), limit=args.get("limit", 2)
    ),
    "get_market_health_barometer": lambda ticker, args, mn, kw: tools.execute_market_health_barometer_tool(
        limit=args.get("limit", 5)
    ),
    "get_sector_fundamentals": lambda ticker, args, mn, kw: tools.execute_sector_fundamentals_tool(
        limit=args.get("limit", 11)
    ),
    "get_earnings_history": lambda ticker, args, mn, kw: tools.execute_earnings_history_tool(
        ticker, limit=args.get("limit", 8)
    ),
    "get_pead_candidates": lambda ticker, args, mn, kw: tools.execute_pead_candidates_tool(
        sector=args.get("sector"), min_sue=args.get("min_sue", 2.0), limit=args.get("limit", 15)
    ),
    "get_earnings_revisions": lambda ticker, args, mn, kw: tools.execute_earnings_revisions_tool(ticker),
    "get_sector_bellwethers": lambda ticker, args, mn, kw: tools.execute_sector_bellwethers_tool(
        args.get("sector", "")
    ),
    "search_prediction_markets": lambda ticker, args, mn, kw: tools.execute_search_prediction_markets_tool(
        args.get("query", ""), platform=args.get("platform")
    ),
    "get_prediction_market_odds": lambda ticker, args, mn, kw: tools.execute_get_prediction_market_odds_tool(
        args.get("market_id", ""), platform=args.get("platform", "polymarket")
    ),
    "audit_financial_valuation": lambda ticker, args, mn, kw: tools.execute_financial_valuation_tool(
        ticker=ticker,
        growth_rate=args.get("growth_rate"),
        discount_rate=args.get("discount_rate"),
        terminal_growth=args.get("terminal_growth", 0.025),
    ),
    "fetch_newsletter_content": lambda ticker, args, mn, kw: tools.execute_fetch_newsletter_content_tool(
        args.get("source_ids", [])
    ),
    "search_past_memories": lambda ticker, args, mn, kw: tools.execute_search_past_memories_tool(
        args.get("query", ""), limit=args.get("limit", 5), model_name=mn
    ),
    "get_portfolio_ledger": lambda ticker, args, mn, kw: tools.execute_get_portfolio_ledger_tool(owner_id=mn),
    "get_todays_news_menu": lambda ticker, args, mn, kw: tools.execute_get_todays_news_menu_tool(),
    "get_market_feeling": lambda ticker, args, mn, kw: tools.execute_get_market_feeling_tool(),
    "get_global_macro_context": lambda ticker, args, mn, kw: tools.execute_get_global_macro_context_tool(),
    "get_volatility_index_details": lambda ticker, args, mn, kw: tools.execute_get_volatility_index_details_tool(
        args.get("lookback_days", 90)
    ),
    "get_verifier_rejections": lambda ticker, args, mn, kw: tools.execute_get_verifier_rejections_tool(
        ticker=ticker or args.get("ticker"), limit=args.get("limit", 5), model_name=mn
    ),
    "inspect_verifier_rules_and_rejections": lambda ticker, args, mn, kw: tools.execute_inspect_verifier_rules_tool(
        limit=args.get("limit", 5),
        ticker=ticker or args.get("ticker"),
        track_id=kw.get("track_id") or args.get("track_id", "track_claude"),
    ),
    "get_thematic_flows": lambda ticker, args, mn, kw: tools.execute_get_thematic_flows_tool(
        limit=args.get("limit", 5)
    ),
    "add_thematic_flow": lambda ticker, args, mn, kw: tools.execute_add_thematic_flow_tool(
        content=args.get("content", ""),
        importance_score=args.get("importance_score", 8),
        category=args.get("category"),
    ),
    "get_macro_economic_series": lambda ticker, args, mn, kw: tools.execute_macro_economic_series_tool(
        args.get("series_id_or_alias", ""),
        lookback_periods=args.get("lookback_periods", 12),
        units=args.get("units", "lin"),
        frequency=args.get("frequency"),
    ),
    "get_options_sentiment": lambda ticker, args, mn, kw: tools.execute_get_options_sentiment_tool(
        ticker=ticker, expiration_date=args.get("expiration_date")
    ),
    "get_option_chain": lambda ticker, args, mn, kw: tools.execute_get_option_chain_tool(
        ticker=ticker,
        expiration_date=args.get("expiration_date"),
        contract_type=args.get("contract_type", "all"),
        strike_range_pct=args.get("strike_range_pct", 10.0),
        min_dte=args.get("min_dte"),
        max_dte=args.get("max_dte"),
    ),
    "get_yield_curve_regime": lambda ticker, args, mn, kw: tools.execute_yield_curve_regime_tool(),
    "get_options_vol_surface": lambda ticker, args, mn, kw: tools.execute_options_vol_surface_tool(
        ticker=ticker or "SPY"
    ),
    "track_thesis_pillars": lambda ticker, args, mn, kw: tools.execute_track_thesis_pillars_tool(
        ticker=ticker,
        action=args.get("action", "get"),
        thesis_statement=args.get("thesis_statement"),
        pillars=args.get("pillars"),
        risks=args.get("risks"),
        disconfirming_factor=args.get("disconfirming_factor"),
        pillar_impacted=args.get("pillar_impacted"),
        price_target=args.get("price_target"),
        stop_loss=args.get("stop_loss"),
        conviction=args.get("conviction"),
    ),
    "get_catalyst_radar": lambda ticker, args, mn, kw: tools.execute_get_catalyst_radar_tool(
        days_ahead=args.get("days_ahead", 7),
        include_digesting=args.get("include_digesting", True),
        min_velocity=args.get("min_velocity", 1.2),
        detail=args.get("detail", False),
    ),
    "get_calendar_scenario_analysis": lambda ticker, args, mn, kw: tools.execute_get_calendar_scenario_analysis_tool(
        timeframe=args.get("timeframe", "next_week"),
        ticker=ticker or args.get("ticker"),
        min_importance=args.get("min_importance", 5),
        detail=args.get("detail", True),
        include_historical_memories=args.get("include_historical_memories", True),
    ),
    "get_barrier_touch_probabilities": lambda ticker, args, mn, kw: tools.execute_barrier_touch_probabilities_tool(
        ticker=ticker,
        target_pct=args.get("target_pct"),
        stop_pct=args.get("stop_pct"),
        horizon_bars=args.get("horizon_bars", 5),
        lookback_days=args.get("lookback_days", 252),
    ),
    "get_ticker_news": lambda ticker, args, mn, kw: tools.execute_get_ticker_news_tool(
        ticker=ticker, limit=args.get("limit", 5)
    ),
    "get_congress_trades": lambda ticker, args, mn, kw: tools.execute_get_congress_trades_tool(
        ticker=args.get("ticker") or args.get("symbol"),
        chamber=args.get("chamber"),
        days=args.get("days", 45),
        transaction_type=args.get("transaction_type"),
        limit=args.get("limit", 20),
    ),
    "analyze_thematic_beneficiaries": lambda ticker, args, mn, kw: tools.execute_analyze_thematic_beneficiaries_tool(
        anchor_ticker=args.get("anchor_ticker") or args.get("ticker", ""),
        theme=args.get("theme"),
        candidate_tickers=args.get("candidate_tickers"),
        candidate_industries=args.get("candidate_industries"),
        candidate_sectors=args.get("candidate_sectors"),
        lookback_days=args.get("lookback_days", 60),
        options_top_n=args.get("options_top_n", 3),
        include_financials=args.get("include_financials", True),
        include_institutional=args.get("include_institutional", False),
    ),
    "get_today_economic_releases": lambda ticker, args, mn, kw: tools.execute_get_today_economic_releases_tool(
        target_date=args.get("target_date"), country=args.get("country", "US")
    ),
    "call_warren_buffett": lambda ticker, args, mn, kw: tools.execute_call_warren_buffett_tool(
        ticker=args.get("ticker"), action=args.get("action"), proposed_thesis=args.get("proposed_thesis")
    ),
    "get_intraday_movement_profile": lambda ticker, args, mn, kw: tools.execute_get_intraday_movement_profile_tool(
        ticker=args.get("ticker", "SPY"),
        date=args.get("date"),
        include_hourly_tape=args.get("include_hourly_tape", True),
    ),
    "research_historical_market_analog": lambda ticker, args, mn, kw: (
        tools.execute_research_historical_market_analog_tool(
            situation=args.get("situation", ""),
            focus_assets=args.get("focus_assets"),
            horizon=args.get("horizon", "1m"),
            model_name=mn,
        )
    ),
    "get_future_forces": lambda ticker, args, mn, kw: tools.execute_get_future_forces_tool(
        archetype=args.get("archetype"),
        max_horizon_months=args.get("max_horizon_months", 24),
        limit=args.get("limit", 5),
    ),
    "research_future_force": lambda ticker, args, mn, kw: tools.execute_research_future_force_tool(
        force_title=args.get("force_title", ""),
        archetype=args.get("archetype", "secular_tollroad"),
        thesis=args.get("thesis", ""),
        catalyst_event=args.get("catalyst_event", ""),
        invalidation_triggers=args.get("invalidation_triggers", ""),
        transmission_mechanism=args.get("transmission_mechanism", ""),
        tickers=args.get("tickers"),
        horizon_months=args.get("horizon_months", 3),
        model_name=mn,
    ),
    "get_system_portfolios": lambda ticker, args, mn, kw: tools.execute_get_system_portfolios_tool(
        category=args.get("category", "all"),
        include_positions=args.get("include_positions", True),
        lookback_days=args.get("lookback_days", 7),
    ),
    "web_search": lambda ticker, args, mn, kw: tools.execute_web_search_tool(args.get("query", "")),
}


async def _dispatch_tool(name: str, args: dict, model_name: str, **kwargs) -> str:
    """Dispatches tool execution to the correct tool implementation."""
    ticker = _get_ticker(args)
    if ticker and not _is_valid_ticker(ticker):
        return (
            f"Error: '{ticker}' is not a valid stock ticker. "
            "Tickers must be 1 to 5 alphanumeric characters (A-Z, 0-9) and can optionally contain a single period or hyphen."
        )

    if name in TICKER_REQUIRED_TOOLS and not ticker:
        return f"Error: Missing required 'ticker' argument for {name}."

    handler = TOOL_DISPATCH_TABLE.get(name)
    if handler is None:
        return "Unknown tool"

    return await handler(ticker, args, model_name, kwargs)
