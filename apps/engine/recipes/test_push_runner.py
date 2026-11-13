"""Hermetic TDD tests for the 5-block push-based strategy schema, hydrator, and runner."""

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


def _sample_strategy() -> PushStrategy:
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
    return PushStrategy(name="Chip Tariff Momentum", cadence="1d", stages=stages)


def test_push_strategy_rejects_more_than_one_llm_stage():
    from pydantic import ValidationError

    first = _sample_strategy().stages[0]
    second = first.model_copy(update={"id": "stage-2"})
    with pytest.raises(ValidationError, match="one LLM stage"):
        PushStrategy(name="Two Calls", cadence="1d", stages=[first, second])


def test_push_strategy_rejects_zero_llm_stages():
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="exactly one LLM stage"):
        PushStrategy(name="No Call", cadence="1d", stages=[])


def test_push_strategy_rejects_prev_output_placeholder():
    from pydantic import ValidationError

    from recipes.push_schema import PromptBlock, StrategyStage

    stage = StrategyStage(
        id="stage-1",
        blocks=[PromptBlock(id="b1", type="prompt", text="Given {{prev_output}}, output BUY/SELL JSON.")],
    )
    with pytest.raises(ValidationError, match="prev_output is not available"):
        PushStrategy(name="Two Calls", cadence="1d", stages=[stage])


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
    from recipes.push_schema import PromptBlock, StrategyStage

    strategy = _sample_strategy()
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

    follow_up = StrategyStage(
        id="stage-2",
        blocks=[PromptBlock(id="b5", type="prompt", text="Given {{prev_output}}, output BUY/SELL JSON.")],
    )
    p2 = hydrate_stage_prompt(follow_up, news, memories, as_of, prev_output="NVDA looks strong")
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


def _mock_sb_client(news_rows, memory_rows, price_rows):
    client = MagicMock()

    def _table(name: str):
        tbl = MagicMock()
        chain = tbl.select.return_value
        chain.order.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.limit.return_value = chain
        if name == "recipe_news_corpus":
            chain.execute.return_value = MagicMock(data=news_rows)
        elif name == "memories":
            chain.execute.return_value = MagicMock(data=memory_rows)
        elif name == "price_history":
            chain.execute.return_value = MagicMock(data=price_rows)
        else:
            chain.execute.return_value = MagicMock(data=[])
        return tbl

    client.table.side_effect = _table
    return client


@pytest.mark.asyncio
async def test_run_push_live_makes_exactly_one_llm_call_with_selected_tools():
    strategy = _sample_strategy()
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
        price_rows=[],
    )

    calls: list[dict] = []

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        calls.append({"prompt": prompt, "tools": selected_tools, "cutoff": cutoff_date})
        return {
            "output": '[{"action": "BUY", "ticker": "NVDA"}]',
            "tool_calls": ["get_technical_indicators(NVDA)"],
        }

    result = await run_push_live(strategy, sb, llm_caller=fake_llm, as_of_utc=as_of)

    assert len(calls) == 1
    assert len(result["stages"]) == 1
    assert calls[0]["tools"] == ["get_technical_indicators", "get_key_metrics"]
    assert result["signals"] == [{"action": "BUY", "ticker": "NVDA"}]


@pytest.mark.asyncio
async def test_run_push_backtest_runs_random_two_week_window_point_in_time():
    strategy = _sample_strategy()
    base_day = datetime(2026, 2, 2, 0, 0, tzinfo=UTC)
    prices = []
    for i in range(20):
        day = base_day + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        prices.append(
            {
                "ticker": "NVDA",
                "fetched_at": day.isoformat(),
                "close": 101.0 + i,
                "price": 101.0 + i,
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
        price_rows=prices,
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
    assert "weeks_breakdown" not in result


def test_output_format_block_renders_immutable_schema_section_last():
    from recipes.push_schema import OutputFormatBlock, PromptBlock, StrategyStage

    stage = StrategyStage(
        id="s1",
        blocks=[
            PromptBlock(id="p1", type="prompt", text="Analyze the catalysts."),
            OutputFormatBlock(id="f1", type="output_format"),
        ],
    )
    out = hydrate_stage_prompt(stage, [], [], datetime(2026, 1, 1, tzinfo=UTC))
    assert "Analyze the catalysts." in out
    assert "=== REQUIRED OUTPUT FORMAT ===" in out
    assert '[{"action": "BUY", "ticker": "NVDA"}]' in out
    # Output format section is rendered after the prompt (final instruction).
    assert out.index("=== REQUIRED OUTPUT FORMAT ===") > out.index("Analyze the catalysts.")


def test_parse_trade_signals_still_parses_through_output_format_footer():
    signals = parse_trade_signals(
        "Reasoning here.\n"
        "=== REQUIRED OUTPUT FORMAT ===\n"
        '[{"action": "BUY", "ticker": "NVDA"}]\n'
        'Each object must have exactly "action" and "ticker".'
    )
    assert signals == [{"action": "BUY", "ticker": "NVDA"}]


def test_output_format_block_is_frozen():
    from pydantic import ValidationError

    from recipes.push_schema import OutputFormatBlock

    block = OutputFormatBlock(id="f1", type="output_format")
    with pytest.raises(ValidationError):
        block.type = "prompt"


def test_output_format_block_renders_last_regardless_of_input_order():
    from recipes.push_schema import OutputFormatBlock, PromptBlock, StrategyStage

    stage = StrategyStage(
        id="s1",
        blocks=[
            OutputFormatBlock(id="f1", type="output_format"),
            PromptBlock(id="p1", type="prompt", text="Analyze the catalysts."),
        ],
    )
    out = hydrate_stage_prompt(stage, [], [], datetime(2026, 1, 1, tzinfo=UTC))
    assert out.index("=== REQUIRED OUTPUT FORMAT ===") > out.index("Analyze the catalysts.")
