"""Hermetic tests for the materialised recipe public-stats writer."""

from __future__ import annotations

from types import SimpleNamespace

from recipes.public_stats import (
    build_last_action,
    build_public_stats,
    parse_equity_curve,
    refresh_public_stats,
    return_pct,
    spy_return_pct,
)


class _FakeQuery:
    """Chainable PostgREST stub: every filter is a no-op, execute returns fixed rows."""

    def __init__(self, data, recorder=None):
        self._data = data
        self._recorder = recorder

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def delete(self, **kwargs):
        return self

    def insert(self, rows, **kwargs):
        return self

    def upsert(self, rows, **kwargs):
        if self._recorder is not None:
            self._recorder.append(list(rows))
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _FakeClient:
    def __init__(self, tables):
        self._tables = tables
        self.upserted: list[list[dict]] = []

    def table(self, name):
        if name == "recipe_public_stats":
            return _FakeQuery([], recorder=self.upserted)
        return _FakeQuery(self._tables.get(name, []))


def test_parse_equity_curve_ignores_unreadable_points():
    curve = [
        {"time": "2026-11-10 09:30 ET", "equity": 10050.0},
        {"time": "bad-label", "equity": 10100.0},
        {"time": "2026-11-11 09:30 ET", "equity": None},
        {"time": "2026-11-12 09:30 ET", "equity": 9900.0},
    ]
    assert parse_equity_curve(curve) == [("2026-11-10", 10050.0), ("2026-11-12", 9900.0)]


def test_return_pct_is_first_to_last_point():
    curve = [{"time": "2026-11-10 09:30 ET", "equity": 10000.0}, {"time": "2026-11-24 15:30 ET", "equity": 10250.0}]
    assert return_pct(curve) == 2.5


def test_return_pct_is_none_for_single_point_or_empty_curve():
    assert return_pct([]) is None
    assert return_pct([{"time": "2026-11-10 09:30 ET", "equity": 10000.0}]) is None


def test_losing_recipe_reports_a_negative_return():
    """The board publishes losers, so a negative number must survive the builder."""
    curve = [{"time": "2026-11-10 09:30 ET", "equity": 10000.0}, {"time": "2026-11-14 09:30 ET", "equity": 9500.0}]
    assert return_pct(curve) == -5.0


def test_spy_return_uses_matching_window_closes():
    rows = [
        {"price": 500.0, "fetched_at": "2026-11-10T14:00:00+00:00"},
        {"price": 510.0, "fetched_at": "2026-11-14T14:00:00+00:00"},
    ]
    assert spy_return_pct(rows, "2026-11-10", "2026-11-14") == 2.0


def test_spy_return_is_none_without_a_matching_start_close():
    rows = [{"price": 510.0, "fetched_at": "2026-11-14T14:00:00+00:00"}]
    assert spy_return_pct(rows, "2026-11-10", "2026-11-14") is None


def test_build_last_action_prefers_the_first_executed_signal():
    result = {
        "executed_signals": [{"action": "EXIT", "ticker": "nvda", "price": 181.234}],
        "output": "  Thesis\nbroken:\tguidance cut  ",
    }
    assert build_last_action(result) == {
        "action": "EXIT",
        "ticker": "NVDA",
        "price": 181.234,
        "reason": "Thesis broken: guidance cut",
    }


def test_build_last_action_is_empty_without_signals():
    assert build_last_action({"executed_signals": []}) == {}
    assert build_last_action(None) == {}


def test_build_public_stats_counts_trades_and_positions():
    recipe = {
        "id": "r-1",
        "name": "Chip Momentum",
        "is_live": True,
        "paper_trades": [{"ticker": "NVDA"}, {"ticker": "AMD"}],
        "paper_positions": [{"ticker": "NVDA"}],
        "paper_equity_curve": [
            {"time": "2026-11-10 09:30 ET", "equity": 10000.0},
            {"time": "2026-11-14 15:30 ET", "equity": 10300.0},
        ],
        "updated_at": "2026-11-14T20:00:00+00:00",
    }
    stats = build_public_stats(
        recipe,
        spy_rows=[
            {"price": 500.0, "fetched_at": "2026-11-10T14:00:00+00:00"},
            {"price": 505.0, "fetched_at": "2026-11-14T14:00:00+00:00"},
        ],
        last_job_result={"executed_signals": [{"action": "BUY", "ticker": "NVDA", "price": 120.0}]},
        runs_today=2,
        resolved_model="qwen3.8-27b",
    )
    assert stats["recipe_id"] == "r-1"
    assert stats["return_pct"] == 3.0
    assert stats["spy_return_pct"] == 1.0
    assert stats["trade_count"] == 2
    assert stats["open_positions"] == 1
    assert stats["runs_today"] == 2
    assert stats["first_equity_date"] == "2026-11-10"
    assert stats["last_equity_date"] == "2026-11-14"
    assert stats["last_action"]["ticker"] == "NVDA"
    assert stats["resolved_model"] == "qwen3.8-27b"


def test_refresh_public_stats_upserts_one_row_per_live_recipe():
    recipe_row = {
        "id": "r-1",
        "name": "Chip Momentum",
        "is_live": True,
        "paper_trades": [],
        "paper_positions": [],
        "paper_equity_curve": [
            {"time": "2026-11-10 09:30 ET", "equity": 10000.0},
            {"time": "2026-11-14 15:30 ET", "equity": 10100.0},
        ],
        "updated_at": "2026-11-14T20:00:00+00:00",
    }
    queue_rows = [
        {
            "recipe_id": "r-1",
            "created_at": "2026-11-14T15:30:00+00:00",
            "result_json": {
                "executed_signals": [{"action": "BUY", "ticker": "AMD", "price": 98.5}],
                "resolved_model": "qwen3.8-27b",
            },
        }
    ]
    client = _FakeClient(
        {
            "strategy_recipes": [recipe_row],
            "price_history": [
                {"price": 500.0, "fetched_at": "2026-11-10T14:00:00+00:00"},
                {"price": 505.0, "fetched_at": "2026-11-14T14:00:00+00:00"},
            ],
            "recipe_execution_queue": queue_rows,
        }
    )

    result = refresh_public_stats(client)

    assert result == {"live_recipes": 1, "rows_written": 1, "rows_pruned": 0}
    assert len(client.upserted) == 1
    row = client.upserted[0][0]
    assert row["recipe_id"] == "r-1"
    assert row["return_pct"] == 1.0
    assert row["resolved_model"] == "qwen3.8-27b"
    assert row["last_action"]["ticker"] == "AMD"
