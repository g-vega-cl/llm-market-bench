"""Hermetic TDD tests for the 5-block push-based strategy schema, hydrator, and runner."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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
    base_day = datetime(2026, 3, 2, 0, 0, tzinfo=UTC)
    prices = []
    bars = []
    for i in range(14):
        day = base_day + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        day_iso = day.date().isoformat()
        prices.append({"ticker": "NVDA", "fetched_at": day.isoformat(), "close": 100.0 + i, "price": 100.0 + i})
        for h_offset, px in ((13, 100.0 + i), (16, 101.0 + i), (19, 102.0 + i)):
            bars.append(
                {
                    "ticker": "NVDA",
                    "bar_time_utc": f"{day_iso}T{h_offset:02d}:30:00+00:00",
                    "open": px,
                    "high": px + 1.0,
                    "low": px - 1.0,
                    "close": px,
                    "volume": 100,
                    "source": "fmp",
                }
            )

    sb = _mock_sb_client(
        news_rows=[
            {
                "article_id": "a1",
                "title": "Trump chips rally",
                "full_text": "Strong demand",
                "date_published": "2026-03-01T12:00:00+00:00",
                "tickers": ["NVDA"],
            }
        ],
        memory_rows=[],
        price_rows=prices,
    )

    cutoffs_seen: list[str] = []
    prompts_seen: list[str] = []

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        if cutoff_date:
            cutoffs_seen.append(cutoff_date)
        prompts_seen.append(prompt)
        if len(prompts_seen) == 1:
            return {"output": '[{"action": "BUY", "ticker": "NVDA"}]', "tool_calls": []}
        if len(prompts_seen) == 5:
            return {"output": '[{"action": "EXIT", "ticker": "NVDA"}]', "tool_calls": []}
        return {"output": "[]", "tool_calls": []}

    with patch(
        "recipes.push_runner.fetch_intraday_bars_for_ticker", new=MagicMock(side_effect=AsyncMock(return_value=bars))
    ):
        result = await run_push_backtest(strategy, sb, llm_caller=fake_llm, rng=random.Random(7))

    # 10 trading days expanded to 30 ET slots (09:30, 12:30, 15:30 ET)
    assert len(result["window_dates"]) == 30
    assert result["window_dates"][0].endswith("09:30 ET")
    assert result["window_dates"][1].endswith("12:30 ET")
    assert result["window_dates"][2].endswith("15:30 ET")
    assert len(cutoffs_seen) == 30
    # Turn 2 saw the open NVDA position injected into its prompt!
    assert "NVDA:" in prompts_seen[1]
    assert result["total_trades"] == 1
    assert result["trades"][0]["exit_reason"] == "SIGNAL_EXIT"
    assert result["total_return_pct_midpoint"] > 0
    assert result["win_rate_pct"] == 100.0
    assert "weeks_breakdown" not in result


@pytest.mark.asyncio
async def test_run_push_backtest_emits_incremental_progress_checkpoints():
    strategy = _sample_strategy()
    base_day = datetime(2026, 3, 2, 0, 0, tzinfo=UTC)
    prices = []
    for i in range(6):
        day = base_day + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        prices.append({"ticker": "NVDA", "fetched_at": day.isoformat(), "close": 101.0 + i, "price": 101.0 + i})

    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=prices)

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        if cutoff_date == "2026-03-02" and "Open Positions: None" in prompt:
            return {
                "output": '[{"action": "BUY", "ticker": "NVDA"}]',
                "tool_calls": [f'get_technical_indicators({{"ticker": "NVDA", "cutoff": "{cutoff_date}"}})'],
            }
        return {"output": "[]", "tool_calls": []}

    checkpoints: list[tuple[int, dict]] = []

    def capture_progress(pct: int, partial: dict) -> None:
        checkpoints.append((pct, partial))

    bars = [
        {
            "ticker": "NVDA",
            "bar_time_utc": f"{row['fetched_at'][:10]}T14:30:00+00:00",
            "open": row["price"],
            "close": row["price"],
        }
        for row in prices
    ]
    with patch(
        "recipes.push_runner.fetch_intraday_bars_for_ticker", new=MagicMock(side_effect=AsyncMock(return_value=bars))
    ):
        result = await run_push_backtest(
            strategy,
            sb,
            llm_caller=fake_llm,
            rng=random.Random(7),
            on_progress=capture_progress,
        )

    total_slots = len(result["window_dates"])
    assert len(checkpoints) == 1 + total_slots

    init_pct, init_payload = checkpoints[0]
    assert init_pct == 10
    assert init_payload["days_completed"] == 0
    assert init_payload["total_days"] == total_slots
    assert init_payload["day_steps"] == []

    prev_pct = init_pct
    for idx in range(total_slots):
        pct, payload = checkpoints[idx + 1]
        assert pct >= prev_pct
        prev_pct = pct
        assert payload["days_completed"] == idx + 1
        assert len(payload["day_steps"]) == idx + 1
        assert payload["day_steps"][-1]["day"] == result["window_dates"][idx]
        assert len(payload["equity_curve"]) == idx + 1

    # Held across window and settled at END_OF_WINDOW on final slot
    assert len(result["trades"]) == 1
    assert result["trades"][0]["exit_reason"] == "END_OF_WINDOW"
    assert result["days_completed"] == total_slots


@pytest.mark.asyncio
async def test_run_push_backtest_supports_async_on_progress_callback():
    strategy = _sample_strategy()
    base_day = datetime(2026, 3, 2, 0, 0, tzinfo=UTC)
    prices = [
        {
            "ticker": "SPY",
            "fetched_at": (base_day + timedelta(days=i)).isoformat(),
            "close": 500.0 + i,
            "price": 500.0 + i,
        }
        for i in range(4)
    ]
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=prices)
    seen: list[int] = []

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        return {"output": "HOLD", "tool_calls": []}

    async def async_progress(pct: int, partial: dict) -> None:
        seen.append(pct)

    bars = [
        {
            "ticker": "NVDA",
            "bar_time_utc": f"{row['fetched_at'][:10]}T14:30:00+00:00",
            "open": row["price"],
            "close": row["price"],
        }
        for row in prices
    ]
    with patch(
        "recipes.push_runner.fetch_intraday_bars_for_ticker", new=MagicMock(side_effect=AsyncMock(return_value=bars))
    ):
        result = await run_push_backtest(
            strategy,
            sb,
            llm_caller=fake_llm,
            rng=random.Random(1),
            on_progress=async_progress,
        )

    assert len(seen) == 1 + len(result["window_dates"])
    assert seen[0] == 10


def test_parse_trade_signals_supports_exit_json_and_text():
    assert parse_trade_signals('[{"action": "EXIT", "ticker": "nvda"}]') == [{"action": "EXIT", "ticker": "NVDA"}]
    assert parse_trade_signals("EXIT AMZN now") == [{"action": "EXIT", "ticker": "AMZN"}]


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


@pytest.mark.asyncio
async def test_run_push_backtest_caches_unknown_tickers_across_days(monkeypatch):
    strategy = _sample_strategy()
    news_rows = []
    memory_rows = []
    price_rows = [{"date": f"2026-03-{d:02d}", "ticker": "SPY", "close": 500.0} for d in range(1, 5)]
    sb = _mock_sb_client(news_rows, memory_rows, price_rows)

    fetch_calls = []
    from recipes import push_runner as pr

    def _spy_load_closes(client, tickers, start_day, end_day):
        fetch_calls.append(set(tickers))
        return {}

    monkeypatch.setattr(pr, "_load_daily_closes", _spy_load_closes)
    monkeypatch.setattr(pr, "fetch_intraday_bars_for_ticker", AsyncMock(return_value=[]))

    async def _llm(prompt: str, tools: list[str], sim_date: str | None = None):
        return {"output": '[{"action": "BUY", "ticker": "GHOST"}]', "tool_calls": []}

    result = await run_push_backtest(strategy, sb, llm_caller=_llm, rng=random.Random(1))
    assert result["total_days"] == 30
    assert fetch_calls == [{"GHOST"}]


@pytest.mark.asyncio
async def test_run_push_live_injects_held_positions_and_returns_updated_portfolio():
    strategy = _sample_strategy()
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=[])
    recipe_row = {
        "id": "rec-live-1",
        "concurrency_config": {"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
        "paper_cash": 7500.0,
        "paper_positions": [
            {
                "ticker": "NVDA",
                "side": "LONG",
                "shares": 25.0,
                "entry_price": 100.0,
                "entry_time": "2026-04-06 09:30 ET",
                "cost_basis": 2500.0,
            }
        ],
        "paper_trades": [],
        "paper_equity_curve": [],
    }
    captured_prompts: list[str] = []

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        captured_prompts.append(prompt)
        return {"output": '[{"action": "EXIT", "ticker": "NVDA"}]', "tool_calls": []}

    with patch("recipes.push_runner._resolve_live_prices", new=AsyncMock(return_value={"NVDA": 110.0})):
        res = await run_push_live(
            strategy,
            sb,
            llm_caller=fake_llm,
            as_of_utc=datetime(2026, 4, 7, 13, 30, tzinfo=UTC),
            recipe_row=recipe_row,
        )

    assert "NVDA: 25 shares" in captured_prompts[0]
    assert res["updated_portfolio"]["paper_positions"] == []
    assert len(res["updated_portfolio"]["paper_trades"]) == 1
    assert res["updated_portfolio"]["paper_cash"] > 10200.0


@pytest.mark.asyncio
async def test_run_push_live_mirrors_fills_and_stamps_open_positions():
    """Wiring check: a live BUY must reach the broker mirror and carry its order id back."""
    strategy = _sample_strategy()
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=[])
    recipe_row = {
        "id": "0773afba-948e-4b11-a445-1d39934839ad",
        "concurrency_config": {"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
        "paper_cash": 10000.0,
        "paper_positions": [],
        "paper_trades": [],
        "paper_equity_curve": [],
    }

    class FakeBroker:
        def __init__(self) -> None:
            self.orders = []

        def get_open_position(self, ticker: str):
            raise RuntimeError("flat")

        def submit_order(self, request):
            self.orders.append(request)
            return type("Order", (), {"id": "alpaca-order-1"})()

    broker = FakeBroker()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("recipes.alpaca_mirror._build_client", lambda: broker)

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        return {"output": '[{"action": "BUY", "ticker": "DIS"}]', "tool_calls": []}

    try:
        with patch("recipes.push_runner._resolve_live_prices", new=AsyncMock(return_value={"DIS": 122.04})):
            res = await run_push_live(
                strategy,
                sb,
                llm_caller=fake_llm,
                as_of_utc=datetime(2026, 11, 19, 14, 30, tzinfo=UTC),
                recipe_row=recipe_row,
            )
    finally:
        monkeypatch.undo()

    assert len(broker.orders) == 1
    assert broker.orders[0].symbol == "DIS"
    assert broker.orders[0].qty == 20
    assert broker.orders[0].client_order_id == "recipe-0773afba__DIS__BUY__20261119T143000Z"
    assert res["alpaca_fills"][0]["status"] == "SUBMITTED"
    assert res["updated_portfolio"]["paper_positions"][0]["alpaca_order_id"] == "alpaca-order-1"


@pytest.mark.asyncio
async def test_run_push_live_and_backtest_propagate_full_trace_and_prompt():
    strategy = _sample_strategy()
    prices = [{"date": f"2026-03-{d:02d}", "ticker": "SPY", "close": 500.0} for d in range(1, 15)]
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=prices)
    sample_trace = {
        "rounds": [
            {
                "round": 1,
                "reasoning": "Checking NVDA price",
                "assistant_text": "",
                "tool_calls": [{"name": "get_stock_quote", "args": {"ticker": "NVDA"}, "result": "$100.00"}],
            }
        ],
        "forced_final_synthesis": False,
    }

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        return {"output": "[]", "tool_calls": ['get_stock_quote({"ticker": "NVDA"})'], "trace": sample_trace}

    with patch("recipes.push_runner._resolve_live_prices", new=AsyncMock(return_value={})):
        live_res = await run_push_live(
            strategy,
            sb,
            llm_caller=fake_llm,
            as_of_utc=datetime(2026, 4, 7, 13, 30, tzinfo=UTC),
        )
    assert live_res["stages"][0]["trace"] == sample_trace

    bars = [
        {"ticker": "SPY", "bar_time_utc": f"{row['date'][:10]}T14:30:00+00:00", "open": 500.0, "close": 500.0}
        for row in prices
    ]
    with patch(
        "recipes.push_runner.fetch_intraday_bars_for_ticker", new=MagicMock(side_effect=AsyncMock(return_value=bars))
    ):
        bt_res = await run_push_backtest(strategy, sb, llm_caller=fake_llm, rng=random.Random(1))
    assert bt_res["day_steps"][0]["trace"] == sample_trace
    assert "Find momentum catalysts." in bt_res["day_steps"][0]["prompt"]


@pytest.mark.asyncio
async def test_run_push_live_enriches_open_positions_and_preserves_equity_identity():
    strategy = _sample_strategy()
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=[])

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        return {"output": '[{"action": "BUY", "ticker": "NVDA"}]', "tool_calls": []}

    with patch("recipes.push_runner._resolve_live_prices", new=AsyncMock(return_value={"NVDA": 200.0})):
        res = await run_push_live(
            strategy,
            sb,
            llm_caller=fake_llm,
            as_of_utc=datetime(2026, 4, 7, 13, 30, tzinfo=UTC),
        )

    pos = res["updated_portfolio"]["paper_positions"][0]
    assert pos["current_price"] == 200.0
    assert "market_value" in pos
    assert "unrealized_pnl_net" in pos
    total_eq = res["updated_portfolio"]["paper_cash"] + pos["market_value"]
    latest_curve_eq = res["updated_portfolio"]["paper_equity_curve"][-1]["equity"]
    assert abs(total_eq - latest_curve_eq) < 0.05


@pytest.mark.asyncio
async def test_run_push_backtest_refreshes_partial_intraday_bars_on_later_slot_days():
    """If early slot fetch returned only Day 1 bars, later slot days must refresh instead of falling back to prior daily close."""
    strategy = _sample_strategy()
    prices = [
        {"ticker": "SPY", "fetched_at": "2026-03-02T00:00:00+00:00", "close": 500.0, "price": 500.0},
        {"ticker": "SPY", "fetched_at": "2026-03-03T00:00:00+00:00", "close": 502.0, "price": 502.0},
        {"ticker": "NVDA", "fetched_at": "2026-03-02T00:00:00+00:00", "close": 100.0, "price": 100.0},
        {"ticker": "NVDA", "fetched_at": "2026-03-03T00:00:00+00:00", "close": 250.0, "price": 250.0},
    ]
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=prices)

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        if cutoff_date == "2026-03-02" and "Open Positions: None" in prompt:
            return {"output": '[{"action": "BUY", "ticker": "NVDA"}]', "tool_calls": []}
        if cutoff_date == "2026-03-03":
            return {"output": '[{"action": "EXIT", "ticker": "NVDA"}]', "tool_calls": []}
        return {"output": "[]", "tool_calls": []}

    fetch_calls = []

    async def partial_then_full(sb_client, tkr, start_day, end_day):
        fetch_calls.append((tkr, start_day, end_day))
        if len(fetch_calls) == 1:
            return [{"ticker": "NVDA", "bar_time_utc": "2026-03-02T14:30:00+00:00", "open": 100.0, "close": 100.0}]
        return [{"ticker": "NVDA", "bar_time_utc": "2026-03-03T14:30:00+00:00", "open": 250.0, "close": 250.0}]

    with patch("recipes.push_runner.fetch_intraday_bars_for_ticker", side_effect=partial_then_full):
        res = await run_push_backtest(strategy, sb, llm_caller=fake_llm, rng=random.Random(1))

    assert res["trades"][0]["exit_price"] == 250.0
    assert len(fetch_calls) >= 2


@pytest.mark.asyncio
async def test_run_push_backtest_stops_early_when_cancelled():
    strategy = _sample_strategy()
    prices = [
        {"ticker": "SPY", "fetched_at": "2026-03-02T00:00:00+00:00", "close": 500.0, "price": 500.0},
        {"ticker": "SPY", "fetched_at": "2026-03-03T00:00:00+00:00", "close": 502.0, "price": 502.0},
    ]
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=prices)
    calls = 0

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        nonlocal calls
        calls += 1
        return {"output": "[]", "tool_calls": []}

    res = await run_push_backtest(
        strategy,
        sb,
        llm_caller=fake_llm,
        rng=random.Random(1),
        is_cancelled=lambda: calls >= 2,
    )

    assert calls == 2
    assert res["days_completed"] == 2
    assert res.get("cancelled") is True


@pytest.mark.asyncio
async def test_run_push_backtest_refreshes_same_day_later_slot_when_earlier_slot_incomplete():
    """If 09:30 ET fetch only held 09:30 bar, 12:30 ET on the SAME day must still refresh."""
    strategy = _sample_strategy()
    prices = [
        {"ticker": "SPY", "fetched_at": "2026-03-02T00:00:00+00:00", "close": 500.0, "price": 500.0},
        {"ticker": "NVDA", "fetched_at": "2026-03-02T00:00:00+00:00", "close": 100.0, "price": 100.0},
    ]
    sb = _mock_sb_client(news_rows=[], memory_rows=[], price_rows=prices)
    turn = 0
    fetch_calls = 0

    async def fake_llm(prompt: str, selected_tools: list[str], cutoff_date: str | None) -> dict:
        nonlocal turn
        turn += 1
        if turn == 1:
            return {"output": '[{"action": "BUY", "ticker": "NVDA"}]', "tool_calls": []}
        if turn == 2:
            return {"output": '[{"action": "EXIT", "ticker": "NVDA"}]', "tool_calls": []}
        return {"output": "[]", "tool_calls": []}

    async def progressive_fetch(sb_client, tkr, start_day, end_day):
        nonlocal fetch_calls
        fetch_calls += 1
        if fetch_calls == 1:
            return [{"ticker": "NVDA", "bar_time_utc": "2026-03-02T14:30:00+00:00", "open": 100.0, "close": 100.0}]
        return [{"ticker": "NVDA", "bar_time_utc": "2026-03-02T17:30:00+00:00", "open": 125.0, "close": 125.0}]

    with patch("recipes.push_runner.fetch_intraday_bars_for_ticker", side_effect=progressive_fetch):
        res = await run_push_backtest(strategy, sb, llm_caller=fake_llm, rng=random.Random(1))

    assert fetch_calls >= 2
    assert res["trades"][0]["exit_price"] == 125.0
