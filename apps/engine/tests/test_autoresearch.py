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
    async def test_evaluate_week_returns_score_dict(self, monkeypatch):
        """evaluate_week returns (report, metrics) where metrics has score,
        excess_return, max_drawdown — no DQ, no concordance, no validator."""
        from autoresearch import evaluator

        async def _fake_ws_metrics(*a, **k):
            return {"total_return_pct": 5.0, "max_drawdown": 0.10}
        monkeypatch.setattr(evaluator, "compute_wall_street_metrics", _fake_ws_metrics)

        async def _fake_spy_returns(*a, **k):
            return [0.001, 0.002, -0.001]  # ~0.2% cumulative
        monkeypatch.setattr(evaluator, "_spy_returns", _fake_spy_returns)

        async def fake_get_active_prompt(): return "ACTIVE_PROMPT"
        async def fake_get_previous_variants(**kw): return []
        async def fake_get_all_time_baseline(): return None

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_all_time_baseline", fake_get_all_time_baseline)

        # New evaluate_week doesn't need get_async_supabase_client directly
        # — it passes it to internal functions

        result = await evaluator.evaluate_week()
        assert isinstance(result, tuple), "evaluate_week must return (report, metrics, baseline_tag)"
        report, metrics, baseline_tag = result
        assert isinstance(report, str) and "Weekly" in report
        assert isinstance(metrics, dict) and "score" in metrics
        assert "excess_return" in metrics
        assert "max_drawdown" in metrics
    @pytest.mark.asyncio
    async def test_evaluate_week_includes_control_reference(self, monkeypatch):
        """Report must mention control agent return as reference."""
        from autoresearch import evaluator

        async def _fake_ws_metrics(*a, **k):
            return {"total_return_pct": 2.0, "max_drawdown": 0.05}
        monkeypatch.setattr(evaluator, "compute_wall_street_metrics", _fake_ws_metrics)

        async def _fake_spy_returns(*a, **k):
            return [0.001, 0.001, 0.001]
        monkeypatch.setattr(evaluator, "_spy_returns", _fake_spy_returns)

        async def fake_get_active_prompt(): return "PROMPT"
        async def fake_get_previous_variants(**kw): return []
        async def fake_get_all_time_baseline(): return None

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_all_time_baseline", fake_get_all_time_baseline)

        report, _, _ = await evaluator.evaluate_week()
        assert "Control" in report, "Report must include control reference"


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

    def test_price_history_query_uses_fetched_at_and_price(self, monkeypatch):
        """The price_history table has `fetched_at` and `price` columns, NOT
        `date` and `close_price`.  Verify that _spy_returns() builds the query
        with the real column names so it does not fail at runtime."""
        from autoresearch import metrics

        client, recorder = _make_async_client(data=[])
        async def _fake_m(): return client
        monkeypatch.setattr(metrics, "get_async_supabase_client", _fake_m)

        asyncio.run(metrics._spy_returns(
            client, date(2026, 5, 1), date(2026, 5, 7)
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

# ---------------------------------------------------------------------------
# Test C: activation gate — skip when beating baseline, activate when losing.
# ---------------------------------------------------------------------------

class TestActivationGate:
    """Every week must deploy a new prompt variant — no skipping, no gate.
    The meta-researcher always explores. When score < baseline, the active
    prompt is reverted to the baseline before the next experiment deploys."""

    @staticmethod
    def _make_result(**overrides) -> "PromptResearchResult":
        from autoresearch.researcher import PromptResearchResult
        defaults = dict(
            new_prompt_text="test prompt",
            change_description="test change",
            experiment_type="incremental",
            research_reasoning="test reasoning",
            confidence=75,
        )
        defaults.update(overrides)
        return PromptResearchResult(**defaults)

    @staticmethod
    def _make_score(score: float) -> dict:
        return {"score": score, "excess_return": 0.0, "max_drawdown": 0.0}

    def _patch_runner(self, monkeypatch, exp_score: float):
        """Patch runner deps. Returns (runner, save_calls, revert_calls) for assertion."""
        from autoresearch import runner

        async def fake_evaluate(ws, we):
            return ("# report", self._make_score(exp_score), "v-baseline")

        async def fake_research(report):
            return self._make_result()

        async def fake_baseline_metrics():
            return self._make_score(1.0)

        async def fake_check(ws, we):
            return (False, "")

        monkeypatch.setattr(runner, "evaluate_week", fake_evaluate)
        monkeypatch.setattr(runner, "run_research", fake_research)
        monkeypatch.setattr(runner, "_check_safety", fake_check)
        monkeypatch.setattr(runner, "get_baseline_metrics", fake_baseline_metrics)

        save_calls = []

        async def fake_save(**kw):
            save_calls.append(kw)
            return "v-test"

        revert_calls = []

        async def fake_revert_to_baseline(**kw):
            revert_calls.append(kw)
            return "v-baseline-reverted"

        monkeypatch.setattr(runner, "save_variant", fake_save)
        monkeypatch.setattr(runner, "revert_to_previous", lambda **kw: "v-prev")
        monkeypatch.setattr(runner, "revert_to_baseline", fake_revert_to_baseline)
        return runner, save_calls, revert_calls

    def test_deploys_when_score_beats_baseline(self, monkeypatch):
        """When score BEATS baseline, deploy AND do NOT revert to baseline."""
        runner, save_calls, revert_calls = self._patch_runner(monkeypatch, exp_score=2.0)
        import asyncio
        asyncio.run(runner.run())
        assert len(save_calls) == 1, (
            f"Must deploy new variant when score beats baseline (2.0 > 1.0). "
            f"save_variant was called {len(save_calls)} times"
        )
        assert len(revert_calls) == 0, (
            f"Must NOT revert when score beats baseline. "
            f"revert_to_baseline was called {len(revert_calls)} times"
        )

    def test_deploys_and_reverts_when_below_baseline(self, monkeypatch):
        """When score < baseline, revert to baseline THEN deploy new variant."""
        runner, save_calls, revert_calls = self._patch_runner(monkeypatch, exp_score=-0.5)
        import asyncio
        asyncio.run(runner.run())
        assert len(save_calls) == 1, (
            f"Must still deploy new variant after revert. "
            f"save_variant was called {len(save_calls)} times"
        )
        assert len(revert_calls) == 1, (
            f"Must call revert_to_baseline when score (-0.5) < baseline (1.0). "
            f"revert_to_baseline was called {len(revert_calls)} times"
        )

    def test_deploys_and_reverts_when_zero_score(self, monkeypatch):
        """Zero score (treading water) < baseline → revert + deploy."""
        runner, save_calls, revert_calls = self._patch_runner(monkeypatch, exp_score=0.0)
        import asyncio
        asyncio.run(runner.run())
        assert len(save_calls) == 1, (
            f"Must deploy new variant even at zero score. "
            f"save_variant was called {len(save_calls)} times"
        )
        assert len(revert_calls) == 1, (
            f"Must revert when score (0.0) < baseline (1.0). "
            f"revert_to_baseline was called {len(revert_calls)} times"
        )

    def test_deploys_when_baseline_unavailable(self, monkeypatch):
        """When no baseline exists (first week), deploy without revert."""
        from autoresearch import runner

        async def fake_evaluate(ws, we):
            return ("# report", self._make_score(0.5), None)

        async def fake_research(report):
            return self._make_result()

        async def fake_baseline_metrics():
            return None  # No baseline yet

        async def fake_check(ws, we):
            return (False, "")

        monkeypatch.setattr(runner, "evaluate_week", fake_evaluate)
        monkeypatch.setattr(runner, "run_research", fake_research)
        monkeypatch.setattr(runner, "_check_safety", fake_check)
        monkeypatch.setattr(runner, "get_baseline_metrics", fake_baseline_metrics)

        save_calls = []
        revert_calls = []

        async def fake_save(**kw):
            save_calls.append(kw)
            return "v-test"

        async def fake_revert_to_baseline(**kw):
            revert_calls.append(kw)
            return "v-baseline"

        monkeypatch.setattr(runner, "save_variant", fake_save)
        monkeypatch.setattr(runner, "revert_to_previous", lambda **kw: "v-prev")
        monkeypatch.setattr(runner, "revert_to_baseline", fake_revert_to_baseline)

        import asyncio
        asyncio.run(runner.run())
        assert len(save_calls) == 1
        assert len(revert_calls) == 0, "No revert when no baseline exists"

# ==============================================================================
# TDD: Fix price_history end-of-day filtering and baseline metrics ordering.
# ==============================================================================

class TestBaselineMetricsOrdering:
    """get_baseline_metrics must return the most recent baseline, not the oldest."""

    @pytest.mark.asyncio
    async def test_all_time_baseline_logic(self, monkeypatch):
        """get_all_time_baseline must find the variant with the highest score."""
        from autoresearch import prompt_store

        variants = [
            {"variant_tag": "v1", "metrics": {"score": 1.0}},
            {"variant_tag": "v2", "metrics": {"score": 3.0}},
            {"variant_tag": "v3", "metrics": {"score": 2.0}},
        ]

        client, recorder = _make_async_client(data=variants)
        monkeypatch.setattr(prompt_store, "get_async_supabase_client", lambda: asyncio.Future())

        # Manually override the client return to avoid real network call
        async def fake_client(): return client
        monkeypatch.setattr(prompt_store, "get_async_supabase_client", fake_client)

        result = await prompt_store.get_all_time_baseline()
        assert result["variant_tag"] == "v2"
        assert result["metrics"]["score"] == 3.0


# ==============================================================================
# PHASE 2: New single-score formula — RED tests.
# ==============================================================================

class TestComputeScore:
    """compute_score(portfolio_return_pct, spy_return_pct, max_drawdown_pct)
    returns a dict with score, excess_return, max_drawdown."""

    def test_basic_formula(self):
        """score = (portfolio_return - spy_return) - (max_drawdown * 0.3)"""
        from autoresearch.metrics import compute_score
        result = compute_score(portfolio_return_pct=3.0, spy_return_pct=1.0, max_drawdown_pct=5.0)
        assert result["excess_return"] == pytest.approx(2.0)
        assert result["score"] == pytest.approx(0.5)  # 2.0 - (5.0 * 0.3) = 2.0 - 1.5 = 0.5

    def test_drawdown_penalty_reduces_score(self):
        """Higher drawdown must produce lower score for same excess return."""
        from autoresearch.metrics import compute_score
        low_dd = compute_score(portfolio_return_pct=3.0, spy_return_pct=1.0, max_drawdown_pct=2.0)
        high_dd = compute_score(portfolio_return_pct=3.0, spy_return_pct=1.0, max_drawdown_pct=10.0)
        assert low_dd["score"] > high_dd["score"]

    def test_negative_excess_gives_negative_score(self):
        """Underperforming SPY should produce negative score."""
        from autoresearch.metrics import compute_score
        result = compute_score(portfolio_return_pct=-2.0, spy_return_pct=1.0, max_drawdown_pct=2.0)
        assert result["score"] < 0
        assert result["excess_return"] == pytest.approx(-3.0)

    def test_beat_spy_but_high_drawdown_can_be_negative(self):
        """Beating SPY is not enough — drawdown penalty can flip score negative."""
        from autoresearch.metrics import compute_score
        result = compute_score(portfolio_return_pct=3.0, spy_return_pct=1.0, max_drawdown_pct=15.0)
        # excess = 2.0 - (15*0.3) = 2.0 - 4.5 = -2.5
        assert result["score"] < 0

    def test_zero_drawdown_positive_excess(self):
        """Perfect run: excess return with no drawdown."""
        from autoresearch.metrics import compute_score
        result = compute_score(portfolio_return_pct=5.0, spy_return_pct=1.0, max_drawdown_pct=0.0)
        assert result["score"] == pytest.approx(4.0)
        assert result["max_drawdown"] == 0.0

    def test_excess_return_in_output(self):
        """Output dict must include excess_return and max_drawdown for transparency."""
        from autoresearch.metrics import compute_score
        result = compute_score(portfolio_return_pct=2.0, spy_return_pct=0.5, max_drawdown_pct=3.0)
        assert "excess_return" in result
        assert "max_drawdown" in result
        assert "score" in result


# ==============================================================================
# Baseline tracking: best (score, prompt) pair. Replaces "last week's target."
# ==============================================================================

class TestBaselineTracking:
    """The baseline is the highest score achieved so far (with its prompt).
    It updates when beaten, stays when not. The meta-researcher's target."""

    @pytest.mark.asyncio
    async def test_baseline_is_max_historical_score(self, monkeypatch):
        """Baseline must be taken from get_all_time_baseline()."""
        from autoresearch import evaluator

        async def _fake_ws_metrics(*a, **k):
            return {"total_return_pct": 2.0, "max_drawdown": 0.02}
        monkeypatch.setattr(evaluator, "compute_wall_street_metrics", _fake_ws_metrics)

        async def _fake_spy_returns(*a, **k):
            return [0.001, 0.001, 0.001]
        monkeypatch.setattr(evaluator, "_spy_returns", _fake_spy_returns)

        async def fake_get_active_prompt(): return "PROMPT"
        async def fake_get_previous_variants(**kw): return []
        async def fake_get_all_time_baseline():
            return {
                "variant_tag": "v-best",
                "prompt_content": "BEST_PROMPT",
                "metrics": {"score": 3.0}
            }

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_all_time_baseline", fake_get_all_time_baseline)

        report, _, _ = await evaluator.evaluate_week()
        assert "Baseline: 3.0" in report, (
            f"Report must show max historical score as baseline.\nReport:\n{report}"
        )

    @pytest.mark.asyncio
    async def test_baseline_shows_delta(self, monkeypatch):
        """When current score is 2.0 and baseline is 3.0, show Δ: -1.0."""
        from autoresearch import evaluator

        async def _fake_ws_metrics(*a, **k):
            return {"total_return_pct": 2.5, "max_drawdown": 0.02}
        monkeypatch.setattr(evaluator, "compute_wall_street_metrics", _fake_ws_metrics)

        async def _fake_spy_returns(*a, **k):
            return [0.001, 0.001, 0.001]
        monkeypatch.setattr(evaluator, "_spy_returns", _fake_spy_returns)

        async def fake_get_active_prompt(): return "PROMPT"
        async def fake_get_previous_variants(**kw): return []
        async def fake_get_all_time_baseline():
            return {
                "variant_tag": "v-best",
                "prompt_content": "BEST_PROMPT",
                "metrics": {"score": 3.0}
            }

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_all_time_baseline", fake_get_all_time_baseline)

        report, _, _ = await evaluator.evaluate_week()
        # Current score: portfolio=2.5, SPY=~0.3, drawdown=2.0 → score ≈ 1.9
        # Baseline = 3.0 → delta should be negative
        assert "Baseline:" in report
        assert "Δ:" in report, f"Report must show delta vs baseline:\n{report}"

    @pytest.mark.asyncio
    async def test_no_previous_variants_shows_no_baseline(self, monkeypatch):
        """First week with no prior variants must show 'no baseline yet'."""
        from autoresearch import evaluator

        async def _fake_ws_metrics(*a, **k):
            return {"total_return_pct": 2.0, "max_drawdown": 0.02}
        monkeypatch.setattr(evaluator, "compute_wall_street_metrics", _fake_ws_metrics)

        async def _fake_spy_returns(*a, **k):
            return [0.001, 0.001, 0.001]
        monkeypatch.setattr(evaluator, "_spy_returns", _fake_spy_returns)

        async def fake_get_active_prompt(): return "PROMPT"
        async def fake_get_previous_variants(**kw): return []
        async def fake_get_all_time_baseline(): return None

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_all_time_baseline", fake_get_all_time_baseline)

        report, _, _ = await evaluator.evaluate_week()
        assert "no baseline" in report.lower() or "n/a" in report.lower(), (
            f"First week report must indicate no baseline yet:\n{report}"
        )

# ==============================================================================
# TDD: _daily_returns must compute equal-weighted percentage returns.
# ==============================================================================

class TestDailyReturnsEqualWeighted:
    """_daily_returns must average per-agent percentage returns, not sum equity."""

    @pytest.mark.asyncio
    async def test_two_agents_equal_weighted(self):
        """Two agents: Gemini +10%, DeepSeek -20% → average = -5%"""
        from autoresearch import metrics

        rows = [
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-04", "total_equity": 5000, "portfolios": {"owner_id": "deepseek"}},
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-05", "total_equity": 4000, "portfolios": {"owner_id": "deepseek"}},
        ]

        client, recorder = _make_async_client(data=rows)

        from datetime import date
        result = await metrics._daily_returns(
            client, {"gemini", "deepseek"},
            date(2026, 5, 4), date(2026, 5, 5)
        )

        # Gemini: (11000-10000)/10000 = +0.10
        # DeepSeek: (4000-5000)/5000 = -0.20
        # Average = -0.05
        assert len(result) == 1
        assert result[0] == pytest.approx(-0.05)
