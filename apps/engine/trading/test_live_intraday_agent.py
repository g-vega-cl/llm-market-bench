"""Hermetic tests for live intraday agent loop and multi-tier LLM execution."""

from __future__ import annotations

import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from trading.live_intraday_agent import (
    _extract_json_decision,
    _format_tape_age,
    build_session_context,
    calculate_technical_snapshot,
    execute_intraday_agent_step,
    fetch_active_candle,
    fetch_intraday_bars,
    query_multi_tier_llm,
    query_multi_tier_llm_raw,
    truncate_reasoning_trace,
)

ET = ZoneInfo("America/New_York")


def _fake_broker(order_id: str | None = "alpaca-ord-123", status: str = "SUBMITTED") -> MagicMock:
    """Broker double whose mirror call resolves like AlpacaBroker.submit_market_order."""
    broker = MagicMock()
    broker.submit_market_order = AsyncMock(return_value={"status": status, "order_id": order_id})
    return broker


def test_calculate_technical_snapshot():
    # Synthetic 25 bars
    bars = []
    base_price = 580.0
    for i in range(25):
        p = base_price + (i * 0.2)
        bars.append(
            {
                "time": f"2026-10-29T14:{i:02d}:00Z",
                "open": p - 0.1,
                "high": p + 0.3,
                "low": p - 0.2,
                "close": p,
                "volume": 1000 + (i * 10),
            }
        )

    indicators = calculate_technical_snapshot(bars)
    assert "vwap" in indicators
    assert indicators["vwap"] > 579.0
    assert "rsi_14" in indicators
    assert 0 <= indicators["rsi_14"] <= 100
    assert "ema_20" in indicators
    assert "trend" in indicators
    assert indicators["trend"] in ("BULLISH", "BEARISH", "NEUTRAL")


@pytest.mark.asyncio
async def test_query_multi_tier_llm_calls_auto_go_directly_without_strata():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "BUY",
                            "conviction": 85,
                            "thought": "SPY broke above morning VWAP with strong breadth.",
                            "memories_consulted": ["mem_001"],
                            "allocation_pct": 10,
                        }
                    )
                }
            }
        ]
    }
    mock_http.post.return_value = mock_resp

    messages = [{"role": "user", "content": "Analyze tape"}]
    with patch.dict(os.environ, {"FREE_PROXY_MASTER_KEY": "test-explicit-key"}):
        result = await query_multi_tier_llm(
            messages=messages,
            strata_url="http://localhost:8080/v1",
            cheap_proxy_url="https://llm.clvg.uk/v1",
            fallback_api_key="test-explicit-key",
            http_client=mock_http,
            purpose="live-spy-trader",
        )

    data = json.loads(result)
    assert data["action"] == "BUY"
    assert data["conviction"] == 85
    # Must bypass Strata completely and hit free-llm-proxy directly with auto-go
    assert len(mock_http.post.call_args_list) == 1
    call_url = mock_http.post.call_args_list[0][0][0]
    call_kwargs = mock_http.post.call_args_list[0][1]
    assert "llm.clvg.uk" in call_url
    assert "localhost:8080" not in call_url
    assert call_kwargs["json"]["model"] == "auto-go"
    assert "reasoning_budget_tokens" not in call_kwargs["json"]
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-explicit-key"
    assert call_kwargs["headers"]["X-Purpose"] == "live-spy-trader"


@pytest.mark.asyncio
async def test_query_multi_tier_llm_returns_neutral_hold_when_auto_go_fails():
    mock_http = AsyncMock()
    resp = MagicMock()
    resp.status_code = 503
    resp.text = "Server Unavailable"
    mock_http.post.return_value = resp

    messages = [{"role": "user", "content": "Analyze tape"}]
    with patch.dict(os.environ, {"FREE_PROXY_MASTER_KEY": "test-mock-master-key"}):
        result = await query_multi_tier_llm(
            messages=messages,
            strata_url="http://localhost:8080/v1",
            cheap_proxy_url="https://llm.clvg.uk/v1",
            http_client=mock_http,
        )

    data = json.loads(result)
    assert data["action"] == "HOLD"
    assert data["allocation_pct"] == 0
    assert len(mock_http.post.call_args_list) == 1
    assert "llm.clvg.uk" in mock_http.post.call_args_list[0][0][0]


@pytest.mark.asyncio
async def test_query_multi_tier_llm_without_master_key_hermetic():
    """Verify auto-go executes cleanly when no master key is configured (e.g. Clean CI runner)."""
    mock_http = AsyncMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "HOLD",
                            "conviction": 50,
                            "thought": "No key request.",
                            "memories_consulted": [],
                            "allocation_pct": 0,
                        }
                    )
                }
            }
        ]
    }
    mock_http.post.return_value = resp

    messages = [{"role": "user", "content": "Analyze tape"}]
    with patch("os.path.exists", return_value=False), patch.dict(os.environ, {"FREE_PROXY_MASTER_KEY": ""}):
        result = await query_multi_tier_llm(
            messages=messages,
            strata_url="http://localhost:8080/v1",
            cheap_proxy_url="https://llm.clvg.uk/v1",
            http_client=mock_http,
        )

    data = json.loads(result)
    assert data["action"] == "HOLD"
    assert len(mock_http.post.call_args_list) == 1
    proxy_call = mock_http.post.call_args_list[0]
    headers = proxy_call.kwargs.get("headers", {})
    assert "Authorization" not in headers
    assert proxy_call.kwargs["json"]["model"] == "auto-go"


@pytest.mark.asyncio
async def test_execute_intraday_agent_step_end_to_end_hermetic():
    # Mock Alpaca
    mock_alpaca_data = MagicMock()
    mock_bar = MagicMock()
    mock_bar.timestamp = MagicMock()
    mock_bar.timestamp.isoformat.return_value = "2026-10-29T14:30:00Z"
    mock_bar.open = 582.0
    mock_bar.high = 582.5
    mock_bar.low = 581.8
    mock_bar.close = 582.3
    mock_bar.volume = 5000.0
    mock_alpaca_data.get_stock_bars.return_value = MagicMock(data={"SPY": [mock_bar] * 25})

    mock_alpaca_trade = _fake_broker()

    # Mock Supabase
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "mem-1", "content": "Lesson: Morning gap fill rejection"}]
    )
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "mf-001"}])
    mock_sb.table.return_value = mock_table

    # Mock HTTP client
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "BUY",
                            "conviction": 80,
                            "thought": "Strong bounce from support, scaling in long.",
                            "memories_consulted": ["mem-1"],
                            "allocation_pct": 10,
                        }
                    )
                }
            }
        ]
    }
    mock_http.post.return_value = mock_resp

    with patch("trading.live_intraday_agent.aggregate_intraday_news", new=AsyncMock(return_value=[])):
        result = await execute_intraday_agent_step(
            alpaca_data_client=mock_alpaca_data,
            alpaca_broker=mock_alpaca_trade,
            sb_client=mock_sb,
            http_client=mock_http,
            ticker="SPY",
        )

    assert result["action"] == "BUY"
    assert result["conviction"] == 80
    assert result["order_id"] == "alpaca-ord-123"
    assert "portfolio" in result
    assert result["portfolio"]["signal"] == "BUY"
    assert result["portfolio"]["shares"] > 0
    assert mock_alpaca_trade.submit_market_order.await_count == 1
    assert mock_sb.table.called


@pytest.mark.asyncio
async def test_query_multi_tier_llm_raw_preserves_reasoning_and_token_count():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"action": "HOLD", "conviction": 55, "thought": "Wait.", "allocation_pct": 0}
                    ),
                    "reasoning": "RSI is mid-range and price is pinned to VWAP, so patience beats chasing.",
                }
            }
        ],
        "usage": {"completion_tokens_details": {"reasoning_tokens": 169}},
    }
    mock_http.post.return_value = mock_resp

    message = await query_multi_tier_llm_raw(
        messages=[{"role": "user", "content": "tape"}],
        fallback_api_key="test-key",
        http_client=mock_http,
    )

    assert json.loads(message["content"])["action"] == "HOLD"
    assert message["reasoning"] == "RSI is mid-range and price is pinned to VWAP, so patience beats chasing."
    assert message["reasoning_tokens"] == 169


@pytest.mark.asyncio
async def test_query_multi_tier_llm_raw_without_reasoning_field_is_empty():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": "plain content"}}]}
    mock_http.post.return_value = mock_resp

    message = await query_multi_tier_llm_raw(
        messages=[{"role": "user", "content": "tape"}],
        fallback_api_key="test-key",
        http_client=mock_http,
    )

    assert message["content"] == "plain content"
    assert message["reasoning"] == ""
    assert message["reasoning_tokens"] is None
    # The wrapper still hands plain callers the content string they expect.
    wrapped = await query_multi_tier_llm(
        messages=[{"role": "user", "content": "tape"}],
        fallback_api_key="test-key",
        http_client=mock_http,
    )
    assert wrapped == "plain content"


def test_truncate_reasoning_trace_caps_and_tolerates_none():
    assert truncate_reasoning_trace(None) == ""
    assert truncate_reasoning_trace("abc") == "abc"
    assert len(truncate_reasoning_trace("x" * 20000)) == 16000


@pytest.mark.asyncio
async def test_execute_intraday_agent_step_persists_reasoning_trace():
    mock_alpaca_data = MagicMock()
    mock_bar = MagicMock()
    mock_bar.timestamp = MagicMock()
    mock_bar.timestamp.isoformat.return_value = "2026-10-29T14:30:00Z"
    mock_bar.open = 582.0
    mock_bar.high = 582.5
    mock_bar.low = 581.8
    mock_bar.close = 582.3
    mock_bar.volume = 5000.0
    mock_alpaca_data.get_stock_bars.return_value = MagicMock(data={"SPY": [mock_bar] * 25})

    mock_alpaca_trade = _fake_broker()

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "mem-1", "content": "Lesson: Morning gap fill rejection"}]
    )
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "row-001"}])
    mock_sb.table.return_value = mock_table

    trace = "VWAP reclaim with breadth expansion; risking half size into the print."
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "BUY",
                            "conviction": 80,
                            "thought": "Scaling in long.",
                            "memories_consulted": ["mem-1"],
                            "allocation_pct": 10,
                        }
                    ),
                    "reasoning": trace,
                }
            }
        ],
        "usage": {"completion_tokens_details": {"reasoning_tokens": 412}},
    }
    mock_http.post.return_value = mock_resp

    with patch("trading.live_intraday_agent.aggregate_intraday_news", new=AsyncMock(return_value=[])):
        result = await execute_intraday_agent_step(
            alpaca_data_client=mock_alpaca_data,
            alpaca_broker=mock_alpaca_trade,
            sb_client=mock_sb,
            http_client=mock_http,
            ticker="SPY",
        )

    assert result["reasoning_trace"] == trace
    assert result["reasoning_tokens"] == 412

    inserts = [call.args[0] for call in mock_table.insert.call_args_list if call.args]
    trade_payloads = [p for p in inserts if p.get("signal") in ("BUY", "SELL")]
    feeling_payloads = [p for p in inserts if "why_explanation" in p]

    assert trade_payloads, "expected the fill to be written to trades"
    assert trade_payloads[0]["reasoning_trace"] == trace
    # The short thought stays the human-facing field.
    assert trade_payloads[0]["reasoning"] == "Scaling in long."

    assert feeling_payloads, "expected the turn to be written to market_feeling"
    summary = feeling_payloads[0]["trades_summary"]
    assert summary["reasoning_trace"] == trace
    assert summary["reasoning_tokens"] == 412


def test_extract_json_decision_clean_and_fallback():
    raw_md = '```json\n{"action": "BUY", "conviction": 80, "thought": "Good setup", "allocation_pct": 10}\n```'
    dec1 = _extract_json_decision(raw_md)
    assert dec1["action"] == "BUY"

    raw_text = 'Thinking aloud... {"action": "SELL", "conviction": 90, "thought": "Broken support", "allocation_pct": 5} Extra trailing text'
    dec2 = _extract_json_decision(raw_text)
    assert dec2["action"] == "SELL"

    dec3 = _extract_json_decision(None)
    assert dec3["action"] == "HOLD"


@pytest.mark.asyncio
async def test_fetch_active_candle_hermetic():
    mock_alpaca = MagicMock()
    mock_bar = MagicMock()
    mock_bar.timestamp = MagicMock()
    mock_bar.timestamp.isoformat.return_value = "2026-10-29T14:45:00Z"
    mock_bar.open = 582.0
    mock_bar.high = 582.8
    mock_bar.low = 581.9
    mock_bar.close = 582.4
    mock_bar.volume = 8000.0
    mock_alpaca.get_stock_bars.return_value = {"SPY": [mock_bar]}

    candle = await fetch_active_candle(mock_alpaca, "SPY")
    assert candle is not None
    assert candle["close"] == 582.4
    assert candle["time"] == "2026-10-29T14:45:00Z"

    # None client
    assert await fetch_active_candle(None, "SPY") is None


@pytest.mark.asyncio
async def test_fetch_intraday_bars_sort_descending_and_chronological():
    from alpaca.common.enums import Sort

    mock_alpaca = MagicMock()
    captured_req = None

    def fake_get_stock_bars(req):
        nonlocal captured_req
        captured_req = req
        # Alpaca returns bars in Sort.DESC order: newest first
        b_latest = MagicMock()
        b_latest.timestamp = MagicMock()
        b_latest.timestamp.isoformat.return_value = "2026-10-29T16:00:00Z"
        b_latest.open = 582.5
        b_latest.high = 582.9
        b_latest.low = 582.4
        b_latest.close = 582.8
        b_latest.volume = 12000.0

        b_earlier = MagicMock()
        b_earlier.timestamp = MagicMock()
        b_earlier.timestamp.isoformat.return_value = "2026-10-29T15:59:00Z"
        b_earlier.open = 582.1
        b_earlier.high = 582.6
        b_earlier.low = 582.0
        b_earlier.close = 582.5
        b_earlier.volume = 9500.0

        return {"SPY": [b_latest, b_earlier]}

    mock_alpaca.get_stock_bars.side_effect = fake_get_stock_bars

    bars = await fetch_intraday_bars(mock_alpaca, "SPY", window_minutes=60)

    # 1. Verify sort was set to Sort.DESC so we get newest bars, not oldest
    assert captured_req is not None
    assert getattr(captured_req, "sort", None) == Sort.DESC

    # 2. Verify returned list was reversed into ascending chronological order
    assert len(bars) == 2
    assert bars[0]["time"] == "2026-10-29T15:59:00Z"
    assert bars[1]["time"] == "2026-10-29T16:00:00Z"


@pytest.mark.asyncio
async def test_execute_intraday_agent_step_isolated_from_audience_queue():
    mock_alpaca_data = MagicMock()
    mock_alpaca_trade = MagicMock()
    mock_sb = MagicMock()
    mock_http = AsyncMock()

    # Mock intraday bars
    with (
        patch(
            "trading.live_intraday_agent.fetch_intraday_bars",
            new=AsyncMock(
                return_value=[
                    {
                        "time": "2026-10-29T14:00:00Z",
                        "open": 580,
                        "high": 581,
                        "low": 579,
                        "close": 580.5,
                        "volume": 1000,
                    }
                ]
            ),
        ),
        patch("trading.live_intraday_agent.aggregate_intraday_news", new=AsyncMock(return_value=[])),
    ):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "HOLD",
                                "conviction": 65,
                                "thought": "Consolidating near VWAP $580.50.",
                                "allocation_pct": 0,
                                "memories_consulted": ["mem-1"],
                            }
                        )
                    }
                }
            ]
        }
        mock_http.post.return_value = mock_resp

        result = await execute_intraday_agent_step(
            alpaca_data_client=mock_alpaca_data,
            alpaca_broker=mock_alpaca_trade,
            sb_client=mock_sb,
            http_client=mock_http,
            ticker="SPY",
        )

        assert result["action"] == "HOLD"
        assert result.get("queue_item_id") is None

        # Verify trader prompt NEVER contains untrusted audience questions
        posted_payload = mock_http.post.call_args[1]["json"]
        user_content = posted_payload["messages"][1]["content"]
        assert "<audience_question" not in user_content
        assert "audience" not in user_content.lower()


def _bar(time_iso: str, close: float = 580.5) -> dict[str, object]:
    return {"time": time_iso, "open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000}


def test_build_session_context_weekend_flags_stale_tape():
    # Saturday 2026-11-21 14:25 ET; newest print is Friday's 15:59 ET close.
    now_et = datetime(2026, 11, 21, 14, 25, tzinfo=ET)
    ctx = build_session_context([_bar("2026-11-20T20:59:00Z")], is_market_open=False, now_et=now_et)

    assert ctx["state"] == "CLOSED"
    assert ctx["phase"] == "weekend"
    assert ctx["tape_age_minutes"] == pytest.approx(1346.0)
    assert ctx["last_print"] == "Friday, Nov 20 2026, 15:59 ET"
    assert "### SESSION STATE" in ctx["block"]
    assert "Today is Saturday, Nov 21 2026, 14:25 ET, a weekend day" in ctx["block"]
    assert "Latest tape print: Friday, Nov 20 2026, 15:59 ET — 22h 26m old" in ctx["block"]
    assert "next regular session opens Monday, Nov 23 2026, 09:30 ET" in ctx["block"]
    assert "static closing prints, not live quotes" in ctx["block"]


def test_build_session_context_recomputes_for_a_later_weekend():
    # The same code path must produce next weekend's dates with no code change.
    now_et = datetime(2026, 11, 28, 10, 5, tzinfo=ET)
    ctx = build_session_context([_bar("2026-11-27T20:59:00Z")], is_market_open=False, now_et=now_et)

    assert "Today is Saturday, Nov 28 2026, 10:05 ET" in ctx["block"]
    assert "next regular session opens Monday, Nov 30 2026, 09:30 ET" in ctx["block"]
    assert "Latest tape print: Friday, Nov 27 2026, 15:59 ET" in ctx["block"]
    assert "18h 6m old" in ctx["block"]
    assert "Nov 21" not in ctx["block"]


def test_build_session_context_open_session_has_no_block():
    now_et = datetime(2026, 11, 18, 11, 0, tzinfo=ET)
    ctx = build_session_context([_bar("2026-11-18T15:59:00Z")], is_market_open=True, now_et=now_et)

    assert ctx["state"] == "OPEN"
    assert ctx["phase"] == "regular_session"
    assert ctx["block"] is None


def test_build_session_context_weekday_after_hours_points_at_next_weekday_open():
    now_et = datetime(2026, 11, 20, 18, 40, tzinfo=ET)
    ctx = build_session_context([_bar("2026-11-20T20:59:00Z")], is_market_open=False, now_et=now_et)

    assert ctx["phase"] == "after_hours"
    assert "after the close" in ctx["block"]
    assert "next regular session opens Monday, Nov 23 2026, 09:30 ET" in ctx["block"]


def test_build_session_context_pre_market_points_at_same_day_open():
    now_et = datetime(2026, 11, 23, 8, 15, tzinfo=ET)
    ctx = build_session_context([_bar("2026-11-20T20:59:00Z")], is_market_open=False, now_et=now_et)

    assert ctx["phase"] == "pre_market"
    assert "before today's open" in ctx["block"]
    assert "next regular session opens Monday, Nov 23 2026, 09:30 ET" in ctx["block"]


def test_build_session_context_without_bars_says_no_tape():
    now_et = datetime(2026, 11, 21, 9, 0, tzinfo=ET)
    ctx = build_session_context([], is_market_open=False, now_et=now_et)

    assert ctx["tape_age_minutes"] is None
    assert "No tape data is available for this turn" in ctx["block"]


def test_format_tape_age_units():
    assert _format_tape_age(47) == "47m"
    assert _format_tape_age(1106) == "18h 26m"
    assert _format_tape_age(3000) == "2d 2h"
    assert _format_tape_age(-12) == "0m"


async def _run_step_capturing_prompt(is_market_open: bool) -> dict[str, str]:
    """Run one hermetic turn and return the system/user prompts actually posted."""
    mock_alpaca_data = MagicMock()
    mock_sb = MagicMock()
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"action": "HOLD", "conviction": 40, "thought": "t", "allocation_pct": 0})
                }
            }
        ]
    }
    mock_http.post.return_value = mock_resp

    with (
        patch(
            "trading.live_intraday_agent.fetch_intraday_bars",
            new=AsyncMock(return_value=[_bar("2026-11-20T20:59:00Z")]),
        ),
        patch("trading.live_intraday_agent.aggregate_intraday_news", new=AsyncMock(return_value=[])),
    ):
        await execute_intraday_agent_step(
            alpaca_data_client=mock_alpaca_data,
            alpaca_broker=None,
            sb_client=mock_sb,
            http_client=mock_http,
            ticker="SPY",
            is_market_open=is_market_open,
        )

    payload = mock_http.post.call_args[1]["json"]
    return {
        "system": payload["messages"][0]["content"],
        "user": payload["messages"][1]["content"],
    }


@pytest.mark.asyncio
async def test_closed_session_prompt_injects_staleness_notice():
    prompts = await _run_step_capturing_prompt(is_market_open=False)

    assert prompts["user"].startswith("### SESSION STATE")
    assert "Regular market session is CLOSED" in prompts["user"]
    assert "Latest tape print:" in prompts["user"]
    assert "static closing prints, not live quotes" in prompts["user"]
    assert "stale closing print, not a live quote" in prompts["system"]
    # The JSON contract must survive the extra system rule.
    assert '"action": "BUY" | "SELL" | "HOLD"' in prompts["system"]


@pytest.mark.asyncio
async def test_open_session_prompt_has_no_staleness_notice():
    prompts = await _run_step_capturing_prompt(is_market_open=True)

    assert "SESSION STATE" not in prompts["user"]
    assert "stale" not in prompts["system"].lower()
    assert prompts["user"].startswith("### SPY 120-MINUTE TAPE SNAPSHOT")
