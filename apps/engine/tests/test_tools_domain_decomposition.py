"""TDD contract test verifying the decomposition of core.llm.tools into domain modules."""

from unittest.mock import AsyncMock, patch

import pytest


def test_domain_modules_exist_and_export_handlers():
    """Verify each domain module exists and exports expected tool handler functions."""
    from tools import (
        analyst_personas,
        compliance,
        macro,
        market_data,
        news_memories,
        portfolio,
        prediction_markets,
        technicals_options,
        valuation,
    )

    # 1. Prediction markets
    assert hasattr(prediction_markets, "execute_search_prediction_markets_tool")
    assert hasattr(prediction_markets, "execute_get_prediction_market_odds_tool")

    # 2. Market data
    assert hasattr(market_data, "execute_stock_tool")
    assert hasattr(market_data, "execute_price_history_tool")
    assert hasattr(market_data, "execute_get_intraday_movement_profile_tool")
    assert hasattr(market_data, "execute_get_ticker_news_tool")

    # 3. Portfolio
    assert hasattr(portfolio, "execute_get_portfolio_ledger_tool")
    assert hasattr(portfolio, "execute_position_pnl_tool")
    assert hasattr(portfolio, "execute_buy_quantity_tool")
    assert hasattr(portfolio, "execute_sell_quantity_tool")
    assert hasattr(portfolio, "execute_get_system_portfolios_tool")

    # 4. Technicals & options
    assert hasattr(technicals_options, "execute_volatility_metrics_tool")
    assert hasattr(technicals_options, "compute_volume_context")
    assert hasattr(technicals_options, "execute_stock_screener_tool")
    assert hasattr(technicals_options, "execute_find_uncorrelated_assets_tool")
    assert hasattr(technicals_options, "execute_get_options_sentiment_tool")
    assert hasattr(technicals_options, "execute_get_macro_options_sentiment_tool")
    assert hasattr(technicals_options, "execute_get_option_chain_tool")
    assert hasattr(technicals_options, "execute_options_vol_surface_tool")
    assert hasattr(technicals_options, "execute_barrier_touch_probabilities_tool")

    # 5. Macro
    assert hasattr(macro, "execute_get_global_macro_context_tool")
    assert hasattr(macro, "execute_get_volatility_index_details_tool")
    assert hasattr(macro, "execute_macro_economic_series_tool")
    assert hasattr(macro, "execute_yield_curve_regime_tool")
    assert hasattr(macro, "execute_get_today_economic_releases_tool")

    # 6. Valuation
    assert hasattr(valuation, "execute_key_metrics_tool")
    assert hasattr(valuation, "execute_market_health_barometer_tool")
    assert hasattr(valuation, "execute_sector_fundamentals_tool")
    assert hasattr(valuation, "execute_financial_valuation_tool")
    assert hasattr(valuation, "execute_sector_alternatives_tool")
    assert hasattr(valuation, "execute_search_related_tickers_tool")

    # 7. News & memories
    assert hasattr(news_memories, "execute_get_todays_news_menu_tool")
    assert hasattr(news_memories, "execute_get_market_feeling_tool")
    assert hasattr(news_memories, "execute_fetch_daily_newsletter_tool")
    assert hasattr(news_memories, "execute_fetch_newsletter_content_tool")
    assert hasattr(news_memories, "execute_search_past_memories_tool")
    assert hasattr(news_memories, "execute_web_search_tool")

    # 8. Analyst personas & thematic forces
    assert hasattr(analyst_personas, "execute_call_warren_buffett_tool")
    assert hasattr(analyst_personas, "execute_research_historical_market_analog_tool")
    assert hasattr(analyst_personas, "execute_get_future_forces_tool")
    assert hasattr(analyst_personas, "execute_research_future_force_tool")
    assert hasattr(analyst_personas, "execute_analyze_thematic_beneficiaries_tool")
    assert hasattr(analyst_personas, "execute_get_thematic_flows_tool")
    assert hasattr(analyst_personas, "execute_add_thematic_flow_tool")

    # 9. Compliance & verification
    assert hasattr(compliance, "execute_get_verifier_rejections_tool")
    assert hasattr(compliance, "execute_inspect_verifier_rules_tool")
    assert hasattr(compliance, "execute_get_catalyst_radar_tool")
    assert hasattr(compliance, "execute_get_calendar_scenario_analysis_tool")


def test_core_llm_tools_barrel_parity():
    """Verify core.llm.tools re-exports all domain tool handlers for backward compatibility."""
    from core.llm import tools

    expected_handlers = [
        "execute_stock_tool",
        "execute_price_history_tool",
        "execute_position_pnl_tool",
        "execute_volatility_metrics_tool",
        "compute_volume_context",
        "execute_stock_screener_tool",
        "execute_sector_alternatives_tool",
        "execute_buy_quantity_tool",
        "execute_sell_quantity_tool",
        "execute_search_related_tickers_tool",
        "execute_find_uncorrelated_assets_tool",
        "execute_key_metrics_tool",
        "execute_market_health_barometer_tool",
        "execute_sector_fundamentals_tool",
        "execute_earnings_history_tool",
        "execute_pead_candidates_tool",
        "execute_earnings_revisions_tool",
        "execute_sector_bellwethers_tool",
        "execute_search_prediction_markets_tool",
        "execute_get_prediction_market_odds_tool",
        "execute_financial_valuation_tool",
        "execute_fetch_daily_newsletter_tool",
        "execute_fetch_newsletter_content_tool",
        "execute_search_past_memories_tool",
        "execute_get_thematic_flows_tool",
        "execute_add_thematic_flow_tool",
        "execute_get_portfolio_ledger_tool",
        "execute_get_todays_news_menu_tool",
        "execute_get_market_feeling_tool",
        "execute_get_global_macro_context_tool",
        "execute_get_volatility_index_details_tool",
        "execute_get_verifier_rejections_tool",
        "execute_inspect_verifier_rules_tool",
        "execute_web_search_tool",
        "execute_macro_economic_series_tool",
        "execute_get_options_sentiment_tool",
        "execute_get_macro_options_sentiment_tool",
        "execute_get_option_chain_tool",
        "execute_yield_curve_regime_tool",
        "execute_options_vol_surface_tool",
        "execute_track_thesis_pillars_tool",
        "execute_get_catalyst_radar_tool",
        "execute_get_calendar_scenario_analysis_tool",
        "execute_barrier_touch_probabilities_tool",
        "execute_get_ticker_news_tool",
        "execute_get_congress_trades_tool",
        "execute_analyze_thematic_beneficiaries_tool",
        "execute_get_today_economic_releases_tool",
        "execute_call_warren_buffett_tool",
        "execute_get_intraday_movement_profile_tool",
        "execute_research_historical_market_analog_tool",
        "execute_get_future_forces_tool",
        "execute_research_future_force_tool",
        "execute_get_system_portfolios_tool",
    ]

    for handler_name in expected_handlers:
        assert hasattr(tools, handler_name), f"Barrel core.llm.tools missing {handler_name}"


@pytest.mark.asyncio
async def test_barrel_patch_interception():
    """Verify patching core.llm.tools intercepts dispatch via handlers.base.execute_tool."""
    from core.llm.handlers import base

    with patch("core.llm.tools.execute_stock_tool", new_callable=AsyncMock) as mock_stock:
        mock_stock.return_value = "Intercepted quote AAPL"
        result = await base.execute_tool("get_stock_quote", {"ticker": "AAPL"}, model_name="test-model")
        assert result == "Intercepted quote AAPL"
        mock_stock.assert_awaited_once_with("AAPL")
