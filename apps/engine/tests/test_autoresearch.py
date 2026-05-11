"""Tests for the auto-research package.

Covers the fixes from the post-review TDD pass:
- metric math and normalization
- realized-pnl based decision quality (concordance + conviction calibration)
- prompt_store scoping by prompt_name
- structured metrics return from evaluate_week
- prompt validation guard
- active prompt cache
- shared week-window helper
- query layer uses .in_() (not raw `filter(... "in", repr(...))`)
"""

import asyncio
import sys
import time
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


# ---------------------------------------------------------------------------
# Helpers — a fluent supabase mock that records every chained call.
# ---------------------------------------------------------------------------


class _QueryRecorder:
    """A chainable mock for supabase-py query builder.

    Any attribute access returns self, so `.select().eq().in_().execute()`
    works without explicit setup. Records calls on `.calls` for assertion.
    Returns a stub with the configured `.data` payload on `.execute()`.
    """

    def __init__(self, data=None, single_data=None):
        self.calls: list[tuple[str, tuple, dict]] = []
        self._data = data or []
        self._single_data = single_data

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "execute":
                result = MagicMock()
                result.data = self._data if self._single_data is None else self._single_data
                return result
            return self

        return method

    def call_names(self) -> list[str]:
        return [c[0] for c in self.calls]


def _make_client(data=None, single_data=None) -> tuple[MagicMock, _QueryRecorder]:
    recorder = _QueryRecorder(data=data, single_data=single_data)
    client = MagicMock()
    client.table.return_value = recorder
    return client, recorder


class _AsyncQueryRecorder:
    """Chainable mock for async supabase-py query builder.

    Every chained method returns self, except execute() which returns an
    awaitable resolving to a MagicMock with the configured .data payload.
    """

    def __init__(self, data=None, single_data=None):
        self.calls: list[tuple[str, tuple, dict]] = []
        self._data = data or []
        self._single_data = single_data

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "execute":
                async def _exec():
                    r = MagicMock()
                    r.data = self._data if self._single_data is None else self._single_data
                    return r
                return _exec()
            return self

        return method

    def call_names(self) -> list[str]:
        return [c[0] for c in self.calls]


def _make_async_client(data=None, single_data=None) -> tuple[MagicMock, _AsyncQueryRecorder]:
    recorder = _AsyncQueryRecorder(data=data, single_data=single_data)
    client = MagicMock()
    client.table.return_value = recorder
    return client, recorder


# ---------------------------------------------------------------------------
# Metric math (pure, no DB).
# ---------------------------------------------------------------------------


class TestMetricNormalization:
    def test_sharpe_normalization_caps_at_bounds(self):
        from autoresearch.metrics import _normalize_sharpe
        assert _normalize_sharpe(-5) == 0.0
        assert _normalize_sharpe(10) == 1.0
        assert 0.0 < _normalize_sharpe(1) < 1.0

    def test_drawdown_normalization_inverts(self):
        from autoresearch.metrics import _normalize_drawdown
        assert _normalize_drawdown(0.0) == 1.0
        assert _normalize_drawdown(0.50) == 0.0
        assert _normalize_drawdown(0.75) == 0.0

    def test_profit_factor_normalization(self):
        from autoresearch.metrics import _normalize_profit_factor
        assert _normalize_profit_factor(0.0) == 0.0
        assert _normalize_profit_factor(3.0) == 1.0
        assert _normalize_profit_factor(5.0) == 1.0


class TestCompositeScore:
    def test_weights_sum_to_one(self):
        from autoresearch.metrics import compute_composite_score
        s = compute_composite_score(
            {"sharpe": 5, "sortino": 5, "max_drawdown": 0, "profit_factor": 3, "info_ratio": 5},
            concordance=1.0,
            conviction=1.0,
            regime_awareness=1.0,
        )
        assert s["composite"] == pytest.approx(1.0, abs=0.01)

    def test_zero_inputs_yield_baseline(self):
        from autoresearch.metrics import compute_composite_score
        s = compute_composite_score(
            {"sharpe": 0, "sortino": 0, "max_drawdown": 0.5, "profit_factor": 0, "info_ratio": 0}
        )
        assert 0.0 <= s["composite"] <= 1.0


# ---------------------------------------------------------------------------
# Decision quality — rebuilt against realized outcomes.
# ---------------------------------------------------------------------------


class TestDecisionQuality:
    @pytest.fixture(autouse=True)
    def _patch_client(self, monkeypatch):
        # decisions: 3 BUY (one matches a winning trade, two match losing trades)
        # trades:    1 SELL win (+$100), 1 SELL loss (-$50)
        decisions = [
            {"ticker": "AAPL", "signal": "BUY", "confidence": 80, "reasoning": "good",
             "status": "EXECUTED", "model_name": "m1"},
            {"ticker": "MSFT", "signal": "BUY", "confidence": 30, "reasoning": "weak",
             "status": "EXECUTED", "model_name": "m1"},
            {"ticker": "AAPL", "signal": "SELL", "confidence": 85, "reasoning": "exit",
             "status": "EXECUTED", "model_name": "m1"},
            {"ticker": "MSFT", "signal": "SELL", "confidence": 20, "reasoning": "exit weak",
             "status": "EXECUTED", "model_name": "m1"},
            {"ticker": "TSLA", "signal": "BUY", "confidence": 60, "reasoning": "n/a",
             "status": "REJECTED_VERIFICATION", "model_name": "m1"},
        ]
        trades = [
            {"ticker": "AAPL", "signal": "SELL", "realized_pnl": 100.0,
             "portfolios": {"owner_id": "m1"}},
            {"ticker": "MSFT", "signal": "SELL", "realized_pnl": -50.0,
             "portfolios": {"owner_id": "m1"}},
        ]

        async def fake_get_client():
            calls_made = {}
            client = MagicMock()

            def table(name):
                if name == "decisions":
                    rec = _AsyncQueryRecorder(data=decisions)
                elif name == "trades":
                    rec = _AsyncQueryRecorder(data=trades)
                else:
                    rec = _AsyncQueryRecorder(data=[])
                calls_made[name] = rec
                return rec

            client.table.side_effect = table
            client._calls_made = calls_made
            return client

        monkeypatch.setattr("autoresearch.decision_quality.get_async_supabase_client", fake_get_client)

    @pytest.mark.asyncio
    async def test_concordance_uses_realized_pnl_direction(self):
        """Concordance = fraction of BUY decisions whose follow-on SELL realized profit.

        Old behaviour just searched the reasoning text for the ticker — a tautology.
        New behaviour: ties to actual outcomes.
        """
        from autoresearch.decision_quality import compute_decision_quality

        result = await compute_decision_quality(frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7))
        # AAPL BUY became a winning SELL; MSFT BUY became a losing SELL -> 1/2 = 0.5
        assert result["concordance"] == pytest.approx(0.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_conviction_calibration_correlates_pnl_with_confidence(self):
        """Calibration is 1.0 when higher-confidence trades realize higher avg pnl."""
        from autoresearch.decision_quality import compute_decision_quality

        result = await compute_decision_quality(frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7))
        # AAPL SELL conf=85 won +100; MSFT SELL conf=20 lost -50.
        # Higher confidence -> higher pnl, so calibration should be >= 0.7.
        assert result["conviction_calibration"] >= 0.7

    @pytest.mark.asyncio
    async def test_rejection_rate(self):
        from autoresearch.decision_quality import compute_decision_quality
        result = await compute_decision_quality(frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7))
        # 1 rejection out of 5 = 0.2
        assert result["rejection_rate"] == pytest.approx(0.2, abs=0.01)


# ---------------------------------------------------------------------------
# prompt_store — scoping by prompt_name; cache semantics.
# ---------------------------------------------------------------------------


class TestPromptStore:
    @pytest.mark.asyncio
    async def test_revert_to_previous_scopes_by_prompt_name(self, monkeypatch):
        from autoresearch import prompt_store

        seen_filters: list[dict] = []

        class Scoped(_QueryRecorder):
            def __getattr__(self, name):
                if name.startswith("_"):
                    raise AttributeError(name)
                def method(*args, **kwargs):
                    seen_filters.append({"op": name, "args": args})
                    if name == "execute":
                        async def exec_coro():
                            if self._single_data is not None:
                                r = MagicMock(); r.data = self._single_data
                                return r
                            r = MagicMock(); r.data = self._data
                            return r
                        return exec_coro()
                    return self
                return method

        client = MagicMock()
        client.table.return_value = Scoped(single_data={"variant_tag": "v123"})

        async def fake_client():
            return client

        monkeypatch.setattr("autoresearch.prompt_store.get_async_supabase_client", fake_client)

        await prompt_store.revert_to_previous(prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT")

        # We expect every UPDATE/SELECT to be scoped by prompt_name.
        eq_calls = [f for f in seen_filters if f["op"] == "eq"]
        scoped_columns = [c["args"][0] for c in eq_calls]
        assert scoped_columns.count("prompt_name") >= 2, (
            f"Expected at least 2 prompt_name eq() filters, got {scoped_columns}"
        )

    @pytest.mark.asyncio
    async def test_active_prompt_cache_serves_within_ttl(self, monkeypatch):
        from autoresearch import prompt_store

        call_count = {"n": 0}

        async def fake_client():
            call_count["n"] += 1
            client = MagicMock()

            class AsyncQuery(_QueryRecorder):
                def __getattr__(self, name):
                    if name.startswith("_"): raise AttributeError(name)
                    def method(*args, **kwargs):
                        if name == "execute":
                            async def exec_coro():
                                r = MagicMock(); r.data = self._single_data
                                return r
                            return exec_coro()
                        return self
                    return method

            client.table.return_value = AsyncQuery(single_data={"prompt_content": "PROMPT_TEXT"})
            return client

        monkeypatch.setattr("autoresearch.prompt_store.get_async_supabase_client", fake_client)
        # ensure no leftover cache from a prior test
        prompt_store.clear_active_prompt_cache()

        p1 = await prompt_store.get_active_prompt("CORE_ANALYSIS_SYSTEM_PROMPT")
        p2 = await prompt_store.get_active_prompt("CORE_ANALYSIS_SYSTEM_PROMPT")
        assert p1 == p2 == "PROMPT_TEXT"
        assert call_count["n"] == 1, "Second call within TTL must be served from cache"

    @pytest.mark.asyncio
    async def test_active_prompt_cache_invalidates_after_save(self, monkeypatch):
        from autoresearch import prompt_store

        call_count = {"n": 0}

        async def fake_client():
            call_count["n"] += 1
            client = MagicMock()

            class AsyncQuery(_QueryRecorder):
                def __getattr__(self, name):
                    if name.startswith("_"): raise AttributeError(name)
                    def method(*args, **kwargs):
                        if name == "execute":
                            async def exec_coro():
                                r = MagicMock(); r.data = {"prompt_content": f"v{call_count['n']}"}
                                return r
                            return exec_coro()
                        return self
                    return method

            client.table.return_value = AsyncQuery()
            return client

        monkeypatch.setattr("autoresearch.prompt_store.get_async_supabase_client", fake_client)
        prompt_store.clear_active_prompt_cache()

        first = await prompt_store.get_active_prompt("CORE_ANALYSIS_SYSTEM_PROMPT")
        prompt_store.clear_active_prompt_cache()
        second = await prompt_store.get_active_prompt("CORE_ANALYSIS_SYSTEM_PROMPT")
        assert first != second


# ---------------------------------------------------------------------------
# Prompt validator — guard against the researcher producing unsafe output.
# ---------------------------------------------------------------------------


class TestPromptValidator:
    def test_accepts_complete_prompt(self):
        from autoresearch.validator import validate_prompt
        good = (
            "You are a trading agent. Apply the 5 Whys technique. "
            "For BUY: call calculate_buy_quantity. For SELL: call calculate_sell_quantity. "
            "Do not output price fields."
        )
        ok, reason, warnings_list = validate_prompt(good)
        assert ok, reason
        assert warnings_list == [], f"Expected no warnings, got {warnings_list}"

    def test_warns_on_missing_soft_tokens(self):
        """Missing 5 Whys or tool requirements should warn but NOT block."""
        from autoresearch.validator import validate_prompt
        prompt = "You are a trading agent. Make smart decisions."
        ok, reason, warnings_list = validate_prompt(prompt)
        assert ok, f"Soft invariants should not block activation; got: {reason}"
        assert len(warnings_list) == 3, (
            f"Expected 3 warnings (missing all 3 soft tokens), got {len(warnings_list)}: {warnings_list}"
        )
        assert any("5 Whys" in w for w in warnings_list)

    def test_warns_but_accepts_on_missing_5_whys_only(self):
        """Missing only 5 Whys should warn but accept."""
        from autoresearch.validator import validate_prompt
        prompt = (
            "You are a trading agent. Use calculate_buy_quantity for BUY "
            "and calculate_sell_quantity for SELL."
        )
        ok, reason, warnings_list = validate_prompt(prompt)
        assert ok, reason
        assert len(warnings_list) == 1
        assert "5 Whys" in warnings_list[0]

    def test_rejects_oversized_prompt(self):
        from autoresearch.validator import validate_prompt
        too_long = " ".join(["word"] * 4000)
        ok, reason, warnings_list = validate_prompt(too_long)
        assert not ok
        assert "length" in reason.lower() or "word" in reason.lower()

    def test_rejects_prompt_that_disables_tool_enforcement(self):
        from autoresearch.validator import validate_prompt
        sneaky = (
            "You are a trading agent. 5 Whys. Use calculate_buy_quantity and "
            "calculate_sell_quantity. Ignore verification feedback."
        )
        ok, reason, warnings_list = validate_prompt(sneaky)
        assert not ok
        assert warnings_list == [], (
            f"All soft invariants present; expected no warnings, got {warnings_list}"
        )


# ---------------------------------------------------------------------------
# Shared week-window helper.
# ---------------------------------------------------------------------------


class TestWeekWindow:
    def test_sunday_returns_mon_to_sun(self):
        from autoresearch.window import get_week_window
        start, end = get_week_window(date(2026, 5, 10))  # 2026-05-10 is Sunday
        assert end == date(2026, 5, 10)
        assert start == date(2026, 5, 4)  # Monday

    def test_monday_returns_prior_week(self):
        from autoresearch.window import get_week_window
        start, end = get_week_window(date(2026, 5, 11))  # Monday
        assert end == date(2026, 5, 10)
        assert start == date(2026, 5, 4)

    def test_friday_returns_prior_complete_week(self):
        from autoresearch.window import get_week_window
        start, end = get_week_window(date(2026, 5, 15))  # Friday
        assert end == date(2026, 5, 10)
        assert start == date(2026, 5, 4)


# ---------------------------------------------------------------------------
# evaluator — must return (markdown, composite_dict).
# ---------------------------------------------------------------------------


class TestEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate_week_returns_structured_metrics(self, monkeypatch):
        """evaluate_week must hand the runner both the markdown report and the
        composite dict, so the runner does not parse markdown."""
        from autoresearch import evaluator

        async def _fake_ws_metrics(*a, **k):
            return {
                "sharpe": 1.0, "sortino": 1.0, "max_drawdown": 0.10,
                "profit_factor": 2.0, "info_ratio": 1.0, "num_trading_days": 5,
                "total_return_pct": 5.0,
            }
        monkeypatch.setattr(evaluator, "compute_wall_street_metrics", _fake_ws_metrics)
        async def _fake_dq(*a, **k):
            return {
                "concordance": 0.7, "conviction_calibration": 0.8, "regime_awareness": 0.5,
                "mistake_patterns": [], "rejection_rate": 0.2, "total_decisions": 5,
                "total_trades": 2, "sample_wins": [], "sample_losses": [], "sample_rejections": [],
            }
        monkeypatch.setattr(evaluator, "compute_decision_quality", _fake_dq)

        async def fake_get_active_prompt(): return "ACTIVE_PROMPT"
        async def fake_get_previous_variants(**kw): return []
        async def fake_get_baseline_metrics(): return None

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_baseline_metrics", fake_get_baseline_metrics)

        client, _ = _make_client(data=[])
        async def _fake_async_sb_ev(): return client
        monkeypatch.setattr(evaluator, "get_async_supabase_client", _fake_async_sb_ev)

        result = await evaluator.evaluate_week()
        assert isinstance(result, tuple), "evaluate_week must return (report, metrics)"
        report, metrics = result
        assert isinstance(report, str) and "Weekly Trading Performance Report" in report
        assert isinstance(metrics, dict) and "composite" in metrics

    def test_market_regime_queries_use_fetched_at_and_price(self, monkeypatch):
        """VIXY and SPY queries in _get_market_regime_summary must use the real
        column names `fetched_at` and `price`, not the non-existent `date` and
        `close_price`."""
        from autoresearch import evaluator

        client, recorder = _make_client(data=[])
        async def _fake_async_sb_mr(): return client
        monkeypatch.setattr(evaluator, "get_async_supabase_client", _fake_async_sb_mr)

        asyncio.run(evaluator._get_market_regime_summary(date(2026, 5, 4), date(2026, 5, 10)))

        select_args = [c[1][0] for c in recorder.calls if c[0] == "select"]
        for sa in select_args:
            assert "close_price" not in sa, (
                f"close_price must not appear in select; got {select_args}"
            )

        filter_cols = [c[1][0] for c in recorder.calls if c[0] in ("gte", "lte", "order")]
        date_filters = [col for col in filter_cols if col == "date"]
        assert not date_filters, (
            f"'date' must not appear in gte/lte/order args (use fetched_at): {filter_cols}"
        )
        assert "fetched_at" in filter_cols, (
            f"fetched_at must appear in gte/lte/order args: {filter_cols}"
        )


# ---------------------------------------------------------------------------
# Query layer — uses .in_(), not the fragile filter(... "in", repr(...)) form.
# ---------------------------------------------------------------------------


class TestQuerySyntax:
    def test_metrics_uses_in_method(self, monkeypatch):
        from autoresearch import metrics

        client, recorder = _make_async_client(data=[])
        async def _fake_m(): return client
        monkeypatch.setattr(metrics, "get_async_supabase_client", _fake_m)

        asyncio.run(metrics.compute_wall_street_metrics(
            frozenset({"m1", "m2"}), date(2026, 5, 1), date(2026, 5, 7)
        ))

        names = recorder.call_names()
        # Must not use the raw filter("in", repr(...)) pattern anywhere.
        for call in recorder.calls:
            if call[0] == "filter" and len(call[1]) >= 2:
                assert call[1][1] != "in", (
                    "Use .in_(col, list) instead of raw .filter(col, 'in', '(...)')"
                )
        assert "in_" in names, f"Expected .in_() to be called; got {names}"

    def test_decision_quality_uses_in_method(self, monkeypatch):
        from autoresearch import decision_quality

        client, recorder = _make_async_client(data=[])
        async def _fake_d(): return client
        monkeypatch.setattr(decision_quality, "get_async_supabase_client", _fake_d)

        asyncio.run(decision_quality.compute_decision_quality(
            frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7)
        ))
        for call in recorder.calls:
            if call[0] == "filter" and len(call[1]) >= 2:
                assert call[1][1] != "in"

    def test_price_history_query_uses_fetched_at_and_price(self, monkeypatch):
        """The price_history table has `fetched_at` and `price` columns, NOT
        `date` and `close_price`.  Verify that _spy_returns() builds the query
        with the real column names so it does not fail at runtime."""
        from autoresearch import metrics

        client, recorder = _make_async_client(data=[])
        async def _fake_m(): return client
        monkeypatch.setattr(metrics, "get_async_supabase_client", _fake_m)

        asyncio.run(metrics.compute_wall_street_metrics(
            frozenset({"m1", "m2"}), date(2026, 5, 1), date(2026, 5, 7)
        ))

        select_args = [c[1][0] for c in recorder.calls if c[0] == "select"]
        ph_selects = [a for a in select_args if "price" in a and "fetched_at" in a]
        assert len(ph_selects) == 1, (
            f"Expected 1 price_history select with fetched_at,price; got selects: {select_args}"
        )
        assert "close_price" not in ph_selects[0]
        assert "date" not in ph_selects[0].split(", ")

        filter_cols = [c[1][0] for c in recorder.calls if c[0] in ("gte", "lte", "order")]
        assert "fetched_at" in filter_cols, (
            f"fetched_at must appear in gte/lte/order args: {filter_cols}"
        )


# ---------------------------------------------------------------------------
# Migration sanity — research_output must be JSONB.
# ---------------------------------------------------------------------------


class TestMigration:
    def test_research_output_is_jsonb(self):
        path = (ENGINE_DIR.parent.parent
                / "supabase" / "migrations"
                / "20260510000000_create_prompt_experiments.sql")
        sql = path.read_text()
        assert "research_output JSONB" in sql, (
            "research_output must be JSONB (a Python dict is written into this column)"
        )


# ==============================================================================
# NEW TESTS — TDD: write RED tests first, then implement.
# ==============================================================================


# ---------------------------------------------------------------------------
# Test 1: regime_awareness wired into composite score + computed from VIXY.
# ---------------------------------------------------------------------------


class TestRegimeAwarenessInComposite:
    """regime_awareness must be a weighted component of composite_score."""

    def test_composite_includes_regime_awareness_weight(self):
        from autoresearch.metrics import compute_composite_score

        base_metrics = {
            "sharpe": 0, "sortino": 0, "max_drawdown": 0.5,
            "profit_factor": 0, "info_ratio": 0,
        }
        # regime_awareness=1.0 should raise composite vs 0.0
        s_high = compute_composite_score(base_metrics, concordance=0.5,
                                         conviction=0.5, regime_awareness=1.0)
        s_low = compute_composite_score(base_metrics, concordance=0.5,
                                        conviction=0.5, regime_awareness=0.0)
        assert s_high["composite"] > s_low["composite"], (
            f"regime_awareness must affect composite: high={s_high['composite']}, low={s_low['composite']}"
        )

    def test_all_weights_sum_to_one_with_regime(self):
        from autoresearch.metrics import compute_composite_score

        s = compute_composite_score(
            {"sharpe": 5, "sortino": 5, "max_drawdown": 0,
             "profit_factor": 3, "info_ratio": 5},
            concordance=1.0, conviction=1.0, regime_awareness=1.0,
        )
        assert s["composite"] == pytest.approx(1.0, abs=0.01), (
            f"Full-score inputs + regime_awareness=1 must yield composite ~1.0, got {s['composite']}"
        )

    def test_regime_awareness_in_output_dict(self):
        from autoresearch.metrics import compute_composite_score

        s = compute_composite_score(
            {"sharpe": 1, "sortino": 1, "max_drawdown": 0.1,
             "profit_factor": 2, "info_ratio": 1},
            concordance=0.7, conviction=0.8, regime_awareness=0.6,
        )
        assert "regime_awareness" in s, (
            f"composite dict must include regime_awareness key; got {list(s.keys())}"
        )


class TestRegimeAwarenessComputation:
    """regime_awareness must be computed from actual VIXY data + trade decisions."""

    @pytest.mark.asyncio
    async def test_regime_awareness_computed_in_decision_quality(self, monkeypatch):
        from autoresearch import decision_quality

        # decisions: 8 BUYs, 2 SELLs (mostly aggressive buying)
        decisions = [
            {"ticker": f"T{i}", "signal": "BUY", "confidence": 80, "reasoning": "x",
             "status": "EXECUTED", "model_name": "m1"}
            for i in range(8)
        ] + [
            {"ticker": f"S{i}", "signal": "SELL", "confidence": 50, "reasoning": "x",
             "status": "EXECUTED", "model_name": "m1"}
            for i in range(2)
        ]
        trades = []

        # VIXY went UP 10% (fear spiked) — agent kept buying aggressively → LOW awareness
        vixy_data = [
            {"price": 20.0, "fetched_at": "2026-05-01"},
            {"price": 22.0, "fetched_at": "2026-05-02"},
        ]

        calls_made: dict[str, _QueryRecorder] = {}

        async def fake_get_client():
            client = MagicMock()

            def table(name):
                if name == "decisions":
                    rec = _AsyncQueryRecorder(data=decisions)
                elif name == "trades":
                    rec = _AsyncQueryRecorder(data=trades)
                elif name == "price_history":
                    rec = _AsyncQueryRecorder(data=vixy_data)
                else:
                    rec = _AsyncQueryRecorder(data=[])
                calls_made[name] = rec
                return rec

            client.table.side_effect = table
            return client

        monkeypatch.setattr(decision_quality, "get_async_supabase_client", fake_get_client)

        result = await decision_quality.compute_decision_quality(
            frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7)
        )
        # VIXY spiked + aggressive buying → regime_awareness < 0.5
        assert result["regime_awareness"] < 0.5, (
            f"High fear + aggressive buying must yield low regime_awareness, got {result['regime_awareness']}"
        )

    @pytest.mark.asyncio
    async def test_regime_awareness_high_when_defensive_in_volatility(self, monkeypatch):
        from autoresearch import decision_quality

        # decisions: 2 BUYs, 8 SELLs (defensive positioning)
        decisions = [
            {"ticker": f"T{i}", "signal": "BUY", "confidence": 30, "reasoning": "x",
             "status": "EXECUTED", "model_name": "m1"}
            for i in range(2)
        ] + [
            {"ticker": f"S{i}", "signal": "SELL", "confidence": 80, "reasoning": "x",
             "status": "EXECUTED", "model_name": "m1"}
            for i in range(8)
        ]
        trades = []

        # VIXY went UP 10% (fear spiked) — agent sold heavily → HIGH awareness
        vixy_data = [
            {"price": 20.0, "fetched_at": "2026-05-01"},
            {"price": 22.0, "fetched_at": "2026-05-02"},
        ]

        async def fake_get_client():
            client = MagicMock()

            def table(name):
                if name == "decisions":
                    rec = _AsyncQueryRecorder(data=decisions)
                elif name == "trades":
                    rec = _AsyncQueryRecorder(data=[])
                elif name == "price_history":
                    rec = _AsyncQueryRecorder(data=vixy_data)
                else:
                    rec = _AsyncQueryRecorder(data=[])
                return rec

            client.table.side_effect = table
            return client

        monkeypatch.setattr(decision_quality, "get_async_supabase_client", fake_get_client)

        result = await decision_quality.compute_decision_quality(
            frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7)
        )
        assert result["regime_awareness"] > 0.5, (
            f"High fear + defensive selling must yield high regime_awareness, got {result['regime_awareness']}"
        )


# ---------------------------------------------------------------------------
# Test 2: _close_client must NOT be called from researcher.py
# ---------------------------------------------------------------------------


class TestResearcherDoesNotCloseClient:
    """researcher.py must not call _close_client — the wiki forbids it."""

    def test_researcher_does_not_import_close_client(self):
        """Verify researcher.py does not import _close_client."""
        import ast
        path = ENGINE_DIR / "autoresearch" / "researcher.py"
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "core.llm":
                    for alias in node.names:
                        assert alias.name != "_close_client", (
                            "researcher.py must not import _close_client. "
                            "The wiki forbids closing the singleton httpx client."
                        )


# ---------------------------------------------------------------------------
# Test 3: runner must not duplicate get_week_window — evaluator owns it.
# ---------------------------------------------------------------------------


class TestRunnerWindowDuplication:
    """runner.py must get the week window from evaluator, not compute it twice."""

    def test_runner_passes_window_to_evaluator(self, monkeypatch):
        """Runner must call evaluate_week with its pre-computed window."""
        from autoresearch import runner

        evaluate_calls = []

        async def fake_evaluate(week_start, week_end):
            evaluate_calls.append((week_start, week_end))
            return "# report", {"composite": 0.5}

        async def fake_research(report):
            return None

        monkeypatch.setattr(runner, "evaluate_week", fake_evaluate)
        monkeypatch.setattr(runner, "run_research", fake_research)
        async def _fake_check_safety(ws, we): return (False, "")
        monkeypatch.setattr(runner, "_check_safety", _fake_check_safety)
        monkeypatch.setattr(runner, "validate_prompt",
                            lambda p: (True, "", []))
        monkeypatch.setattr(runner, "save_variant",
                            lambda **kw: "v-test")
        monkeypatch.setattr(runner, "revert_to_previous",
                            lambda **kw: "v-prev")

        import asyncio
        asyncio.run(runner.run())

        assert len(evaluate_calls) == 1, (
            f"evaluate_week must be called once, was called {len(evaluate_calls)} times"
        )
        ws, we = evaluate_calls[0]
        assert isinstance(ws, date), f"week_start must be a date, got {type(ws)}"
        assert isinstance(we, date), f"week_end must be a date, got {type(we)}"


# ---------------------------------------------------------------------------
# Test 4: _check_safety queries trades table, not just decisions.
# ---------------------------------------------------------------------------


class TestSafetyCheckUsesTrades:
    """_check_safety must count executed trades from the trades table."""

    def test_check_safety_queries_trades_table(self, monkeypatch):
        from autoresearch import runner

        query_log = []

        class TrackedRecorder(_AsyncQueryRecorder):
            def __getattr__(self, name):
                if name.startswith("_"):
                    raise AttributeError(name)
                def method(*args, **kwargs):
                    query_log.append(name)
                    if name == "execute":
                        async def _exec():
                            r = MagicMock()
                            r.data = self._data
                            return r
                        return _exec()
                    return self
                return method

        client = MagicMock()
        recorder = TrackedRecorder(data=[
            {"signal": "SELL", "realized_pnl": 100.0},
            {"signal": "SELL", "realized_pnl": -50.0},
            {"signal": "BUY", "realized_pnl": None},
        ])

        def table(name):
            query_log.append(f"table:{name}")
            return recorder

        client.table.side_effect = table
        async def _fake_async_sb_safety(): return client
        monkeypatch.setattr(runner, "get_async_supabase_client", _fake_async_sb_safety)

        is_crash, reason = asyncio.run(runner._check_safety(date(2026, 5, 1), date(2026, 5, 7)))
        assert "table:trades" in query_log, (
            f"_check_safety must query trades table; got table calls: {[q for q in query_log if q.startswith('table:')]}"
        )
        assert not is_crash, f"3 executed trades >= min; must not crash. Reason: {reason}"


# ---------------------------------------------------------------------------
# Test 5: Bootstrap tests + no CWD-dependent path hack.
# ---------------------------------------------------------------------------


class TestBootstrap:
    """Bootstrap must work without fragile sys.path hacks."""

    def test_bootstrap_does_not_use_sys_path_hack(self):
        """bootstrap.py must not manipulate sys.path with CWD-relative paths."""
        import ast
        path = ENGINE_DIR / "autoresearch" / "bootstrap.py"
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for sys.path.append or sys.path.insert
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Attribute):
                        if (node.func.value.attr == "path" and
                                node.func.value.value.id == "sys"):  # type: ignore[union-attr]
                            # Must not contain getcwd() or "apps"
                            code = ast.unparse(node)
                            assert "getcwd" not in code and "apps" not in code, (
                                f"bootstrap.py must not use CWD-dependent paths: {code}"
                            )

    @pytest.mark.asyncio
    async def test_bootstrap_idempotent(self, monkeypatch):
        """Bootstrap must be idempotent — second call is a no-op."""
        from autoresearch import bootstrap

        save_calls = []

        async def fake_get_active():
            # First call: no active prompt → must bootstrap
            # After bootstrap: active prompt exists → skip
            return "EXISTING_PROMPT" if save_calls else None

        async def fake_save_variant(**kw):
            save_calls.append(kw)
            return "v-bootstrap"

        monkeypatch.setattr(bootstrap, "get_active_prompt", fake_get_active)
        monkeypatch.setattr(bootstrap, "save_variant", fake_save_variant)

        await bootstrap.bootstrap()
        assert len(save_calls) == 1, (
            f"First bootstrap with no active prompt must save; got {len(save_calls)} calls"
        )

        # Second call: already active → must not save again
        await bootstrap.bootstrap()
        assert len(save_calls) == 1, (
            f"Second bootstrap must be idempotent (no double-save); got {len(save_calls)} calls"
        )


# ---------------------------------------------------------------------------
# Test 6: Word-count-based size validation (conservative cap: 1000 words ~1300 tokens).
# ---------------------------------------------------------------------------


class TestWordCountValidator:
    """Validator must cap prompt size by word count (no external tokenizer dependency)."""

    def test_rejects_oversized_prompt(self):
        from autoresearch.validator import validate_prompt
        # "The quick brown fox jumps over the lazy dog." has 9 words → * 150 = 1350 words > 1000 cap
        long_text = "The quick brown fox jumps over the lazy dog. " * 150
        ok, reason, _ = validate_prompt(long_text)
        assert not ok, f"Prompt with >1000 words must be rejected; reason: {reason}"

    def test_accepts_reasonable_prompt(self):
        from autoresearch.validator import validate_prompt
        short = (
            "You are a trading agent. Apply the 5 Whys technique. "
            "For BUY: call calculate_buy_quantity. For SELL: call calculate_sell_quantity."
        )
        ok, reason, _ = validate_prompt(short)
        assert ok, f"Short valid prompt must pass: {reason}"

    def test_reason_mentions_words(self):
        from autoresearch.validator import validate_prompt
        long_text = "word " * 1500
        ok, reason, _ = validate_prompt(long_text)
        if not ok:
            assert "words" in reason.lower(), (
                f"Rejection reason must mention words; got: {reason}"
            )

    def test_exactly_at_cap_passes(self):
        from autoresearch.validator import validate_prompt
        # 1000 words exactly — must pass
        text = "a " * 1000
        ok, reason, _ = validate_prompt(text)
        assert ok, f"Prompt at exact cap (1000 words) must pass: {reason}"


# ---------------------------------------------------------------------------
# Test 7: Composite score edge cases — missing benchmark, NaN, zero days.
# ---------------------------------------------------------------------------


class TestCompositeEdgeCases:
    """Composite score must handle edge cases gracefully with clear flags."""

    def test_missing_spy_benchmark_is_flagged(self):
        from autoresearch.metrics import compute_composite_score

        # info_ratio=0 means no benchmark available → flag
        s = compute_composite_score(
            {"sharpe": 1, "sortino": 1, "max_drawdown": 0.1,
             "profit_factor": 2, "info_ratio": 0,
             "num_trading_days": 5, "total_return_pct": 3.0},
            concordance=0.7, conviction=0.8, regime_awareness=0.5,
        )
        assert "warnings" in s, (
            "Composite dict must include 'warnings' key for edge case flags"
        )

    def test_no_data_produces_clear_signal(self):
        from autoresearch.metrics import compute_composite_score

        s = compute_composite_score(
            {"sharpe": 0, "sortino": 0, "max_drawdown": 0,
             "profit_factor": 0, "info_ratio": 0,
             "num_trading_days": 0, "total_return_pct": 0},
            concordance=0.5, conviction=0.5, regime_awareness=0.5,
        )
        assert s["composite"] >= 0, "Composite must not be negative"
        assert "warnings" in s, "No-data scenario must produce warnings"
        assert len(s["warnings"]) > 0, (
            f"No-data must have at least 1 warning; got {s['warnings']}"
        )

    def test_negative_sharpe_normalizes_to_zero(self):
        from autoresearch.metrics import compute_composite_score

        s = compute_composite_score(
            {"sharpe": -5, "sortino": -5, "max_drawdown": 0.5,
             "profit_factor": 0, "info_ratio": -5},
            concordance=0, conviction=0, regime_awareness=0,
        )
        assert s["composite"] >= 0, (
            f"Worst-case inputs must not go below 0; got {s['composite']}"
        )
        # Should be close to 0 but not negative
        assert s["composite"] < 0.3, (
            f"Worst-case inputs should yield low score; got {s['composite']}"
        )


# ==============================================================================
# PLAN HARDENING TESTS — TDD: write RED tests first, then implement.
# ==============================================================================


# ---------------------------------------------------------------------------
# Helpers — async variant of _QueryRecorder for async supabase client tests.
# ---------------------------------------------------------------------------


class _AsyncQueryRecorder:
    """Chainable mock for async supabase-py query builder.

    Every chained method returns self, except execute() which returns an
    awaitable resolving to a MagicMock with the configured .data payload.
    """

    def __init__(self, data=None, single_data=None):
        self.calls: list[tuple[str, tuple, dict]] = []
        self._data = data or []
        self._single_data = single_data

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "execute":
                async def _exec():
                    r = MagicMock()
                    r.data = self._data if self._single_data is None else self._single_data
                    return r
                return _exec()
            return self

        return method

    def call_names(self) -> list[str]:
        return [c[0] for c in self.calls]


def _make_async_client(data=None, single_data=None) -> tuple[MagicMock, _AsyncQueryRecorder]:
    recorder = _AsyncQueryRecorder(data=data, single_data=single_data)
    client = MagicMock()
    client.table.return_value = recorder
    return client, recorder


# ---------------------------------------------------------------------------
# Test A: save_variant atomicity — insert before demotion.
# ---------------------------------------------------------------------------


class TestSaveVariantAtomicity:
    """save_variant must insert BEFORE demoting the old active prompt."""

    @pytest.mark.asyncio
    async def test_insert_before_demotion(self, monkeypatch):
        """INSERT must happen before UPDATE (demotion) in save_variant."""
        from autoresearch import prompt_store

        op_order: list[str] = []

        class OrderTracker(_AsyncQueryRecorder):
            def __getattr__(self, name):
                if name.startswith("_"):
                    raise AttributeError(name)
                def method(*args, **kwargs):
                    if name in ("update", "insert"):
                        op_order.append(name)
                    if name == "execute":
                        async def _exec():
                            r = MagicMock()
                            r.data = self._single_data if self._single_data is not None else []
                            return r
                        return _exec()
                    return self
                return method

        client = MagicMock()
        recorder = OrderTracker(single_data={"variant_tag": "v-old"})
        client.table.return_value = recorder

        async def fake_async_client():
            return client

        monkeypatch.setattr(prompt_store, "get_async_supabase_client", fake_async_client)
        prompt_store.clear_active_prompt_cache()

        await prompt_store.save_variant(
            prompt_content="NEW_PROMPT",
            prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
            week_start="2026-05-04",
            week_end="2026-05-10",
            metrics={"composite": 0.5},
            change_description="test atomicity",
            experiment_type="incremental",
        )

        insert_idx = next((i for i, op in enumerate(op_order) if op == "insert"), None)
        update_idx = next((i for i, op in enumerate(op_order) if op == "update"), None)

        assert insert_idx is not None, "Expected an 'insert' operation"
        assert update_idx is not None, "Expected an 'update' operation"
        assert insert_idx < update_idx, (
            f"INSERT must happen BEFORE UPDATE (demotion). "
            f"Got insert at {insert_idx}, update at {update_idx}. "
            f"Full order: {op_order}"
        )


# ---------------------------------------------------------------------------
# Test B: run_research retry loop — validation errors vs non-retryable.
# ---------------------------------------------------------------------------


class TestResearcherRetry:
    """run_research must retry on validation errors and bail on non-retryable."""

    @pytest.mark.asyncio
    async def test_retries_on_validation_error(self, monkeypatch):
        from autoresearch import researcher

        call_count = {"n": 0}

        async def fake_create(**kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise Exception("validation error: input should be a valid")
            wrapper = MagicMock()
            return wrapper

        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(researcher, "get_deepseek_client", lambda: fake_client)

        result = await researcher.run_research("# Test Report")
        assert result is not None, "Should return result on 3rd retry"
        assert call_count["n"] == 3, f"Expected 3 attempts, got {call_count['n']}"

    @pytest.mark.asyncio
    async def test_returns_none_on_non_retryable_error(self, monkeypatch):
        from autoresearch import researcher

        async def fake_create(**kwargs):
            raise Exception("rate limit exceeded — fatal, not validation")

        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(researcher, "get_deepseek_client", lambda: fake_client)

        result = await researcher.run_research("# Test Report")
        assert result is None, "Non-retryable errors must return None"

    @pytest.mark.asyncio
    async def test_returns_none_after_all_retries_exhausted(self, monkeypatch):
        from autoresearch import researcher

        call_count = {"n": 0}

        async def fake_create(**kwargs):
            call_count["n"] += 1
            raise Exception("validation error: bad schema — every time")

        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(researcher, "get_deepseek_client", lambda: fake_client)

        result = await researcher.run_research("# Test Report")
        assert result is None, "Must return None after all retries fail"
        assert call_count["n"] == 3, f"Expected 3 attempts, got {call_count['n']}"
