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
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

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
                                r = MagicMock()
                                r.data = self._single_data
                                return r
                            r = MagicMock()
                            r.data = self._data
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
                    if name.startswith("_"):
                        raise AttributeError(name)

                    def method(*args, **kwargs):
                        if name == "execute":

                            async def exec_coro():
                                r = MagicMock()
                                r.data = self._single_data
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
                    if name.startswith("_"):
                        raise AttributeError(name)

                    def method(*args, **kwargs):
                        if name == "execute":

                            async def exec_coro():
                                r = MagicMock()
                                r.data = {"prompt_content": f"v{call_count['n']}"}
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

        async def fake_get_active_prompt():
            return "ACTIVE_PROMPT"

        async def fake_get_previous_variants(**kw):
            return []

        async def fake_get_all_time_baseline():
            return None

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

        async def fake_get_active_prompt():
            return "PROMPT"

        async def fake_get_previous_variants(**kw):
            return []

        async def fake_get_all_time_baseline():
            return None

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

        async def _fake_m():
            return client

        monkeypatch.setattr(metrics, "get_async_supabase_client", _fake_m)

        asyncio.run(metrics.compute_wall_street_metrics(frozenset({"m1", "m2"}), date(2026, 5, 1), date(2026, 5, 7)))

        names = recorder.call_names()
        # Must not use the raw filter("in", repr(...)) pattern anywhere.
        for call in recorder.calls:
            if call[0] == "filter" and len(call[1]) >= 2:
                assert call[1][1] != "in", "Use .in_(col, list) instead of raw .filter(col, 'in', '(...)')"
        assert "in_" in names, f"Expected .in_() to be called; got {names}"

    def test_price_history_query_uses_fetched_at_and_price(self, monkeypatch):
        """The price_history table has `fetched_at` and `price` columns, NOT
        `date` and `close_price`.  Verify that _spy_returns() builds the query
        with the real column names so it does not fail at runtime."""
        from autoresearch import metrics

        client, recorder = _make_async_client(data=[])

        async def _fake_m():
            return client

        monkeypatch.setattr(metrics, "get_async_supabase_client", _fake_m)

        asyncio.run(metrics._spy_returns(client, date(2026, 5, 1), date(2026, 5, 7)))

        select_args = [c[1][0] for c in recorder.calls if c[0] == "select"]
        ph_selects = [a for a in select_args if "price" in a and "fetched_at" in a]
        assert len(ph_selects) == 1, (
            f"Expected 1 price_history select with fetched_at,price; got selects: {select_args}"
        )
        assert "close_price" not in ph_selects[0]
        assert "date" not in ph_selects[0].split(", ")

        filter_cols = [c[1][0] for c in recorder.calls if c[0] in ("gte", "lte", "order")]
        assert "fetched_at" in filter_cols, f"fetched_at must appear in gte/lte/order args: {filter_cols}"


# ---------------------------------------------------------------------------
# Do-Nothing return calculation tests
# ---------------------------------------------------------------------------


class TestDoNothingReturn:
    @pytest.mark.asyncio
    async def test_do_nothing_return_with_legacy_positions(self, monkeypatch):
        """Verify that _do_nothing_return uses older price records (legacy assets)
        and does not value them at 0.0 when they fall outside the 14-day window.
        """
        from autoresearch import metrics

        week_start = date(2026, 5, 25)
        week_end = date(2026, 5, 31)

        class FakeResponse:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def __init__(self, table_name, data_map):
                self.table_name = table_name
                self.data_map = data_map
                self.gte_filters = {}
                self.lte_filters = {}
                self.eq_filters = {}

            def select(self, *args, **kwargs):
                return self

            def in_(self, *args, **kwargs):
                return self

            def gte(self, col, val):
                self.gte_filters[col] = val
                return self

            def lte(self, col, val):
                self.lte_filters[col] = val
                return self

            def lt(self, *args, **kwargs):
                return self

            def eq(self, col, val):
                self.eq_filters[col] = val
                return self

            def order(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

            async def execute(self):
                data = self.data_map.get(self.table_name, [])
                filtered = []
                print(f"\n[FakeQuery execute] Table: {self.table_name}")
                print(f"  GTE filters: {self.gte_filters}")
                print(f"  LTE filters: {self.lte_filters}")
                print(f"  EQ filters: {self.eq_filters}")
                for row in data:
                    keep = True
                    if self.eq_filters:
                        for col, val in self.eq_filters.items():
                            if row.get(col) != val:
                                keep = False
                    if self.table_name == "price_history" and row.get("fetched_at"):
                        fetched_at = row["fetched_at"]
                        if "fetched_at" in self.gte_filters and fetched_at < self.gte_filters["fetched_at"]:
                            print(f"    Filtering out {row} because fetched_at < {self.gte_filters['fetched_at']}")
                            keep = False
                        if "fetched_at" in self.lte_filters:
                            # Strip trailing T23:59:59 if any to do string comparison
                            val_str = self.lte_filters["fetched_at"].split("T")[0]
                            if fetched_at.split("T")[0] > val_str:
                                print(f"    Filtering out {row} because fetched_at > {val_str}")
                                keep = False

                    if keep:
                        filtered.append(row)
                print(f"  Result count: {len(filtered)}")
                return FakeResponse(filtered)

        class FakeClient:
            def __init__(self, data_map):
                self.data_map = data_map

            def table(self, name):
                return FakeQuery(name, self.data_map)

        # Mock database data:
        # Portfolio initial state has 10,000 equity and 3,500 cash.
        # Trades before week start has 20 shares of IBM (legacy) and 10 shares of AAPL (active).
        # Price history has IBM at $250 fetched on April 15 (older than 14 days),
        # and AAPL at $150 fetched on May 28 (fresh).
        data_map = {
            "portfolio_performance": [
                {
                    "portfolio_id": "p1",
                    "total_equity": 10000.0,
                    "cash_balance": 3500.0,
                    "date": "2026-05-25",
                    "portfolios": {"owner_id": "agent-1"},
                }
            ],
            "trades": [
                {
                    "portfolio_id": "p1",
                    "ticker": "IBM",
                    "signal": "BUY",
                    "quantity": 20,
                    "portfolios": {"owner_id": "agent-1"},
                },
                {
                    "portfolio_id": "p1",
                    "ticker": "AAPL",
                    "signal": "BUY",
                    "quantity": 10,
                    "portfolios": {"owner_id": "agent-1"},
                },
            ],
            "price_history": [
                {
                    "ticker": "IBM",
                    "price": 250.0,
                    "fetched_at": "2026-04-15T00:00:00",
                },
                {
                    "ticker": "AAPL",
                    "price": 150.0,
                    "fetched_at": "2026-05-28T00:00:00",
                },
            ],
        }

        fake_sb = FakeClient(data_map)

        # Call _do_nothing_return with our mock client
        ret, details = await metrics._do_nothing_return(
            fake_sb,
            owner_ids=frozenset({"agent-1"}),
            week_start=week_start,
            week_end=week_end,
        )

        # Expected return is 0.0% (3500 cash + 20 * 250 IBM + 10 * 150 AAPL = 10000 equity).
        # Before the fix, the return will be -50.0% because IBM is valued at 0.0.
        assert ret == pytest.approx(0.0)
        assert len(details) == 1

    @pytest.mark.asyncio
    async def test_do_nothing_pre_populates_price_history(self, monkeypatch):
        """Verify that _do_nothing_return pre-populates price history using MarketDataManager."""
        from autoresearch import metrics
        from execution.market_data import MarketDataManager

        week_start = date(2026, 5, 25)
        week_end = date(2026, 5, 31)

        # Track tickers called
        called_tickers = []
        called_days = []

        async def fake_get_history(self_mdm, ticker, days=14, force_refresh=False):
            called_tickers.append(ticker)
            called_days.append(days)
            return [{"price": 100.0, "fetched_at": "2026-05-29T00:00:00+00:00"}]

        monkeypatch.setattr(MarketDataManager, "get_history", fake_get_history)

        class FakeResponse:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def select(self, *args, **kwargs):
                return self

            def in_(self, *args, **kwargs):
                return self

            def gte(self, *args, **kwargs):
                return self

            def lte(self, *args, **kwargs):
                return self

            def lt(self, *args, **kwargs):
                return self

            def eq(self, *args, **kwargs):
                return self

            def order(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

            async def execute(self):
                return FakeResponse([])

        original_res_perf = FakeResponse(
            [
                {
                    "portfolio_id": "p1",
                    "total_equity": 10000.0,
                    "cash_balance": 3500.0,
                    "date": "2026-05-25",
                    "portfolios": {"owner_id": "agent-1"},
                }
            ]
        )

        original_res_trades = FakeResponse(
            [
                {
                    "portfolio_id": "p1",
                    "ticker": "AAPL",
                    "signal": "BUY",
                    "quantity": 10,
                    "portfolios": {"owner_id": "agent-1"},
                }
            ]
        )

        class AdvancedFakeQuery(FakeQuery):
            def __init__(self, table_name):
                self.table_name = table_name

            async def execute(self):
                if self.table_name == "portfolio_performance":
                    return original_res_perf
                elif self.table_name == "trades":
                    return original_res_trades
                return FakeResponse([])

        class AdvancedFakeClient:
            def table(self, name):
                return AdvancedFakeQuery(name)

        await metrics._do_nothing_return(
            AdvancedFakeClient(),
            owner_ids=frozenset({"agent-1"}),
            week_start=week_start,
            week_end=week_end,
        )

        assert "AAPL" in called_tickers
        assert len(called_tickers) == 1
        assert called_days[0] >= 14

    @pytest.mark.asyncio
    async def test_do_nothing_stale_price_logs_error(self, monkeypatch):
        """Verify that _do_nothing_return logs a critical error when using a stale price."""
        from autoresearch import metrics

        week_start = date(2026, 5, 25)
        week_end = date(2026, 5, 31)

        # Track logged errors
        logged_errors = []

        def fake_error(msg, *args):
            logged_errors.append(msg % args)

        monkeypatch.setattr(metrics.logger, "error", fake_error)

        class FakeResponse:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def select(self, *args, **kwargs):
                return self

            def in_(self, *args, **kwargs):
                return self

            def gte(self, *args, **kwargs):
                return self

            def lte(self, *args, **kwargs):
                return self

            def lt(self, *args, **kwargs):
                return self

            def eq(self, *args, **kwargs):
                return self

            def order(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

            async def execute(self):
                return FakeResponse([])

        original_res_perf = FakeResponse(
            [
                {
                    "portfolio_id": "p1",
                    "total_equity": 10000.0,
                    "cash_balance": 3500.0,
                    "date": "2026-05-25",
                    "portfolios": {"owner_id": "agent-1"},
                }
            ]
        )

        original_res_trades = FakeResponse(
            [
                {
                    "portfolio_id": "p1",
                    "ticker": "AAPL",
                    "signal": "BUY",
                    "quantity": 10,
                    "portfolios": {"owner_id": "agent-1"},
                }
            ]
        )

        price_res = FakeResponse([{"price": 100.0, "fetched_at": "2026-04-20T00:00:00+00:00"}])

        class AdvancedFakeQuery(FakeQuery):
            def __init__(self, table_name):
                self.table_name = table_name

            async def execute(self):
                if self.table_name == "portfolio_performance":
                    return original_res_perf
                elif self.table_name == "trades":
                    return original_res_trades
                elif self.table_name == "price_history":
                    return price_res
                return FakeResponse([])

        class AdvancedFakeClient:
            def table(self, name):
                return AdvancedFakeQuery(name)

        from execution.market_data import MarketDataManager

        # Use an async mock function
        async def fake_get_history(*args, **kwargs):
            pass

        monkeypatch.setattr(MarketDataManager, "get_history", fake_get_history)

        await metrics._do_nothing_return(
            AdvancedFakeClient(),
            owner_ids=frozenset({"agent-1"}),
            week_start=week_start,
            week_end=week_end,
        )

        assert any("CRITICAL METRIC ERROR" in err for err in logged_errors)

    @pytest.mark.asyncio
    async def test_do_nothing_includes_initial_and_end_prices(self, monkeypatch):
        """Verify that _do_nothing_return fetches and returns both start and end prices for held positions."""
        from autoresearch import metrics

        week_start = date(2026, 5, 25)
        week_end = date(2026, 5, 31)

        class FakeResponse:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def __init__(self, table_name):
                self.table_name = table_name
                self.lte_val = None

            def select(self, *args, **kwargs):
                return self

            def in_(self, *args, **kwargs):
                return self

            def gte(self, *args, **kwargs):
                return self

            def lte(self, col, val):
                self.lte_val = val
                return self

            def lt(self, *args, **kwargs):
                return self

            def eq(self, *args, **kwargs):
                return self

            def order(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

            async def execute(self):
                if self.table_name == "portfolio_performance":
                    return FakeResponse(
                        [
                            {
                                "portfolio_id": "p1",
                                "total_equity": 10000.0,
                                "cash_balance": 3500.0,
                                "date": "2026-05-25",
                                "portfolios": {"owner_id": "agent-1"},
                            }
                        ]
                    )
                elif self.table_name == "trades":
                    return FakeResponse(
                        [
                            {
                                "portfolio_id": "p1",
                                "ticker": "IBM",
                                "signal": "BUY",
                                "quantity": 20,
                                "portfolios": {"owner_id": "agent-1"},
                            }
                        ]
                    )
                elif self.table_name == "price_history":
                    # If fetching start price (lte week_start: 2026-05-25)
                    if self.lte_val and "2026-05-25" in self.lte_val:
                        return FakeResponse([{"price": 240.0, "fetched_at": "2026-05-25T00:00:00"}])
                    # If fetching end price (lte week_end: 2026-05-31)
                    if self.lte_val and "2026-05-31" in self.lte_val:
                        return FakeResponse([{"price": 250.0, "fetched_at": "2026-05-31T00:00:00"}])
                return FakeResponse([])

        class FakeClient:
            def table(self, name):
                return FakeQuery(name)

        from execution.market_data import MarketDataManager

        async def fake_get_history(*args, **kwargs):
            pass

        monkeypatch.setattr(MarketDataManager, "get_history", fake_get_history)

        ret, details = await metrics._do_nothing_return(
            FakeClient(),
            owner_ids=frozenset({"agent-1"}),
            week_start=week_start,
            week_end=week_end,
        )

        # Assert correct return return calculation
        assert ret == pytest.approx(-15.0)  # (3500 cash + 20 * 250 end_price - 10000) / 10000 * 100 = -15%
        assert "p1" in details
        positions = details["p1"]["positions"]
        assert "IBM" in positions
        ibm_pos = positions["IBM"]

        # Verify that start_price and start_value are populated correctly
        assert "start_price" in ibm_pos
        assert "start_value" in ibm_pos
        assert "start_date" in ibm_pos
        assert "end_date" in ibm_pos
        assert ibm_pos["qty"] == 20
        assert ibm_pos["start_price"] == 240.0
        assert ibm_pos["start_value"] == 4800.0
        assert ibm_pos["start_date"] == "2026-05-25 00:00"
        assert ibm_pos["end_price"] == 250.0
        assert ibm_pos["end_value"] == 5000.0
        assert ibm_pos["end_date"] == "2026-05-31 00:00"


# ---------------------------------------------------------------------------


class TestMigration:
    def test_research_output_is_jsonb(self):
        path = ENGINE_DIR.parent.parent / "supabase" / "migrations" / "20260510000000_create_prompt_experiments.sql"
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
            if isinstance(node, ast.ImportFrom) and node.module == "core.llm":
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

        async def _fake_check_safety(ws, we):
            return (False, "")

        monkeypatch.setattr(runner, "_check_safety", _fake_check_safety)

        async def _fake_active_var(**kw):
            return None

        async def _fake_baseline_metrics(**kw):
            return None

        monkeypatch.setattr(runner, "get_active_variant", _fake_active_var)
        monkeypatch.setattr(runner, "get_baseline_metrics", _fake_baseline_metrics)
        monkeypatch.setattr(runner, "save_variant", lambda **kw: "v-test")
        monkeypatch.setattr(runner, "revert_to_previous", lambda **kw: "v-prev")

        import asyncio

        asyncio.run(runner.run())

        assert len(evaluate_calls) == 1, f"evaluate_week must be called once, was called {len(evaluate_calls)} times"
        ws, we = evaluate_calls[0]
        assert isinstance(ws, date), f"week_start must be a date, got {type(ws)}"
        assert isinstance(we, date), f"week_end must be a date, got {type(we)}"


class TestCrashRecoveryContinuesGeneration:
    """When a crash occurs, runner must revert to baseline AND generate a new prompt variant."""

    def test_crash_recovery_deploys_new_variant(self, monkeypatch):
        from autoresearch import runner

        async def fake_evaluate(ws, we):
            return ("# report", {"score": -5.0}, "v-baseline")

        async def fake_research(report):
            from unittest.mock import MagicMock

            res = MagicMock()
            res.experiment_type = "incremental"
            res.change_description = "Recovery experiment"
            res.new_prompt_text = "new prompt"
            res.model_dump.return_value = {}
            return res

        async def fake_check_safety(ws, we):
            return (True, "Only 0 trades executed")

        async def fake_get_active_variant():
            return {"variant_tag": "v-baseline", "status": "active", "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT"}

        async def fake_get_baseline_metrics():
            return {"score": 1.0}

        save_calls = []
        revert_calls = []
        update_calls = []

        async def fake_save(**kw):
            save_calls.append(kw)
            return "v-new-recovery"

        async def fake_revert_to_previous():
            revert_calls.append("reverted")
            return "v-baseline"

        async def fake_update_metrics(tag, metrics):
            update_calls.append((tag, metrics))

        monkeypatch.setattr(runner, "evaluate_week", fake_evaluate)
        monkeypatch.setattr(runner, "run_research", fake_research)
        monkeypatch.setattr(runner, "_check_safety", fake_check_safety)
        monkeypatch.setattr(runner, "get_active_variant", fake_get_active_variant)
        monkeypatch.setattr(runner, "get_baseline_metrics", fake_get_baseline_metrics)
        monkeypatch.setattr(runner, "save_variant", fake_save)
        monkeypatch.setattr(runner, "revert_to_previous", fake_revert_to_previous)
        monkeypatch.setattr(runner, "update_variant_metrics", fake_update_metrics)

        import asyncio

        asyncio.run(runner.run())

        assert len(revert_calls) == 1, "Must revert to previous baseline upon crash"
        assert len(save_calls) == 1, "Must deploy new variant off restored baseline"
        assert save_calls[0]["parent_tag"] == "v-baseline"
        assert len(update_calls) == 0, "Must not overwrite restored baseline metrics with crashed week metrics"


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
        recorder = TrackedRecorder(
            data=[
                {"signal": "SELL", "realized_pnl": 100.0},
                {"signal": "SELL", "realized_pnl": -50.0},
                {"signal": "BUY", "realized_pnl": None},
            ]
        )

        def table(name):
            query_log.append(f"table:{name}")
            return recorder

        client.table.side_effect = table

        async def _fake_async_sb_safety():
            return client

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
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "path"
                and node.func.value.value.id == "sys"  # type: ignore[union-attr]
            ):
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
        assert len(save_calls) == 1, f"First bootstrap with no active prompt must save; got {len(save_calls)} calls"

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

    @pytest.mark.asyncio
    async def test_retries_when_proposed_prompt_is_identical_to_baseline(self, monkeypatch):
        from autoresearch import researcher

        baseline_text = "=== REASONING RIGOR ===\nBase strategy."
        new_modified_text = "=== REASONING RIGOR ===\nNew modified strategy."

        call_count = {"n": 0}

        async def fake_create(**kwargs):
            call_count["n"] += 1
            res = MagicMock()
            if call_count["n"] == 1:
                res.new_prompt_text = baseline_text
            else:
                res.new_prompt_text = new_modified_text
            return res

        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(researcher, "get_deepseek_client", lambda: fake_client)

        result = await researcher.run_research("# Test Report", baseline_prompt=baseline_text)
        assert result is not None
        assert result.new_prompt_text == new_modified_text
        assert call_count["n"] == 2, f"Expected 2 attempts (retry after identical baseline), got {call_count['n']}"


# ---------------------------------------------------------------------------
# Test C: activation gate — skip when beating baseline, activate when losing.
# ---------------------------------------------------------------------------


class TestActivationGate:
    """Every week must deploy a new prompt variant — no skipping, no gate.
    The meta-researcher always explores. When score < baseline, the active
    prompt is reverted to the baseline before the next experiment deploys."""

    @staticmethod
    def _make_result(**overrides) -> "PromptResearchResult":  # noqa: F821
        from autoresearch.researcher import PromptResearchResult

        defaults = dict(
            new_prompt_text="test prompt",
            selected_tools=["get_portfolio_ledger"],
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
        """Patch runner deps. Returns (runner, save_calls, revert_calls, active_variant_calls) for assertion."""
        from autoresearch import runner

        async def fake_evaluate(ws, we):
            return ("# report", self._make_score(exp_score), "v-baseline")

        async def fake_research(report):
            return self._make_result()

        async def fake_baseline_metrics():
            return self._make_score(1.0)

        async def fake_check(ws, we):
            return (False, "")

        async def fake_get_active_variant():
            return {"variant_tag": "v-active-mock", "status": "active", "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT"}

        active_variant_calls = []

        async def fake_update_variant_metrics(tag, metrics):
            active_variant_calls.append((tag, metrics))

        monkeypatch.setattr(runner, "evaluate_week", fake_evaluate)
        monkeypatch.setattr(runner, "run_research", fake_research)
        monkeypatch.setattr(runner, "_check_safety", fake_check)
        monkeypatch.setattr(runner, "get_baseline_metrics", fake_baseline_metrics)
        monkeypatch.setattr(runner, "get_active_variant", fake_get_active_variant)
        monkeypatch.setattr(runner, "update_variant_metrics", fake_update_variant_metrics)

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
        return runner, save_calls, revert_calls, active_variant_calls

    def test_deploys_when_score_beats_baseline(self, monkeypatch):
        """When score BEATS baseline, deploy AND do NOT revert to baseline."""
        runner, save_calls, revert_calls, active_calls = self._patch_runner(monkeypatch, exp_score=2.0)
        import asyncio

        asyncio.run(runner.run())
        assert len(save_calls) == 1, (
            f"Must deploy new variant when score beats baseline (2.0 > 1.0). "
            f"save_variant was called {len(save_calls)} times"
        )
        assert len(revert_calls) == 0, (
            f"Must NOT revert when score beats baseline. revert_to_baseline was called {len(revert_calls)} times"
        )
        # Check active variant got updated
        assert len(active_calls) == 1
        assert active_calls[0][0] == "v-active-mock"
        assert active_calls[0][1]["score"] == 2.0
        # Check new variant is empty metrics
        assert save_calls[0]["metrics"] == {}

    def test_deploys_and_reverts_when_below_baseline(self, monkeypatch):
        """When score < baseline, revert to baseline THEN deploy new variant."""
        runner, save_calls, revert_calls, active_calls = self._patch_runner(monkeypatch, exp_score=-0.5)
        import asyncio

        asyncio.run(runner.run())
        assert len(save_calls) == 1, (
            f"Must still deploy new variant after revert. save_variant was called {len(save_calls)} times"
        )
        assert len(revert_calls) == 1, (
            f"Must call revert_to_baseline when score (-0.5) < baseline (1.0). "
            f"revert_to_baseline was called {len(revert_calls)} times"
        )
        # Check active variant got updated
        assert len(active_calls) == 1
        assert active_calls[0][0] == "v-active-mock"
        assert active_calls[0][1]["score"] == -0.5
        # Check new variant is empty metrics
        assert save_calls[0]["metrics"] == {}

    def test_deploys_and_reverts_when_zero_score(self, monkeypatch):
        """Zero score (treading water) < baseline → revert + deploy."""
        runner, save_calls, revert_calls, active_calls = self._patch_runner(monkeypatch, exp_score=0.0)
        import asyncio

        asyncio.run(runner.run())
        assert len(save_calls) == 1, (
            f"Must deploy new variant even at zero score. save_variant was called {len(save_calls)} times"
        )
        assert len(revert_calls) == 1, (
            f"Must revert when score (0.0) < baseline (1.0). revert_to_baseline was called {len(revert_calls)} times"
        )
        # Check active variant got updated
        assert len(active_calls) == 1
        assert active_calls[0][0] == "v-active-mock"
        assert active_calls[0][1]["score"] == 0.0
        # Check new variant is empty metrics
        assert save_calls[0]["metrics"] == {}

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

        async def fake_get_active_variant():
            return {"variant_tag": "v-active-mock", "status": "active", "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT"}

        active_calls = []

        async def fake_update_variant_metrics(tag, metrics):
            active_calls.append((tag, metrics))

        monkeypatch.setattr(runner, "evaluate_week", fake_evaluate)
        monkeypatch.setattr(runner, "run_research", fake_research)
        monkeypatch.setattr(runner, "_check_safety", fake_check)
        monkeypatch.setattr(runner, "get_baseline_metrics", fake_baseline_metrics)
        monkeypatch.setattr(runner, "get_active_variant", fake_get_active_variant)
        monkeypatch.setattr(runner, "update_variant_metrics", fake_update_variant_metrics)

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
        assert len(active_calls) == 1
        assert active_calls[0][1]["score"] == 0.5
        assert save_calls[0]["metrics"] == {}


# ==============================================================================
# TDD: Fix price_history end-of-day filtering and baseline metrics ordering.
# ==============================================================================


class TestBaselineMetricsOrdering:
    """get_baseline_metrics must return the most recent baseline, not the oldest."""

    @pytest.mark.asyncio
    async def test_all_time_baseline_logic(self, monkeypatch):
        """get_all_time_baseline must find the variant with the highest score."""
        from autoresearch import prompt_store

        tools_output = {"selected_tools": ["get_portfolio_ledger"]}
        variants = [
            {"variant_tag": "v1", "metrics": {"score": 1.0}, "research_output": tools_output},
            {"variant_tag": "v2", "metrics": {"score": 3.0}, "research_output": tools_output},
            {"variant_tag": "v3", "metrics": {"score": 2.0}, "research_output": tools_output},
        ]

        client, recorder = _make_async_client(data=variants)
        monkeypatch.setattr(prompt_store, "get_async_supabase_client", lambda: asyncio.Future())

        # Manually override the client return to avoid real network call
        async def fake_client():
            return client

        monkeypatch.setattr(prompt_store, "get_async_supabase_client", fake_client)

        result = await prompt_store.get_all_time_baseline()
        assert result["variant_tag"] == "v2"
        assert result["metrics"]["score"] == 3.0

    @pytest.mark.asyncio
    async def test_all_time_baseline_ignores_missing_score(self, monkeypatch):
        """get_all_time_baseline must ignore variants without a score key in metrics."""
        from autoresearch import prompt_store

        tools_output = {"selected_tools": ["get_portfolio_ledger"]}
        variants = [
            {"variant_tag": "v_old", "metrics": {"composite": 0.5}, "research_output": tools_output},
            {"variant_tag": "v_demoted", "metrics": {"old_score": 0.4271}, "research_output": tools_output},
            {"variant_tag": "v_baseline", "metrics": {"score": 0.0}, "research_output": tools_output},
        ]

        client, recorder = _make_async_client(data=variants)
        monkeypatch.setattr(prompt_store, "get_async_supabase_client", lambda: asyncio.Future())

        async def fake_client():
            return client

        monkeypatch.setattr(prompt_store, "get_async_supabase_client", fake_client)

        result = await prompt_store.get_all_time_baseline()
        assert result is not None
        assert result["variant_tag"] == "v_baseline"
        assert result["metrics"]["score"] == 0.0


# ==============================================================================
# PHASE 2: New single-score formula — RED tests.
# ==============================================================================


class TestComputeScore:
    """compute_score(portfolio_return_pct, spy_return_pct, max_drawdown_pct)
    returns a dict with score, excess_return, max_drawdown."""

    def test_basic_formula(self):
        """score = 0.4*(portfolio - spy) + 0.4*(portfolio - do_nothing) + 0.2*(portfolio - bond) - (max_drawdown * 0.3)"""
        from autoresearch.metrics import compute_score

        result = compute_score(
            portfolio_return_pct=3.0,
            spy_return_pct=1.0,
            max_drawdown_pct=5.0,
            do_nothing_return_pct=0.0,
            bond_return_pct=0.0,
        )
        # excess_vs_spy = 2.0, excess_vs_do_nothing = 3.0, excess_vs_bond = 3.0
        # excess_return = 0.4(2.0) + 0.4(3.0) + 0.2(3.0) = 0.8 + 1.2 + 0.6 = 2.6
        # score = 2.6 - (5.0 * 0.3) = 2.6 - 1.5 = 1.1
        assert result["excess_return"] == pytest.approx(2.6)
        assert result["score"] == pytest.approx(1.1)

    def test_drawdown_penalty_reduces_score(self):
        """Higher drawdown must produce lower score for same excess return."""
        from autoresearch.metrics import compute_score

        low_dd = compute_score(portfolio_return_pct=3.0, spy_return_pct=1.0, max_drawdown_pct=2.0)
        high_dd = compute_score(portfolio_return_pct=3.0, spy_return_pct=1.0, max_drawdown_pct=10.0)
        assert low_dd["score"] > high_dd["score"]

    def test_negative_excess_gives_negative_score(self):
        """Underperforming SPY and Do-Nothing should produce negative score."""
        from autoresearch.metrics import compute_score

        result = compute_score(
            portfolio_return_pct=-2.0,
            spy_return_pct=1.0,
            max_drawdown_pct=2.0,
            do_nothing_return_pct=-1.0,
            bond_return_pct=0.0,
        )
        assert result["score"] < 0
        # excess_vs_spy = -3.0, excess_vs_do_nothing = -1.0, excess_vs_bond = -2.0
        # excess_return = 0.4(-3.0) + 0.4(-1.0) + 0.2(-2.0) = -1.2 - 0.4 - 0.4 = -2.0
        assert result["excess_return"] == pytest.approx(-2.0)

    def test_beat_spy_but_high_drawdown_can_be_negative(self):
        """Beating SPY is not enough — drawdown penalty can flip score negative."""
        from autoresearch.metrics import compute_score

        result = compute_score(
            portfolio_return_pct=3.0, spy_return_pct=1.0, max_drawdown_pct=25.0, do_nothing_return_pct=2.0
        )
        assert result["score"] < 0

    def test_zero_drawdown_positive_excess(self):
        """Perfect run: excess return with no drawdown."""
        from autoresearch.metrics import compute_score

        result = compute_score(
            portfolio_return_pct=5.0,
            spy_return_pct=1.0,
            max_drawdown_pct=0.0,
            do_nothing_return_pct=2.0,
            bond_return_pct=0.0,
        )
        # excess_vs_spy = 4.0, excess_vs_do_nothing = 3.0, excess_vs_bond = 5.0
        # excess_return = 0.4(4.0) + 0.4(3.0) + 0.2(5.0) = 1.6 + 1.2 + 1.0 = 3.8
        assert result["score"] == pytest.approx(3.8)
        assert result["max_drawdown"] == 0.0

    def test_excess_return_in_output(self):
        """Output dict must include excess_return, max_drawdown, do_nothing_return_pct for transparency."""
        from autoresearch.metrics import compute_score

        result = compute_score(
            portfolio_return_pct=2.0, spy_return_pct=0.5, max_drawdown_pct=3.0, do_nothing_return_pct=1.0
        )
        assert "excess_return" in result
        assert "max_drawdown" in result
        assert "score" in result
        assert "portfolio_return_pct" in result
        assert "spy_return_pct" in result
        assert "do_nothing_return_pct" in result
        assert "drawdown_penalty" in result

    def test_volatility_passed_through(self):
        """Verify volatility parameter is included in output dict."""
        from autoresearch.metrics import compute_score

        result = compute_score(portfolio_return_pct=5.0, spy_return_pct=1.0, max_drawdown_pct=0.0, volatility_pct=12.5)
        assert result["volatility"] == pytest.approx(12.5)

    def test_benchmark_triad_weighted_score_calculation(self):
        """Verify that score is computed using the Approach 3 Benchmark-Triad Weighted Model (40% SPY, 40% Do-Nothing, 20% Bond)."""
        from autoresearch.metrics import compute_score

        # Scenario: R_p = 1.5%, SPY = 0.5%, Do-Nothing = 0.3%, Bond = 0.1%, Drawdown = 2.0%
        # excess_vs_spy = 1.0%
        # excess_vs_do_nothing = 1.2%
        # excess_vs_bond = 1.4%
        # excess_return = 0.4(1.0) + 0.4(1.2) + 0.2(1.4) = 0.4 + 0.48 + 0.28 = 1.16
        # drawdown_penalty = 2.0 * 0.3 = 0.6
        # score = 1.16 - 0.6 = 0.56
        result = compute_score(
            portfolio_return_pct=1.5,
            spy_return_pct=0.5,
            max_drawdown_pct=2.0,
            bond_return_pct=0.1,
            dollar_return_pct=0.8,
            do_nothing_return_pct=0.3,
        )
        assert result["excess_return"] == pytest.approx(1.16)
        assert result["bond_return_pct"] == pytest.approx(0.1)
        assert result["dollar_return_pct"] == pytest.approx(0.8)
        assert result["opportunity_cost_penalty"] == pytest.approx(1.4)  # 1.5 - 0.1 = 1.4
        assert result["drawdown_penalty"] == pytest.approx(0.6)
        assert result["score"] == pytest.approx(0.56)

    def test_opportunity_cost_negative_when_underperforming_bond_hurdle(self):
        """Verify that underperforming the bond hurdle results in a negative risk-free excess value (0.0% vs 0.1% = -0.1%)."""
        from autoresearch.metrics import compute_score

        # Scenario: R_p = 0.0% (cash), SPY = 0.5%, Do-Nothing = 0.3%, Bond = 0.1%, Drawdown = 0.0%
        # excess_vs_spy = -0.5%
        # excess_vs_do_nothing = -0.3%
        # excess_vs_bond = -0.1%
        # excess_return = 0.4(-0.5) + 0.4(-0.3) + 0.2(-0.1) = -0.2 - 0.12 - 0.02 = -0.34
        result = compute_score(
            portfolio_return_pct=0.0,
            spy_return_pct=0.5,
            max_drawdown_pct=0.0,
            bond_return_pct=0.1,
            dollar_return_pct=2.0,
            do_nothing_return_pct=0.3,
        )
        assert result["excess_return"] == pytest.approx(-0.34)
        assert result["opportunity_cost_penalty"] == pytest.approx(-0.1)
        assert result["score"] == pytest.approx(-0.34)


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

        async def fake_get_active_prompt():
            return "PROMPT"

        async def fake_get_previous_variants(**kw):
            return []

        async def fake_get_all_time_baseline():
            return {"variant_tag": "v-best", "prompt_content": "BEST_PROMPT", "metrics": {"score": 3.0}}

        monkeypatch.setattr(evaluator, "get_active_prompt", fake_get_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", fake_get_previous_variants)
        monkeypatch.setattr(evaluator, "get_all_time_baseline", fake_get_all_time_baseline)

        report, _, _ = await evaluator.evaluate_week()
        assert "Baseline: 3.0" in report, f"Report must show max historical score as baseline.\nReport:\n{report}"

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

        async def fake_get_active_prompt():
            return "PROMPT"

        async def fake_get_previous_variants(**kw):
            return []

        async def fake_get_all_time_baseline():
            return {"variant_tag": "v-best", "prompt_content": "BEST_PROMPT", "metrics": {"score": 3.0}}

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

        async def fake_get_active_prompt():
            return "PROMPT"

        async def fake_get_previous_variants(**kw):
            return []

        async def fake_get_all_time_baseline():
            return None

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

        result = await metrics._daily_returns(client, {"gemini", "deepseek"}, date(2026, 5, 4), date(2026, 5, 5))

        # Gemini: (11000-10000)/10000 = +0.10
        # DeepSeek: (4000-5000)/5000 = -0.20
        # Average = -0.05
        assert len(result) == 1
        assert result[0] == pytest.approx(-0.05)

    @pytest.mark.asyncio
    async def test_single_agent_returns_unchanged(self):
        """Single agent: +10% daily → returns [0.10]"""
        from autoresearch import metrics

        rows = [
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
        ]

        client, recorder = _make_async_client(data=rows)

        from datetime import date

        result = await metrics._daily_returns(client, {"gemini"}, date(2026, 5, 4), date(2026, 5, 5))

        assert len(result) == 1
        assert result[0] == pytest.approx(0.10)

    @pytest.mark.asyncio
    async def test_two_agents_two_days(self):
        """Two agents, 3 days → 2 daily returns, each averaged."""
        from autoresearch import metrics

        rows = [
            # Day 1
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-04", "total_equity": 20000, "portfolios": {"owner_id": "deepseek"}},
            # Day 2: Gemini +10%, DeepSeek -10%
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-05", "total_equity": 18000, "portfolios": {"owner_id": "deepseek"}},
            # Day 3: Gemini -9.09%, DeepSeek +11.11%
            {"date": "2026-05-06", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-06", "total_equity": 20000, "portfolios": {"owner_id": "deepseek"}},
        ]

        client, recorder = _make_async_client(data=rows)

        from datetime import date

        result = await metrics._daily_returns(client, {"gemini", "deepseek"}, date(2026, 5, 4), date(2026, 5, 6))

        # Day 1→2: gemini=(11000-10000)/10000=0.10, deepseek=(18000-20000)/20000=-0.10 → avg=0.0
        # Day 2→3: gemini=(10000-11000)/11000≈-0.0909, deepseek=(20000-18000)/18000≈0.1111 → avg≈0.0101
        assert len(result) == 2
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.0101, abs=1e-4)

    @pytest.mark.asyncio
    async def test_missing_day_one_agent(self):
        """DeepSeek missing on Day 2 → use only Gemini's return."""
        from autoresearch import metrics

        rows = [
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-04", "total_equity": 5000, "portfolios": {"owner_id": "deepseek"}},
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
            # deepseek missing on 2026-05-05
        ]

        client, recorder = _make_async_client(data=rows)

        from datetime import date

        result = await metrics._daily_returns(client, {"gemini", "deepseek"}, date(2026, 5, 4), date(2026, 5, 5))

        # Only Gemini has data for both days: +10%
        assert len(result) == 1
        assert result[0] == pytest.approx(0.10)


class TestPromptConstraints:
    def test_split_prompt_exact(self):
        from core.llm.prompts import (
            CORE_ANALYSIS_SYSTEM_PROMPT,
            SYSTEM_PROMPT_CONSTRAINTS_FOOTER,
            SYSTEM_PROMPT_CONSTRAINTS_HEADER,
            SYSTEM_PROMPT_MUTABLE_STRATEGIES,
            split_prompt,
        )

        header, mutable, footer = split_prompt(CORE_ANALYSIS_SYSTEM_PROMPT)
        assert header == SYSTEM_PROMPT_CONSTRAINTS_HEADER
        assert footer == SYSTEM_PROMPT_CONSTRAINTS_FOOTER
        assert mutable == SYSTEM_PROMPT_MUTABLE_STRATEGIES

    def test_split_prompt_fuzzy(self):
        from core.llm.prompts import (
            SYSTEM_PROMPT_CONSTRAINTS_FOOTER,
            SYSTEM_PROMPT_CONSTRAINTS_HEADER,
            split_prompt,
        )

        # Create a modified prompt where the mutable strategies section is modified
        modified_mutable = (
            '=== REASONING RIGOR: THE "5 WHYS" TECHNIQUE ===\nSome modified strategy instructions here.\n\n'
        )
        full_prompt = SYSTEM_PROMPT_CONSTRAINTS_HEADER + modified_mutable + SYSTEM_PROMPT_CONSTRAINTS_FOOTER

        header, mutable, footer = split_prompt(full_prompt)
        assert header == SYSTEM_PROMPT_CONSTRAINTS_HEADER
        assert footer == SYSTEM_PROMPT_CONSTRAINTS_FOOTER
        assert mutable == modified_mutable

    def test_recombine_prompt_matches_original(self):
        from core.llm.prompts import (
            CORE_ANALYSIS_SYSTEM_PROMPT,
            split_prompt,
        )

        header, mutable, footer = split_prompt(CORE_ANALYSIS_SYSTEM_PROMPT)
        recombined = header + mutable + footer
        assert recombined == CORE_ANALYSIS_SYSTEM_PROMPT

    def test_program_mentions_reasoning_frameworks(self):
        from autoresearch.researcher import _load_research_program

        program_text = _load_research_program()
        assert "MECE" in program_text
        assert "IS / IS NOT" in program_text
        assert "Ishikawa" in program_text
        assert "5 Whys" in program_text


class TestPullBaselineIsolation:
    @pytest.mark.asyncio
    async def test_get_all_time_baseline_isolates_pull_variants(self):
        """Verify get_all_time_baseline ignores pre-pull variants (missing selected_tools) and returns best pull variant."""
        from unittest.mock import patch

        from autoresearch import prompt_store

        rows = [
            {
                "variant_tag": "v_pre_pull",
                "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
                "metrics": {"score": 4.2006},
                "research_output": None,  # Pre-pull (push model)
            },
            {
                "variant_tag": "v_pull",
                "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
                "metrics": {"score": -4.5858},
                "research_output": {"selected_tools": ["get_portfolio_ledger", "get_todays_news_menu"]},  # Pull model
            },
        ]

        client, recorder = _make_async_client(data=rows)

        with patch("autoresearch.prompt_store.get_async_supabase_client", return_value=client):
            baseline = await prompt_store.get_all_time_baseline("CORE_ANALYSIS_SYSTEM_PROMPT")

        assert baseline is not None
        assert baseline["variant_tag"] == "v_pull"
        assert baseline["metrics"]["score"] == -4.5858


class TestTradeRejectionAnalysis:
    @pytest.mark.asyncio
    async def test_execute_get_verifier_rejections_tool(self):
        """Test that execute_get_verifier_rejections_tool queries decisions and formats output."""
        from unittest.mock import patch

        from core.llm import tools

        rows = [
            {
                "id": "dec-1",
                "ticker": "AAPL",
                "signal": "BUY",
                "status": "REJECTED_VERIFICATION",
                "reasoning": "Agent thesis: high momentum",
                "model_name": "gpt-4o",
                "metadata": '{"reason": "Verifier rejected: Position size exceeds risk limit"}',
                "created_at": "2026-08-01T10:00:00",
            }
        ]

        client, _ = _make_async_client(data=rows)
        with patch("core.llm.tools.get_async_supabase_client", return_value=client):
            output = await tools.execute_get_verifier_rejections_tool(ticker="AAPL", limit=5, model_name="gpt-4o")

        assert "REJECTED_VERIFICATION" in output
        assert "AAPL" in output
        assert "Verifier rejected: Position size exceeds risk limit" in output

    @pytest.mark.asyncio
    async def test_fetch_trade_rejections_computes_stats(self):
        """Test fetch_trade_rejections computes counts, breakdown, and extracts reasons."""
        from unittest.mock import patch

        from autoresearch.metrics import fetch_trade_rejections

        rows = [
            {
                "id": "d1",
                "ticker": "NVDA",
                "signal": "BUY",
                "status": "VALIDATED",
                "reasoning": "Good earnings",
                "model_name": "deepseek_chat",
                "metadata": {"reason": "Passed verifier"},
                "created_at": "2026-08-02T10:00:00",
            },
            {
                "id": "d2",
                "ticker": "TSLA",
                "signal": "SELL",
                "status": "REJECTED_VERIFICATION",
                "reasoning": "Overvalued EV market",
                "model_name": "deepseek_chat",
                "metadata": {"reason": "Verifier rejected: Lacks contrarian hedge analysis"},
                "created_at": "2026-08-03T10:00:00",
            },
            {
                "id": "d3",
                "ticker": "AMD",
                "signal": "BUY",
                "status": "REJECTED_MARGIN",
                "reasoning": "Buying power check",
                "model_name": "deepseek_chat",
                "metadata": '{"reason": "Insufficient buying power"}',
                "created_at": "2026-08-04T10:00:00",
            },
        ]

        client, _ = _make_async_client(data=rows)
        with patch("autoresearch.metrics.get_async_supabase_client", return_value=client):
            stats = await fetch_trade_rejections(
                client,
                week_start=date(2026, 8, 1),
                week_end=date(2026, 8, 7),
            )

        assert stats["total_decisions"] == 3
        assert stats["validated_count"] == 1
        assert stats["rejected_count"] == 2
        assert stats["rejection_rate_pct"] == 66.67
        assert stats["status_breakdown"]["REJECTED_VERIFICATION"] == 1
        assert stats["status_breakdown"]["REJECTED_MARGIN"] == 1
        assert len(stats["rejection_details"]) == 2
        assert stats["rejection_details"][0]["ticker"] in ("TSLA", "AMD")

    @pytest.mark.asyncio
    async def test_evaluate_week_includes_trade_rejection_section(self, monkeypatch):
        """Test evaluate_week includes # Trade Rejection & Verifier Analysis in report and metrics."""
        from autoresearch import evaluator, metrics

        fake_rejection_stats = {
            "total_decisions": 10,
            "validated_count": 6,
            "rejected_count": 4,
            "rejection_rate_pct": 40.0,
            "status_breakdown": {"REJECTED_VERIFICATION": 3, "REJECTED_MARGIN": 1},
            "rejection_details": [
                {
                    "ticker": "MSFT",
                    "signal": "BUY",
                    "status": "REJECTED_VERIFICATION",
                    "model_name": "deepseek_chat",
                    "reason": "Verifier rejected: Missing stop-loss strategy",
                    "agent_reasoning": "Strong cloud revenue growth",
                }
            ],
        }

        async def mock_fetch_trade_rejections(*args, **kwargs):
            return fake_rejection_stats

        async def mock_spy_returns(*args, **kwargs):
            return [0.01, 0.005]

        async def mock_compute_wall_street_metrics(*args, **kwargs):
            return {
                "total_return_pct": 2.5,
                "max_drawdown": 0.01,
                "volatility": 0.05,
                "do_nothing_return_pct": 1.0,
                "portfolio_details": {},
            }

        async def mock_active_prompt(*args, **kwargs):
            return "Test Prompt"

        async def mock_previous_variants(*args, **kwargs):
            return []

        async def mock_all_time_baseline(*args, **kwargs):
            return None

        monkeypatch.setattr(evaluator, "fetch_trade_rejections", mock_fetch_trade_rejections)
        monkeypatch.setattr(metrics, "_spy_returns", mock_spy_returns)
        monkeypatch.setattr(metrics, "compute_wall_street_metrics", mock_compute_wall_street_metrics)
        monkeypatch.setattr(evaluator, "get_active_prompt", mock_active_prompt)
        monkeypatch.setattr(evaluator, "get_previous_variants", mock_previous_variants)
        monkeypatch.setattr(evaluator, "get_all_time_baseline", mock_all_time_baseline)

        async def mock_bond_yield(*args, **kwargs):
            return 4.5

        async def mock_dollar_return(*args, **kwargs):
            return 0.0

        from unittest.mock import AsyncMock

        monkeypatch.setattr(evaluator, "get_async_supabase_client", AsyncMock(return_value=_make_async_client()[0]))
        monkeypatch.setattr(metrics, "get_async_supabase_client", AsyncMock(return_value=_make_async_client()[0]))
        monkeypatch.setattr(evaluator, "_fetch_actual_bond_yield", mock_bond_yield)
        monkeypatch.setattr(evaluator, "_fetch_dollar_index_return", mock_dollar_return)

        report, score_result, baseline_tag = await evaluator.evaluate_week()

        assert "# Trade Rejection & Verifier Analysis" in report
        assert "Total Decisions Proposed: 10" in report
        assert "Overall Trade Rejection Rate: 40.00%" in report
        assert "REJECTED_VERIFICATION: 3" in report
        assert "Verifier rejected: Missing stop-loss strategy" in report
        assert score_result["rejection_stats"] == fake_rejection_stats

    def test_selected_tools_allows_get_verifier_rejections(self):
        """Verify PromptResearchResult accepts get_verifier_rejections as a valid selected tool."""
        from autoresearch.researcher import PromptResearchResult

        res = PromptResearchResult(
            new_prompt_text="New Strategy",
            selected_tools=["get_portfolio_ledger", "get_verifier_rejections"],
            change_description="Added verifier rejection lookup tool",
            experiment_type="incremental",
            research_reasoning="Allow agent to query past verifier rejection reasons",
            confidence=80,
        )
        assert "get_verifier_rejections" in res.selected_tools
