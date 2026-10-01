"""TDD contract and unit tests for the vertical slice refactoring of core.llm.analysis."""

from pathlib import Path

from core.models import DecisionObject, DecisionsResponse


def test_analysis_pipeline_vertical_modules_exist():
    """Verify each decomposed vertical module exists and exports expected domain functions."""
    from core.llm.analysis_pipeline import prompt_assembly, response_parsing, validation

    # 1. Prompt assembly module exports
    assert hasattr(prompt_assembly, "format_news_content")
    assert hasattr(prompt_assembly, "extract_held_tickers")
    assert hasattr(prompt_assembly, "extract_tickers_from_chunks")
    assert hasattr(prompt_assembly, "resolve_experiment_tools")
    assert hasattr(prompt_assembly, "resolve_web_search_flag")
    assert hasattr(prompt_assembly, "prepare_messages_for_provider")
    assert hasattr(prompt_assembly, "build_schema_hint")
    assert hasattr(prompt_assembly, "build_provider_extraction_args")

    # 2. Response parsing module exports
    assert hasattr(response_parsing, "repair_json_string")
    assert hasattr(response_parsing, "try_parse_response")
    assert hasattr(response_parsing, "try_parse_decisions_response")
    assert hasattr(response_parsing, "extract_structured_response")
    assert hasattr(response_parsing, "aggregate_response_blocks")
    assert hasattr(response_parsing, "create_fallback_model")

    # 3. Validation module exports
    assert hasattr(validation, "scan_history_for_tools")
    assert hasattr(validation, "get_history_tool_calls_diagnostic")
    assert hasattr(validation, "detect_missing_tool_decisions")
    assert hasattr(validation, "build_tool_correction_message")
    assert hasattr(validation, "enforce_tool_call_history")
    assert hasattr(validation, "validate_portfolio_holdings")
    assert hasattr(validation, "attach_attribution_trace")


def test_core_llm_analysis_barrel_parity():
    """Verify core.llm.analysis maintains full backward compatibility for all callers and tests."""
    from core.llm import analysis

    expected_exports = [
        "analyze_with_provider",
        "_repair_json_string",
        "_try_parse_response",
        "_try_parse_decisions_response",
        "_scan_history_for_tools",
        "_get_history_tool_calls_diagnostic",
        "_extract_tickers_from_chunks",
        "_extract_held_tickers",
        "_flatten_messages_for_minimax",
        "safe_deepcopy",
        "_TICKER_FALSE_POSITIVES",
        "_MAJOR_INDICES",
    ]

    for export_name in expected_exports:
        assert hasattr(analysis, export_name), f"Missing backward-compatible export: {export_name}"

    # Verify mock target attributes exist on the module
    assert hasattr(analysis, "clients")
    assert hasattr(analysis, "PromptFactory")
    assert hasattr(analysis, "log_reasoning_trace")


def test_prompt_assembly_domain_logic():
    """Verify prompt assembly domain behaviors (news formatting, ticker extraction)."""
    from core.llm.analysis_pipeline.prompt_assembly import (
        extract_held_tickers,
        extract_tickers_from_chunks,
        format_news_content,
    )

    # 1. News formatting with summaries
    chunks = [{"source_id": "src1", "sender": "Bloomberg", "subject": "Rates", "content": "Full text"}]
    summaries = {"src1": "Fed holds rates steady."}
    formatted = format_news_content(chunks, summaries)
    assert "Fed holds rates steady." in formatted
    assert "Bloomberg" in formatted

    # 2. News formatting without summaries
    formatted_raw = format_news_content(chunks, None)
    assert "Full text" in formatted_raw

    # 3. Held tickers extraction
    portfolio = "- NVDA: 10 shares\n- AAPL: 50 shares\n- Cash: $1000"
    held = extract_held_tickers(portfolio)
    assert held == ["NVDA", "AAPL"]

    # 4. Ticker candidate extraction with dollar signs and false positive filtration
    chunks_with_tickers = [
        {"content": "Rumors about $MSFT acquiring an AI startup. The $CEO made a statement. $SPY rallied."}
    ]
    extracted = extract_tickers_from_chunks(chunks_with_tickers, held)
    assert "MSFT" in extracted
    assert "NVDA" in extracted
    assert "SPY" in extracted
    assert "CEO" not in extracted  # False positive filtered


def test_response_parsing_domain_logic():
    """Verify response parsing and JSON repair domain behaviors."""
    from core.llm.analysis_pipeline.response_parsing import (
        create_fallback_model,
        repair_json_string,
        try_parse_response,
    )

    # 1. JSON repair with wrapped quotes and extra text
    raw = '```json\n{"decisions": [{"signal": "BUY", "ticker": "AAPL", "confidence": 90, "reasoning": "Rally", "source_id": "news_1"}]}\n``` extra comments'
    cleaned = repair_json_string(raw)
    assert cleaned.startswith("{")
    assert cleaned.endswith("}")

    # 2. Response parsing
    parsed = try_parse_response(cleaned, DecisionsResponse)
    assert parsed is not None
    assert len(parsed.decisions) == 1
    assert parsed.decisions[0].ticker == "AAPL"

    # 3. Fallback model
    fallback = create_fallback_model(DecisionsResponse)
    assert isinstance(fallback, DecisionsResponse)
    assert fallback.decisions == []


def test_validation_domain_logic():
    """Verify tool scanning, hard enforcement, and portfolio validation domain behaviors."""
    from core.llm.analysis_pipeline.validation import (
        enforce_tool_call_history,
        scan_history_for_tools,
        validate_portfolio_holdings,
    )

    # 1. Tool scanning in history
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "name": "calculate_buy_quantity",
                        "arguments": '{"ticker": "NVDA", "percentage": 10}',
                    }
                }
            ],
        }
    ]
    scan_res = scan_history_for_tools(messages, "NVDA")
    assert scan_res["buy_tool_found"] is True
    assert scan_res["sell_tool_found"] is False

    # 2. Hard enforcement: flip buy_tool_called to False if not in history
    unverified_decision = DecisionObject(
        ticker="MSFT",
        signal="BUY",
        confidence=80,
        reasoning="Good cloud growth",
        source_id="news_1",
        buy_tool_called=True,  # Self-reported lie
    )
    resp = DecisionsResponse(decisions=[unverified_decision])
    enforce_tool_call_history(resp, messages, provider="openai", model_name="gpt-4o")
    assert resp.decisions[0].buy_tool_called is False

    # 3. Portfolio ownership validation: SELL for unheld ticker converted to HOLD
    unheld_sell = DecisionObject(
        ticker="TSLA",
        signal="SELL",
        confidence=75,
        reasoning="Overvalued",
        source_id="news_2",
    )
    resp_sell = DecisionsResponse(decisions=[unheld_sell])
    validate_portfolio_holdings(
        resp_sell,
        portfolio_context="- NVDA: 100 shares",
        provider="openai",
        model_name="gpt-4o",
    )
    assert resp_sell.decisions[0].signal == "HOLD"
    assert "REJECTED_OWNERSHIP" in resp_sell.decisions[0].reasoning


def test_file_size_and_loc_ceilings():
    """Ensure refactored analysis.py and new vertical modules strictly adhere to file size limits."""
    repo_root = Path(__file__).resolve().parent.parent

    # analysis.py must be <= 300 LOC (down from 1,353 LOC)
    analysis_file = repo_root / "core" / "llm" / "analysis.py"
    with open(analysis_file, encoding="utf-8") as f:
        analysis_loc = sum(1 for line in f if line.strip())
    assert analysis_loc <= 300, f"analysis.py is {analysis_loc} LOC, expected <= 300"

    # All vertical pipeline modules must be <= 400 LOC (GEMINI.md soft ceiling)
    pipeline_dir = repo_root / "core" / "llm" / "analysis_pipeline"
    for py_file in pipeline_dir.glob("*.py"):
        with open(py_file, encoding="utf-8") as f:
            loc = sum(1 for line in f if line.strip())
        assert loc <= 400, f"{py_file.name} is {loc} LOC, expected <= 400"
