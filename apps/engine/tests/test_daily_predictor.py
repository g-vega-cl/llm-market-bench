from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_CONSTRAINTS_FOOTER,
    DAILY_PREDICTOR_CONSTRAINTS_HEADER,
    DAILY_PREDICTOR_PROMPT,
    DailyPredictionOutput,
    split_daily_predictor_prompt,
)
from tasks.daily_predictor import run_daily_prediction


def test_split_daily_predictor_prompt():
    header, mutable, footer = split_daily_predictor_prompt(DAILY_PREDICTOR_PROMPT)
    assert header == DAILY_PREDICTOR_CONSTRAINTS_HEADER
    assert footer == DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    assert "MACRO CATALYST EXTRACTION" in mutable

    # Test fallback
    custom_prompt = "Custom instructions text"
    h, m, f = split_daily_predictor_prompt(custom_prompt)
    assert h == DAILY_PREDICTOR_CONSTRAINTS_HEADER
    assert m == custom_prompt
    assert f == DAILY_PREDICTOR_CONSTRAINTS_FOOTER


def test_daily_predictor_prompt_symmetry():
    """Verify DAILY_PREDICTOR_PROMPT is strictly symmetric and counter-biases against always-UP predictions."""
    header, mutable, footer = split_daily_predictor_prompt(DAILY_PREDICTOR_PROMPT)

    # Must explicitly direct symmetric zero-mean base-rate evaluation in header or mutable
    assert "ZERO-MEAN BASE RATE" in header or "ZERO-MEAN BASE RATE" in mutable
    assert "SYMMETRIC" in mutable

    # Must contain explicit bearish directives alongside bullish directives
    full_prompt = DAILY_PREDICTOR_PROMPT.lower()
    assert "bearish catalyst" in full_prompt
    assert "bullish catalyst" in full_prompt
    assert "down" in full_prompt and "up" in full_prompt


@pytest.mark.asyncio
async def test_run_daily_prediction_arena_success():
    mock_supabase = MagicMock()

    # Mock active prompt DB query
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "variant_tag": "daily-pred-tag1",
            "prompt_content": DAILY_PREDICTOR_PROMPT,
        }
    ]

    # Mock upsert
    mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "test-uuid"}]

    mock_deepseek = MagicMock()
    mock_prediction = DailyPredictionOutput(
        predicted_direction="UP",
        confidence=75.0,
        expected_return_pct=0.42,
        rationale="Overnight futures up and strong tech momentum.",
        catalysts=["Tech earnings", "Fed stance"],
    )
    mock_deepseek.chat.completions.create.return_value = mock_prediction

    mock_minimax = AsyncMock()
    mock_minimax.chat_with_json_response = AsyncMock(
        return_value={
            "predicted_direction": "DOWN",
            "confidence": 60.0,
            "expected_return_pct": -0.30,
            "rationale": "Overextended RSI and pending macro risk.",
            "catalysts": ["CPI release"],
        }
    )
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
    ):
        results = await run_daily_prediction(ticker="SPY")
        assert isinstance(results, list)
        assert len(results) == 2

        deepseek_res = next((r for r in results if r["model_name"] == "deepseek-v4-flash"), None)
        assert deepseek_res is not None
        assert deepseek_res["predicted_direction"] == "UP"
        assert deepseek_res["confidence"] == 75.0

        minimax_res = next((r for r in results if r["model_name"] == "MiniMax-M3"), None)
        assert minimax_res is not None
        assert minimax_res["predicted_direction"] == "DOWN"
        assert minimax_res["confidence"] == 60.0


@pytest.mark.asyncio
async def test_run_daily_prediction_partial_failure():
    mock_supabase = MagicMock()

    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "variant_tag": "daily-pred-tag1",
            "prompt_content": DAILY_PREDICTOR_PROMPT,
        }
    ]
    mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "test-uuid"}]

    mock_deepseek = MagicMock()
    mock_prediction = DailyPredictionOutput(
        predicted_direction="UP",
        confidence=80.0,
        expected_return_pct=0.50,
        rationale="Strong pre-market breakout.",
        catalysts=["Earnings beat"],
    )
    mock_deepseek.chat.completions.create.return_value = mock_prediction

    # MiniMax fails on all attempts
    mock_minimax = AsyncMock()
    mock_minimax.chat_with_json_response = AsyncMock(side_effect=Exception("MiniMax API Timeout"))
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        results = await run_daily_prediction(ticker="SPY")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["model_name"] == "deepseek-v4-flash"
        assert results[0]["predicted_direction"] == "UP"


@pytest.mark.asyncio
async def test_get_daily_market_context_technicals():
    from tasks.daily_predictor import get_daily_market_context

    mock_history = [{"price": 700.0 + i, "fetched_at": f"2026-07-{i + 1:02d}T00:00:00Z"} for i in range(25)]
    mock_mdm = MagicMock()
    mock_mdm.is_premarket = AsyncMock(return_value=False)
    mock_mdm.get_history = AsyncMock(return_value=mock_history)
    mock_mdm.get_premarket_quote = AsyncMock(
        return_value={
            "price": 725.50,
            "previous_close": 724.00,
            "change": 1.50,
            "change_pct": 0.207,
        }
    )

    with (
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
        patch(
            "core.llm.tools.execute_get_global_macro_context_tool", new_callable=AsyncMock, return_value="Macro test"
        ),
        patch(
            "core.llm.tools.execute_get_volatility_index_details_tool", new_callable=AsyncMock, return_value="VIX test"
        ),
        patch("core.llm.tools.execute_market_health_barometer_tool", new_callable=AsyncMock, return_value="Baro test"),
        patch("core.llm.tools.execute_get_market_feeling_tool", new_callable=AsyncMock, return_value="Feeling test"),
    ):
        ctx = await get_daily_market_context(ticker="SPY")
        assert "Previous Trading Session" in ctx
        assert "5-Day Return" in ctx
        assert "20-Day Simple Moving Average" in ctx
        assert "Live Pre-Market / Early Session Quote" in ctx
        assert "Overnight Gap: +1.50 (+0.21%)" in ctx
        assert "$725.50" in ctx
        assert "Prior Session Macro Baseline" in ctx
        assert "Volatility Index Details" in ctx
        assert "Market Health Barometer" in ctx
        assert "Recent Market Feeling" in ctx


@pytest.mark.asyncio
async def test_get_daily_market_context_premarket_multi_asset():
    from tasks.daily_predictor import get_daily_market_context

    mock_history = [
        {"price": 590.0, "fetched_at": "2026-08-17T00:00:00Z"},
        {"price": 592.0, "fetched_at": "2026-08-18T00:00:00Z"},
    ]
    mock_mdm = MagicMock()
    mock_mdm.is_premarket = AsyncMock(return_value=True)
    mock_mdm.get_history = AsyncMock(return_value=mock_history)

    async def mock_get_pm_quote(sym):
        quotes = {
            "SPY": {"price": 595.0, "previous_close": 592.0, "change": 3.0, "change_pct": 0.507},
            "QQQ": {"price": 510.0, "previous_close": 508.0, "change": 2.0, "change_pct": 0.394},
            "DIA": {"price": 440.0, "previous_close": 439.0, "change": 1.0, "change_pct": 0.228},
            "IWM": {"price": 220.0, "previous_close": 221.0, "change": -1.0, "change_pct": -0.452},
            "EWJ": {"price": 75.0, "previous_close": 74.5, "change": 0.5, "change_pct": 0.671},
            "VGK": {"price": 68.0, "previous_close": 67.8, "change": 0.2, "change_pct": 0.30},
            "TLT": {"price": 92.0, "previous_close": 92.5, "change": -0.5, "change_pct": -0.541},
            "IEF": {"price": 95.0, "previous_close": 95.2, "change": -0.2, "change_pct": -0.210},
            "GLD": {"price": 240.0, "previous_close": 239.0, "change": 1.0, "change_pct": 0.418},
            "USO": {"price": 75.0, "previous_close": 76.0, "change": -1.0, "change_pct": -1.316},
            "UUP": {"price": 28.5, "previous_close": 28.4, "change": 0.1, "change_pct": 0.352},
        }
        return quotes.get(sym)

    mock_mdm.get_premarket_quote = AsyncMock(side_effect=mock_get_pm_quote)

    with (
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
        patch(
            "core.llm.tools.execute_get_global_macro_context_tool", new_callable=AsyncMock, return_value="Macro test"
        ),
        patch(
            "core.llm.tools.execute_get_volatility_index_details_tool", new_callable=AsyncMock, return_value="VIX test"
        ),
        patch("core.llm.tools.execute_market_health_barometer_tool", new_callable=AsyncMock, return_value="Baro test"),
        patch("core.llm.tools.execute_get_market_feeling_tool", new_callable=AsyncMock, return_value="Feeling test"),
    ):
        ctx = await get_daily_market_context(ticker="SPY")
        assert "=== LIVE PRE-MARKET ACTION & GAP ANALYSIS ===" in ctx
        assert "Target Asset (SPY): $595.00 | Overnight Gap: +3.00 (+0.51%) vs Prev Close $592.00" in ctx
        assert "Pre-Market Benchmark Indices & Key Macro Drivers" in ctx
        assert "- QQQ (Nasdaq 100)" in ctx and "+0.39%" in ctx
        assert "- DIA (Dow Jones)" in ctx and "+0.23%" in ctx
        assert "- IWM (Russell 2000)" in ctx and "-0.45%" in ctx
        assert "- EWJ (Japan MSCI)" in ctx and "+0.67%" in ctx
        assert "- VGK (Europe FTSE)" in ctx and "+0.30%" in ctx
        assert "- TLT (20+yr Treasury" in ctx and "-0.54%" in ctx
        assert "- IEF (7-10yr Treasury" in ctx and "-0.21%" in ctx
        assert "- GLD (Gold)" in ctx and "+0.42%" in ctx
        assert "- USO (WTI Crude Oil)" in ctx and "-1.32%" in ctx
        assert "- UUP (US Dollar Index)" in ctx and "+0.35%" in ctx
        assert "Prior Session Macro Baseline" in ctx


def test_daily_predictor_prompt_footer_json_schema():
    """Verify DAILY_PREDICTOR_CONSTRAINTS_FOOTER specifies explicit JSON structure."""
    assert "{" in DAILY_PREDICTOR_CONSTRAINTS_FOOTER and "}" in DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    assert "predicted_direction" in DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    assert "confidence" in DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    assert "expected_return_pct" in DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    assert "rationale" in DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    assert "catalysts" in DAILY_PREDICTOR_CONSTRAINTS_FOOTER


@pytest.mark.asyncio
async def test_minimax_daily_prediction_includes_strict_json_prompt_and_tokens():
    """Verify that MiniMax daily predictor receives explicit JSON directive and 8192 tokens."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "variant_tag": "daily-pred-tag1",
            "prompt_content": DAILY_PREDICTOR_PROMPT,
        }
    ]
    mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "test-uuid"}]

    mock_deepseek = MagicMock()
    mock_prediction = DailyPredictionOutput(
        predicted_direction="UP",
        confidence=75.0,
        expected_return_pct=0.42,
        rationale="Tech momentum.",
        catalysts=["Tech earnings"],
    )
    mock_deepseek.chat.completions.create.return_value = mock_prediction

    minimax_calls = []

    async def mock_minimax_chat(messages, model=None, max_completion_tokens=None, temperature=0.3):
        minimax_calls.append(
            {
                "messages": messages,
                "model": model,
                "max_completion_tokens": max_completion_tokens,
                "temperature": temperature,
            }
        )
        return {
            "predicted_direction": "DOWN",
            "confidence": 60.0,
            "expected_return_pct": -0.30,
            "rationale": "Overextended RSI.",
            "catalysts": ["CPI"],
        }

    mock_minimax = MagicMock()
    mock_minimax.chat_with_json_response = mock_minimax_chat
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
    ):
        results = await run_daily_prediction(ticker="SPY")
        assert len(results) == 2
        assert len(minimax_calls) == 1
        call = minimax_calls[0]
        assert call["max_completion_tokens"] == 8192
        user_msg = next((m["content"] for m in call["messages"] if m["role"] == "user"), "")
        assert "json" in user_msg.lower()
        assert "predicted_direction" in user_msg


@pytest.mark.asyncio
async def test_fetch_active_daily_prompt_model_track_isolation():
    """Verify that fetch_active_daily_prompt never falls back across model tracks."""
    from tasks.daily_predictor import fetch_active_daily_prompt

    mock_supabase = MagicMock()
    # Mock query returning empty data for deepseek track
    query_mock = MagicMock()
    query_mock.execute.return_value.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value = query_mock

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch(
            "tasks.daily_predictor.seed_daily_predictor_prompt",
            new_callable=AsyncMock,
            return_value=("daily-pred-seeded-deepseek-v4-flash", DAILY_PREDICTOR_PROMPT),
        ) as mock_seed,
    ):
        tag, content = await fetch_active_daily_prompt("deepseek-v4-flash")
        assert "minimax" not in tag.lower()
        assert tag == "daily-pred-seeded-deepseek-v4-flash"
        assert mock_seed.called
        mock_seed.assert_called_once_with(model_name="deepseek-v4-flash")

