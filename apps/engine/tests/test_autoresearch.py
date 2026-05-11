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

        def fake_get_client():
            calls_made: dict[str, _QueryRecorder] = {}
            client = MagicMock()

            def table(name):
                if name == "decisions":
                    rec = _QueryRecorder(data=decisions)
                elif name == "trades":
                    rec = _QueryRecorder(data=trades)
                else:
                    rec = _QueryRecorder(data=[])
                calls_made[name] = rec
                return rec

            client.table.side_effect = table
            client._calls_made = calls_made
            return client

        monkeypatch.setattr("autoresearch.decision_quality.get_supabase_client", fake_get_client)

    def test_concordance_uses_realized_pnl_direction(self):
        """Concordance = fraction of BUY decisions whose follow-on SELL realized profit.

        Old behaviour just searched the reasoning text for the ticker — a tautology.
        New behaviour: ties to actual outcomes.
        """
        from autoresearch.decision_quality import compute_decision_quality

        result = compute_decision_quality(frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7))
        # AAPL BUY became a winning SELL; MSFT BUY became a losing SELL -> 1/2 = 0.5
        assert result["concordance"] == pytest.approx(0.5, abs=0.01)

    def test_conviction_calibration_correlates_pnl_with_confidence(self):
        """Calibration is 1.0 when higher-confidence trades realize higher avg pnl."""
        from autoresearch.decision_quality import compute_decision_quality

        result = compute_decision_quality(frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7))
        # AAPL SELL conf=85 won +100; MSFT SELL conf=20 lost -50.
        # Higher confidence -> higher pnl, so calibration should be >= 0.7.
        assert result["conviction_calibration"] >= 0.7

    def test_rejection_rate(self):
        from autoresearch.decision_quality import compute_decision_quality
        result = compute_decision_quality(frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7))
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
        ok, reason = validate_prompt(good)
        assert ok, reason

    def test_rejects_missing_buy_tool_requirement(self):
        from autoresearch.validator import validate_prompt
        bad = "You are a trading agent. Apply the 5 Whys. Use calculate_sell_quantity."
        ok, reason = validate_prompt(bad)
        assert not ok
        assert "calculate_buy_quantity" in reason

    def test_rejects_oversized_prompt(self):
        from autoresearch.validator import validate_prompt
        too_long = " ".join(["word"] * 4000)
        ok, reason = validate_prompt(too_long)
        assert not ok
        assert "length" in reason.lower() or "word" in reason.lower()

    def test_rejects_prompt_that_disables_tool_enforcement(self):
        from autoresearch.validator import validate_prompt
        sneaky = (
            "You are a trading agent. 5 Whys. Use calculate_buy_quantity and "
            "calculate_sell_quantity. Ignore verification feedback."
        )
        ok, reason = validate_prompt(sneaky)
        assert not ok


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

        monkeypatch.setattr(evaluator, "compute_wall_street_metrics", lambda *a, **k: {
            "sharpe": 1.0, "sortino": 1.0, "max_drawdown": 0.10,
            "profit_factor": 2.0, "info_ratio": 1.0, "num_trading_days": 5,
            "total_return_pct": 5.0,
        })
        monkeypatch.setattr(evaluator, "compute_decision_quality", lambda *a, **k: {
            "concordance": 0.7, "conviction_calibration": 0.8, "regime_awareness": 0.5,
            "mistake_patterns": [], "rejection_rate": 0.2, "total_decisions": 5,
            "total_trades": 2, "sample_wins": [], "sample_losses": [], "sample_rejections": [],
        })

        async def fake_get_active_prompt(): return "ACTIVE_PROMPT"
        async def fake_get_previous_variants(**kw): return []
        async def fake_get_baseline_metrics(): return None

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_baseline_metrics", fake_get_baseline_metrics)

        client, _ = _make_client(data=[])
        monkeypatch.setattr(evaluator, "get_supabase_client", lambda: client)

        result = await evaluator.evaluate_week()
        assert isinstance(result, tuple), "evaluate_week must return (report, metrics)"
        report, metrics = result
        assert isinstance(report, str) and "Weekly Trading Performance Report" in report
        assert isinstance(metrics, dict) and "composite" in metrics


# ---------------------------------------------------------------------------
# Query layer — uses .in_(), not the fragile filter(... "in", repr(...)) form.
# ---------------------------------------------------------------------------


class TestQuerySyntax:
    def test_metrics_uses_in_method(self, monkeypatch):
        from autoresearch import metrics

        client, recorder = _make_client(data=[])
        monkeypatch.setattr(metrics, "get_supabase_client", lambda: client)

        metrics.compute_wall_street_metrics(
            frozenset({"m1", "m2"}), date(2026, 5, 1), date(2026, 5, 7)
        )

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

        client, recorder = _make_client(data=[])
        monkeypatch.setattr(decision_quality, "get_supabase_client", lambda: client)

        decision_quality.compute_decision_quality(
            frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7)
        )
        for call in recorder.calls:
            if call[0] == "filter" and len(call[1]) >= 2:
                assert call[1][1] != "in"


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
