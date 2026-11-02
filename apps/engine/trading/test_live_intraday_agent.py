"""Hermetic tests for live intraday agent loop and multi-tier LLM execution."""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trading.live_intraday_agent import (
    _extract_json_decision,
    calculate_technical_snapshot,
    execute_intraday_agent_step,
    fetch_active_candle,
    fetch_intraday_bars,
    query_multi_tier_llm,
)


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
async def test_query_multi_tier_llm_strata_success():
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
    result = await query_multi_tier_llm(
        messages=messages,
        strata_url="http://localhost:8080/v1",
        cheap_proxy_url="https://llm.clvg.uk/v1",
        http_client=mock_http,
    )

    data = json.loads(result)
    assert data["action"] == "BUY"
    assert data["conviction"] == 85
    # Strata was called on the first try with 45s runway and 16k/12k headroom
    assert "localhost:8080" in mock_http.post.call_args_list[0][0][0]
    strata_call = mock_http.post.call_args_list[0][1]
    assert strata_call["timeout"] == 45.0
    assert strata_call["json"]["max_tokens"] == 16384
    assert strata_call["json"]["reasoning_budget_tokens"] == 12288


@pytest.mark.asyncio
async def test_query_multi_tier_llm_fallback_to_cheap_proxy():
    mock_http = AsyncMock()

    async def mock_post(url, **kwargs):
        resp = MagicMock()
        if "localhost:8080" in str(url):
            # Strata stalls / down
            resp.status_code = 503
            resp.text = "Server Unavailable"
        else:
            # Fallback to cheap proxy succeeds
            resp.status_code = 200
            resp.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": "HOLD",
                                    "conviction": 60,
                                    "thought": "Chop near resistance, holding cash.",
                                    "memories_consulted": [],
                                    "allocation_pct": 0,
                                }
                            )
                        }
                    }
                ]
            }
        return resp

    mock_http.post.side_effect = mock_post

    messages = [{"role": "user", "content": "Analyze tape"}]
    with patch.dict(os.environ, {"FREE_PROXY_MASTER_KEY": "test-mock-master-key"}):
        result = await query_multi_tier_llm(
            messages=messages,
            strata_url="http://localhost:8080/v1",
            cheap_proxy_url="https://llm.clvg.uk/v1",
            fallback_api_key="test-explicit-key",
            http_client=mock_http,
        )

    data = json.loads(result)
    assert data["action"] == "HOLD"
    assert data["conviction"] == 60
    assert len(mock_http.post.call_args_list) == 2
    fallback_call = mock_http.post.call_args_list[1][1]
    assert fallback_call["json"]["max_tokens"] == 16384
    assert fallback_call["json"]["model"] == "free-auto"

    # Verify fallback call headers and model
    fallback_call = mock_http.post.call_args_list[1]
    headers = fallback_call.kwargs.get("headers", {})
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test-explicit-key"
    payload = fallback_call.kwargs.get("json", {})
    assert payload.get("model") == "free-auto"


@pytest.mark.asyncio
async def test_query_multi_tier_llm_fallback_without_master_key_hermetic():
    """Verify fallback executes cleanly when no master key is configured (e.g. Clean CI runner)."""
    mock_http = AsyncMock()

    async def mock_post(url, **kwargs):
        resp = MagicMock()
        if "localhost:8080" in str(url):
            resp.status_code = 503
            resp.text = "Server Unavailable"
        else:
            resp.status_code = 200
            resp.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": "HOLD",
                                    "conviction": 50,
                                    "thought": "No key fallback.",
                                    "memories_consulted": [],
                                    "allocation_pct": 0,
                                }
                            )
                        }
                    }
                ]
            }
        return resp

    mock_http.post.side_effect = mock_post

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
    fallback_call = mock_http.post.call_args_list[1]
    headers = fallback_call.kwargs.get("headers", {})
    assert "Authorization" not in headers


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

    mock_alpaca_trade = MagicMock()
    mock_account = MagicMock()
    mock_account.cash = "25000.00"
    mock_alpaca_trade.get_account.return_value = mock_account
    mock_alpaca_trade.submit_order.return_value = MagicMock(id="alpaca-ord-123", status="accepted")

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
            alpaca_trading_client=mock_alpaca_trade,
            sb_client=mock_sb,
            http_client=mock_http,
            ticker="SPY",
        )

    assert result["action"] == "BUY"
    assert result["conviction"] == 80
    assert result["order_id"] == "alpaca-ord-123"
    assert mock_alpaca_trade.submit_order.called
    assert mock_sb.table.called


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
            alpaca_trading_client=mock_alpaca_trade,
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


@pytest.mark.asyncio
async def test_persist_intraday_news_upserts_cleanly():
    from trading.live_intraday_agent import persist_intraday_news

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_table.upsert.return_value = mock_upsert
    mock_sb.table.return_value = mock_table

    news_items = [
        {
            "headline": "Fed Holds Policy Rates Steady at 4.5%",
            "summary": "FOMC keeps benchmark interest rate unchanged.",
            "source": "Alpaca Benzinga",
            "url": "https://benzinga.com/news/123",
            "tickers": ["SPY", "TLT"],
            "published_at": "2026-11-01T20:00:00Z",
            "source_id_hash": "hash_fed_01",
        }
    ]

    count = await persist_intraday_news(news_items, sb_client=mock_sb)
    assert count == 1
    mock_sb.table.assert_called_with("intraday_market_news")
    mock_table.upsert.assert_called_once()
    upsert_arg = mock_table.upsert.call_args[0][0]
    assert len(upsert_arg) == 1
    assert upsert_arg[0]["headline"] == "Fed Holds Policy Rates Steady at 4.5%"
    assert upsert_arg[0]["tickers"] == ["SPY", "TLT"]
    assert upsert_arg[0]["source_id_hash"] == "hash_fed_01"
    assert mock_table.upsert.call_args[1]["on_conflict"] == "source_id_hash"
