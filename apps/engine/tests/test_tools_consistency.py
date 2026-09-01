"""Drift prevention tests ensuring parity across shared tools.json, engine schemas, and prompt specs."""

import json
from pathlib import Path

from autoresearch.researcher import PromptResearchResult
from core.llm.tools import (
    ADD_THEMATIC_FLOW_TOOL,
    AUDIT_FINANCIAL_VALUATION_TOOL,
    FETCH_DAILY_NEWSLETTER_TOOL,
    FETCH_NEWSLETTER_CONTENT_TOOL,
    FIND_UNCORRELATED_ASSETS_TOOL,
    GET_EARNINGS_HISTORY_TOOL,
    GET_GLOBAL_MACRO_CONTEXT_TOOL,
    GET_KEY_METRICS_TOOL,
    GET_MACRO_ECONOMIC_SERIES_TOOL,
    GET_MARKET_FEELING_TOOL,
    GET_MARKET_HEALTH_BAROMETER_TOOL,
    GET_OPTION_CHAIN_TOOL,
    GET_OPTIONS_SENTIMENT_TOOL,
    GET_PORTFOLIO_LEDGER_TOOL,
    GET_PREDICTION_MARKET_ODDS_TOOL,
    GET_THEMATIC_FLOWS_TOOL,
    GET_TODAYS_NEWS_MENU_TOOL,
    GET_VERIFIER_REJECTIONS_TOOL,
    GET_VOLATILITY_INDEX_DETAILS_TOOL,
    POSITION_PNL_TOOL,
    PRICE_HISTORY_TOOL,
    RUN_STOCK_SCREENER_TOOL,
    SEARCH_PAST_MEMORIES_TOOL,
    SEARCH_PREDICTION_MARKETS_TOOL,
    SEARCH_RELATED_TICKERS_TOOL,
    SECTOR_ALTERNATIVES_TOOL,
    STOCK_TOOL,
    VOLATILITY_METRICS_TOOL,
    WEB_SEARCH_TOOL,
)


def _get_root_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def test_tools_json_is_valid_and_non_empty():
    """Verify packages/config/tools.json exists, parses, and contains expected tool structure."""
    tools_json_path = _get_root_dir() / "packages" / "config" / "tools.json"
    assert tools_json_path.is_file(), f"Missing tools.json at {tools_json_path}"

    with open(tools_json_path, encoding="utf-8") as f:
        tools_data = json.load(f)

    assert isinstance(tools_data, list)
    assert len(tools_data) >= 26

    names = set()
    for item in tools_data:
        assert "name" in item
        assert "desc" in item
        assert item["name"] not in names, f"Duplicate tool {item['name']} in tools.json"
        names.add(item["name"])


def test_tools_json_matches_engine_tool_definitions():
    """Verify every tool in tools.json has a matching canonical definition in core/llm/tools.py."""
    tools_json_path = _get_root_dir() / "packages" / "config" / "tools.json"
    with open(tools_json_path, encoding="utf-8") as f:
        tools_data = json.load(f)

    registered_canonical_tools = [
        STOCK_TOOL,
        PRICE_HISTORY_TOOL,
        POSITION_PNL_TOOL,
        VOLATILITY_METRICS_TOOL,
        SECTOR_ALTERNATIVES_TOOL,
        RUN_STOCK_SCREENER_TOOL,
        SEARCH_RELATED_TICKERS_TOOL,
        FIND_UNCORRELATED_ASSETS_TOOL,
        GET_KEY_METRICS_TOOL,
        AUDIT_FINANCIAL_VALUATION_TOOL,
        GET_MARKET_HEALTH_BAROMETER_TOOL,
        GET_EARNINGS_HISTORY_TOOL,
        SEARCH_PREDICTION_MARKETS_TOOL,
        GET_PREDICTION_MARKET_ODDS_TOOL,
        FETCH_DAILY_NEWSLETTER_TOOL,
        FETCH_NEWSLETTER_CONTENT_TOOL,
        SEARCH_PAST_MEMORIES_TOOL,
        GET_THEMATIC_FLOWS_TOOL,
        ADD_THEMATIC_FLOW_TOOL,
        WEB_SEARCH_TOOL,
        GET_PORTFOLIO_LEDGER_TOOL,
        GET_TODAYS_NEWS_MENU_TOOL,
        GET_MARKET_FEELING_TOOL,
        GET_GLOBAL_MACRO_CONTEXT_TOOL,
        GET_VOLATILITY_INDEX_DETAILS_TOOL,
        GET_VERIFIER_REJECTIONS_TOOL,
        GET_MACRO_ECONOMIC_SERIES_TOOL,
        GET_OPTIONS_SENTIMENT_TOOL,
        GET_OPTION_CHAIN_TOOL,
    ]
    registered_names = {t["function"]["name"] for t in registered_canonical_tools}

    for item in tools_data:
        tool_name = item["name"]
        assert tool_name in registered_names, f"Tool '{tool_name}' in tools.json missing from core/llm/tools.py"


def test_tools_json_matches_researcher_schema_description():
    """Verify every tool in tools.json is documented in PromptResearchResult.selected_tools description."""
    tools_json_path = _get_root_dir() / "packages" / "config" / "tools.json"
    with open(tools_json_path, encoding="utf-8") as f:
        tools_data = json.load(f)

    field_info = PromptResearchResult.model_fields["selected_tools"]
    description = field_info.description or ""

    for item in tools_data:
        tool_name = item["name"]
        assert f"'{tool_name}'" in description or f'"{tool_name}"' in description, (
            f"Tool '{tool_name}' in tools.json missing from PromptResearchResult selected_tools description in researcher.py"
        )


def test_tools_json_matches_program_md_spec():
    """Verify every tool in tools.json is documented in autoresearch/program.md."""
    tools_json_path = _get_root_dir() / "packages" / "config" / "tools.json"
    with open(tools_json_path, encoding="utf-8") as f:
        tools_data = json.load(f)

    program_md_path = _get_root_dir() / "apps" / "engine" / "autoresearch" / "program.md"
    assert program_md_path.is_file()
    program_text = program_md_path.read_text(encoding="utf-8")

    for item in tools_data:
        tool_name = item["name"]
        assert tool_name in program_text, (
            f"Tool '{tool_name}' in tools.json missing from autoresearch/program.md toolbox documentation"
        )
