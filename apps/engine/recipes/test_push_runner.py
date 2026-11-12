"""Hermetic TDD tests for the 4-block push-based strategy schema, hydrator, and runner."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from recipes.push_hydrator import (
    filter_memory_rows,
    filter_news_rows,
    format_technicals_block,
    hydrate_stage_prompt,
)
from recipes.push_runner import (
    parse_trade_signals,
    pick_random_two_week_window,
    run_push_backtest,
    run_push_live,
)
from recipes.push_schema import PushStrategy


def _sample_strategy(multi_stage: bool = False) -> PushStrategy:
    stages = [
        {
            "id": "stage-1",
            "title": "Research & Filter",
            "selected_tools": ["get_technical_indicators", "get_key_metrics"],
            "blocks": [
                {"id": "b1", "type": "prompt", "text": "Find momentum catalysts."},
                {"id": "b2", "type": "news", "contains": ["Trump", "chips"], "recency_hours": 48},
                {
                    "id": "b3",
                    "type": "memories",
                    "contains": ["tariff"],
                    "recency_hours": 168,
                    "category": "MARKET_EVENT",
                    "min_importance": 6,
                },
                {
                    "id": "b4",
                    "type": "technicals",
                    "rules": [
                        {"metric": "P/E", "operator": "<", "target": "35"},
                        {"metric": "RSI", "operator": "<", "target": "70"},
                    ],
                },
            ],
        }
    ]
    if multi_stage:
        stages.append(
            {
                "id": "stage-2",
                "title": "Trade Decision",
                "selected_tools": ["get_price_history"],
                "blocks": [
                    {
                        "id": "b5",
                        "type": "prompt",
                        "text": "Given {{prev_output}}, output BUY/SELL JSON.",
                    }
                ],
            }
        )
    return PushStrategy(name="Chip Tariff Momentum", cadence="1d", stages=stages)


def test_filter_news_rows_enforces_contains_and_point_in_time_recency():
    as_of = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    rows = [
        {
            "article_id": "a1",
            "title": "Trump announces new chips tariff",
            "full_text": "Semiconductor imports affected.",
            "date_published": (as_of - timedelta(hours=12)).isoformat(),
            "tickers": ["NVDA"],
        },
        {
            "article_id": "a2",
            "title": "Future chips leak",
            "full_text": "Published after cutoff",
            "date_published": (as_of + timedelta(hours=1)).isoformat(),
            "tickers": ["NVDA"],
        },
        {
            "article_id": "a3",
            "title": "Old chips news",
            "full_text": "Too old",
            "date_published": (as_of - timedelta(hours=72)).isoformat(),
            "tickers": ["AMD"],
        },
        {
            "article_id": "a4",
            "title": "Corn harvest report",
            "full_text": "Unrelated",
            "date_published": (as_of - timedelta(hours=4)).isoformat(),
            "tickers": [],
        },
    ]
    matched = filter_news_rows(rows, contains=["Trump", "chips"], recency_hours=48, as_of_utc=as_of)
    assert [r["article_id"] for r in matched] == ["a1"]


def test_filter_memory_rows_enforces_contains_recency_category_and_importance():
    as_of = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    rows = [
        {
            "id": "m1",
            "content": "2018 tariff shock hit semis hard",
            "memory_type": "MARKET_EVENT",
            "importance_score": 8,
            "created_at": (as_of - timedelta(hours=24)).isoformat(),
        },
        {
            "id": "m2",
            "content": "Low importance tariff note",
            "memory_type": "MARKET_EVENT",
            "importance_score": 3,
            "created_at": (as_of - timedelta(hours=24)).isoformat(),
        },
        {
            "id": "m3",
            "content": "Wrong category tariff note",
            "memory_type": "LESSON_LEARNED",
            "importance_score": 9,
            "created_at": (as_of - timedelta(hours=24)).isoformat(),
        },
        {
            "id": "m4",
            "content": "Future tariff memory",
            "memory_type": "MARKET_EVENT",
            "importance_score": 9,
            "created_at": (as_of + timedelta(hours=2)).isoformat(),
        },
    ]
    matched = filter_memory_rows(
        rows,
        contains=["tariff"],
        recency_hours=168,
        category="MARKET_EVENT",
        min_importance=6,
        as_of_utc=as_of,
    )
    assert [r["id"] for r in matched] == ["m1"]


def test_hydrate_stage_prompt_renders_all_four_blocks_and_prev_output():
    strategy = _sample_strategy(multi_stage=True)
    as_of = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    news = [
        {
            "article_id": "a1",
            "title": "Trump chips update",
            "full_text": "Details",
            "date_published": (as_of - timedelta(hours=2)).isoformat(),
            "tickers": ["NVDA"],
        }
    ]
    memories = [
        {
            "id": "m1",
            "content": "Tariff volatility pattern",
            "memory_type": "MARKET_EVENT",
            "importance_score": 8,
            "created_at": (as_of - timedelta(hours=5)).isoformat(),
        }
    ]

    p1 = hydrate_stage_prompt(strategy.stages[0], news, memories, as_of)
    assert "Find momentum catalysts." in p1
    assert "Trump chips update" in p1
    assert "Tariff volatility pattern" in p1
    assert "P/E < 35" in p1
    assert "RSI < 70" in p1

    p2 = hydrate_stage_prompt(strategy.stages[1], news, memories, as_of, prev_output="NVDA looks strong")
    assert "NVDA looks strong" in p2


def test_format_technicals_block_handles_empty_rules():
    assert "No technical filters" in format_technicals_block([])


def test_parse_trade_signals_extracts_json_and_text_picks():
    signals = parse_trade_signals('Decision: ```json\n[{"action": "BUY", "ticker": "NVDA"}]\n```')
    assert signals == [{"action": "BUY", "ticker": "NVDA"}]

    text_signals = parse_trade_signals("Recommendation: BUY AAPL and SELL TSLA")
    assert {"action": "BUY", "ticker": "AAPL"} in text_signals
    assert {"action": "SELL", "ticker": "TSLA"} in text_signals


def test_pick_random_two_week_window_returns_up_to_10_trading_days():
    dates = [f"2026-02-{d:02d}" for d in range(1, 29)]
    window = pick_random_two_week_window(dates, rng=random.Random(42))
    assert len(window) == 10
    assert window == sorted(window)


def _mock_sb_client(news_rows, memory_rows, bar_rows):
    client = MagicMock()

    def _table(name: str):
        tbl = MagicMock()
        chain = tbl.select.return_value
        chain.order.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.limit.return_value = chain
        if name == "recipe_news_corpus":
            chain.execute.return_value = MagicMock(data=news_rows)
        elif name == "memories":
            chain.execute.return_value = MagicMock(data=memory_rows)
        elif name == "recipe_intraday_bars":
            chain.execute.return_value = MagicMock(data=bar_rows)
        else:
            chain.execute.return_value = MagicMock(data=[])
        return tbl

    client.table.side_effect = _table
    return client


@pytest.mark.asyncio
async def test_run_push_live_executes_multiple_stages_with_selected_tools():
    strategy = _sample_strategy(multi_stage=True)
    as_of = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    sb = _mock_sb_client(
        news_rows=[
            {
                "article_id": "a1",
                "title": "Trump chips tariff",
                "full_text": "NVDA impacted",
                "date_published": (as_of - timedelta(hours=3)).isoformat(),
                "tickers": ["NVDA"],
            }
        ],
        memory_rows=[
            {
                "id": "m1",
                "content": "Tariff fade setup",
                "memory_type": "MARKET_EVENT",
                "importance_score": 8,
                "created_at": (as_of - timedelta(hours=10)).isoformat(),
            }
        ],
        bar_rows=[],
    )

    calls: list[dict] = []

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        calls.append({"prompt": prompt, "tools": selected_tools, "cutoff": cutoff_date})
        if len(calls) == 1:
            return {"output": "Stage 1 says NVDA", "tool_calls": ["get_technical_indicators(NVDA)"]}
        return {
            "output": '[{"action": "BUY", "ticker": "NVDA"}]',
            "tool_calls": ["get_price_history(NVDA)"],
        }

    result = await run_push_live(strategy, sb, llm_caller=fake_llm, as_of_utc=as_of)

    assert len(result["stages"]) == 2
    assert calls[0]["tools"] == ["get_technical_indicators", "get_key_metrics"]
    assert calls[1]["tools"] == ["get_price_history"]
    assert "Stage 1 says NVDA" in calls[1]["prompt"]
    assert result["signals"] == [{"action": "BUY", "ticker": "NVDA"}]


@pytest.mark.asyncio
async def test_run_push_backtest_runs_random_two_week_window_point_in_time():
    strategy = _sample_strategy(multi_stage=False)
    base_day = datetime(2026, 2, 2, 16, 0, tzinfo=UTC)
    bars = []
    for i in range(20):
        day = base_day + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        bars.append(
            {
                "ticker": "NVDA",
                "bar_time_utc": day.isoformat(),
                "open": 100.0 + i,
                "high": 102.0 + i,
                "low": 99.0 + i,
                "close": 101.0 + i,
                "volume": 1_000_000,
            }
        )

    sb = _mock_sb_client(
        news_rows=[
            {
                "article_id": "a1",
                "title": "Trump chips rally",
                "full_text": "Strong demand",
                "date_published": "2026-02-01T12:00:00+00:00",
                "tickers": ["NVDA"],
            }
        ],
        memory_rows=[],
        bar_rows=bars,
    )

    cutoffs_seen: list[str] = []

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        if cutoff_date:
            cutoffs_seen.append(cutoff_date)
        return {"output": '[{"action": "BUY", "ticker": "NVDA"}]', "tool_calls": []}

    result = await run_push_backtest(strategy, sb, llm_caller=fake_llm, rng=random.Random(7))

    assert len(result["window_dates"]) > 0
    assert len(cutoffs_seen) == len(result["window_dates"])
    assert result["total_return_pct_midpoint"] > 0
    assert result["win_rate_pct"] == 100.0
    assert len(result["trades"]) > 0
