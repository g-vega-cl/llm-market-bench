"""Hermetic unit tests for the Voxel Recipe Studio timeline backtester."""

from datetime import UTC, datetime, timedelta
from typing import Any

from recipes.backtester import run_recipe_backtest
from recipes.indicators import Bar
from recipes.schema import DAGEdge, DAGNode, RecipeGraph


def _make_bars(n: int = 50, start_price: float = 100.0, price_step: float = 0.5) -> list[Bar]:
    base_time = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    bars = []
    for i in range(n):
        t = base_time + timedelta(minutes=5 * i)
        p = start_price + (i * price_step)
        bars.append(
            Bar(
                time_utc=t,
                open=p - 0.1,
                high=p + 0.3,
                low=p - 0.2,
                close=p,
                volume=2000,
            )
        )
    return bars


def test_pure_technical_backtest_with_target_profit():
    # Price rising by 0.5 per bar: 100, 100.5, 101, ...
    bars = _make_bars(30, start_price=100.0, price_step=0.5)
    recipe = RecipeGraph(
        name="SPY Momentum",
        cadence="5m",
        nodes=[
            DAGNode(
                id="n1",
                type="technical_gate",
                title="RSI Gate",
                config={"conditions": [{"metric": "price", "operator": ">=", "target": 100.0}]},
            ),
            DAGNode(
                id="n2",
                type="risk_output",
                title="Risk Target",
                config={
                    "action": "BUY",
                    "stop_loss_pct": 2.0,
                    "target_profit_pct": 2.0,
                    "max_hold_bars": 10,
                    "exit_on_session_close": True,
                },
            ),
        ],
        edges=[DAGEdge(**{"from": "n1", "to": "n2"})],
    )

    res = run_recipe_backtest(recipe, {"2026-W10": bars})

    assert res["total_trades"] > 0
    assert res["winning_trades"] >= 1
    assert res["total_return_pct_midpoint"] > 0
    # Net return should be slightly less than midpoint return due to slippage
    assert res["total_return_pct_net"] < res["total_return_pct_midpoint"]
    assert len(res["weeks_breakdown"]) == 1
    assert res["weeks_breakdown"][0]["week"] == "2026-W10"


def test_short_circuit_skips_llm_when_technical_fails():
    bars = _make_bars(20, start_price=100.0, price_step=0.1)
    llm_called = False

    def mock_llm(cfg: dict[str, Any], article: dict[str, Any]) -> tuple[str, float]:
        nonlocal llm_called
        llm_called = True
        return "BULLISH", 95.0

    # Gate requires price > 999.0 which will always fail
    recipe = RecipeGraph(
        name="NVDA Impossible Gate",
        cadence="5m",
        nodes=[
            DAGNode(
                id="n1",
                type="news_source",
                title="Semis",
                config={"bucket": "semiconductors", "lookback_hours": 24},
            ),
            DAGNode(
                id="n2",
                type="technical_gate",
                title="Unreachable Price",
                config={"conditions": [{"metric": "price", "operator": ">", "target": 999.0}]},
            ),
            DAGNode(
                id="n3",
                type="classification",
                title="Jev Sentiment",
                config={"target_choice": "BULLISH", "min_confidence": 70.0},
            ),
            DAGNode(id="n4", type="risk_output", title="Risk", config={"action": "BUY"}),
        ],
        edges=[
            DAGEdge(**{"from": "n1", "to": "n3"}),
            DAGEdge(**{"from": "n2", "to": "n3"}),
            DAGEdge(**{"from": "n3", "to": "n4"}),
        ],
    )

    news = [
        {
            "article_id": "art-1",
            "title": "Nvidia announces next-gen Rubin chips",
            "date_published": datetime(2026, 3, 2, 9, 0, tzinfo=UTC),
        }
    ]

    res = run_recipe_backtest(recipe, {"2026-W10": bars}, news_articles=news, llm_evaluator=mock_llm)

    # LLM must NOT have been called due to short circuit
    assert llm_called is False
    assert res["total_trades"] == 0
    assert res["llm_calls_made"] == 0
    assert len(res["skipped_trades"]) > 0
    assert any(s["skip_type"] == "TECHNICAL_BLOCKED" for s in res["skipped_trades"])


def test_llm_rejection_logs_counterfactual_skipped_trade():
    bars = _make_bars(20, start_price=100.0, price_step=0.1)

    def bearish_llm(cfg: dict[str, Any], article: dict[str, Any]) -> tuple[str, float]:
        return "BEARISH", 85.0

    recipe = RecipeGraph(
        name="Catalyst Momentum",
        cadence="5m",
        nodes=[
            DAGNode(id="n1", type="news_source", config={"lookback_hours": 24}),
            DAGNode(
                id="n2",
                type="classification",
                config={"target_choice": "BULLISH", "min_confidence": 70.0},
            ),
            DAGNode(id="n3", type="risk_output", config={"action": "BUY"}),
        ],
        edges=[
            DAGEdge(**{"from": "n1", "to": "n2"}),
            DAGEdge(**{"from": "n2", "to": "n3"}),
        ],
    )

    news = [
        {
            "article_id": "art-bear",
            "title": "Tech stocks slide amid export concerns",
            "date_published": datetime(2026, 3, 2, 9, 15, tzinfo=UTC),
        }
    ]

    res = run_recipe_backtest(recipe, {"2026-W10": bars}, news_articles=news, llm_evaluator=bearish_llm)

    assert res["total_trades"] == 0
    # LLM was queried once and cached for subsequent bars
    assert res["llm_calls_made"] == 1
    assert any(s["skip_type"] == "LLM_REJECTED" for s in res["skipped_trades"])


def test_llm_call_budget_guard():
    bars = _make_bars(30, start_price=100.0, price_step=0.1)

    recipe = RecipeGraph(
        name="Budget Guard Test",
        cadence="5m",
        nodes=[
            DAGNode(id="n1", type="news_source", config={"lookback_hours": 1}),
            DAGNode(id="n2", type="classification", config={"target_choice": "BULLISH"}),
            DAGNode(id="n3", type="risk_output", config={"action": "BUY"}),
        ],
        edges=[
            DAGEdge(**{"from": "n1", "to": "n2"}),
            DAGEdge(**{"from": "n2", "to": "n3"}),
        ],
    )

    # 5 different articles published at different times
    news = [
        {
            "article_id": f"art-{i}",
            "title": f"Catalyst {i}",
            "date_published": datetime(2026, 3, 2, 9, 30 + (5 * i), tzinfo=UTC),
        }
        for i in range(5)
    ]

    # Max calls set to 2
    res = run_recipe_backtest(
        recipe,
        {"2026-W10": bars},
        news_articles=news,
        max_llm_calls=2,
    )

    assert res["llm_calls_made"] <= 2
    assert any(s["skip_type"] == "BUDGET_EXCEEDED" for s in res["skipped_trades"])


def test_short_selling_target_profit_and_return_math():
    # Price dropping: 100, 99.5, 99.0, 98.5, 98.0 ...
    bars = _make_bars(20, start_price=100.0, price_step=-0.5)
    recipe = RecipeGraph(
        name="Short Trend",
        cadence="5m",
        nodes=[
            DAGNode(
                id="n1",
                type="technical_gate",
                config={"conditions": [{"metric": "price", "operator": "<=", "target": 100.0}]},
            ),
            DAGNode(
                id="n2",
                type="risk_output",
                config={
                    "action": "SELL",
                    "stop_loss_pct": 2.0,
                    "target_profit_pct": 2.0,
                    "max_hold_bars": 10,
                },
            ),
        ],
        edges=[DAGEdge(**{"from": "n1", "to": "n2"})],
    )

    res = run_recipe_backtest(recipe, {"2026-W10": bars})
    assert res["total_trades"] > 0
    trade = res["trades"][0]
    assert trade["action"] == "SELL"
    # Falling price should yield positive profit on short
    assert trade["pnl_midpoint"] > 0
    assert trade["return_pct_midpoint"] > 0
    # Formula check: ((entry - exit) / entry) * 100
    expected_ret = round(((trade["entry_price"] - trade["exit_price"]) / trade["entry_price"]) * 100.0, 2)
    assert abs(trade["return_pct_midpoint"] - expected_ret) < 0.05


def test_conservative_exit_triggers_stop_loss_on_dual_breach():
    # Entry at 100 on bar 0. Bar 1 has wild wick: high 105 (breaches +2% target), low 95 (breaches -2% stop)
    t0 = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    t1 = datetime(2026, 3, 2, 9, 35, tzinfo=UTC)
    bars = [
        Bar(time_utc=t0, open=100.0, high=100.1, low=99.9, close=100.0, volume=1000),
        Bar(time_utc=t1, open=100.0, high=105.0, low=95.0, close=101.0, volume=5000),
    ]

    recipe = RecipeGraph(
        name="Conservative Test",
        cadence="5m",
        nodes=[
            DAGNode(
                id="n1",
                type="technical_gate",
                config={"conditions": [{"metric": "price", "operator": ">=", "target": 99.0}]},
            ),
            DAGNode(
                id="n2",
                type="risk_output",
                config={"action": "BUY", "stop_loss_pct": 2.0, "target_profit_pct": 2.0},
            ),
        ],
        edges=[DAGEdge(**{"from": "n1", "to": "n2"})],
    )

    res = run_recipe_backtest(recipe, {"2026-W10": bars})
    assert res["total_trades"] == 1
    assert res["trades"][0]["exit_reason"] == "STOP_LOSS"


def test_news_bucket_filtering():
    bars = _make_bars(10, start_price=100.0, price_step=0.1)
    recipe = RecipeGraph(
        name="Semis Only",
        cadence="5m",
        nodes=[
            DAGNode(
                id="n1",
                type="news_source",
                config={"bucket": "semiconductors", "lookback_hours": 24},
            ),
            DAGNode(id="n2", type="risk_output", config={"action": "BUY"}),
        ],
        edges=[DAGEdge(**{"from": "n1", "to": "n2"})],
    )

    # News with energy bucket only
    news = [
        {
            "article_id": "oil-1",
            "title": "Crude oil spikes on OPEC supply curb",
            "date_published": datetime(2026, 3, 2, 9, 0, tzinfo=UTC),
            "buckets": ["energy"],
            "tickers": ["XOM"],
        }
    ]

    res = run_recipe_backtest(recipe, {"2026-W10": bars}, news_articles=news)
    # Energy news must not trigger semiconductor recipe
    assert res["total_trades"] == 0
    assert any(s["skip_type"] == "NO_CATALYST" for s in res["skipped_trades"])
