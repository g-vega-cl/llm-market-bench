"""Hermetic tests for the materialised recipe public-stats writer."""

from __future__ import annotations

from types import SimpleNamespace

from recipes.public_stats import (
    build_bot_leaderboard_window_rows,
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


def test_build_bot_leaderboard_window_rows_computes_all_four_windows_and_laplace_consistency():
    from datetime import UTC, datetime

    now = datetime(2026, 11, 25, 16, 0, tzinfo=UTC)
    recipe = {
        "id": "bot-1",
        "name": "Momentum Hunter",
        "is_live": False,
        "paper_cash": 10300.0,
        "paper_positions": [
            {"ticker": "NVDA", "shares": 10, "entry_price": 100.0, "current_price": 110.0, "unrealized_pnl_net": 100.0}
        ],
        "paper_trades": [
            {"ticker": "AAPL", "exit_time": "2026-11-22 15:30 ET", "pnl_net": 200.0},
            {"ticker": "AMD", "exit_time": "2026-10-01 15:30 ET", "pnl_net": -50.0},
        ],
        "paper_equity_curve": [
            {"time": "2026-10-01 15:30 ET", "equity": 9950.0},
            {"time": "2026-11-20 15:30 ET", "equity": 10100.0},
            {"time": "2026-11-22 15:30 ET", "equity": 10400.0},
        ],
    }

    rows = build_bot_leaderboard_window_rows(recipe, now_utc=now)
    by_window = {row["time_window_days"]: row for row in rows}
    assert set(by_window) == {7, 30, 90, 0}

    # 30d: anchored to prior close 2026-10-01 ($9,950.00), current $10,400 -> +4.52%
    w30 = by_window[30]
    assert w30["return_pct"] == 4.52
    # 1 closed win in 30d + 1 open win = 2/2 = 100.0%
    assert w30["win_rate"] == 100.0
    assert w30["total_trades"] == 1
    # 2 positive return days (10100 > 9950, 10400 > 10100) -> Laplace (2+2)/(2+4) = 66.67%
    assert w30["consistency_score"] == 66.67
    # The raw counts behind consistency must be exposed so the UI can show "2/2".
    assert w30["up_days"] == 2
    assert w30["active_days"] == 2
    assert w30["has_activity"] is True

    # All-Time (0): includes older Oct 1 trade (-50.0): 1 win + 1 loss closed + 1 open win = 2/3 = 66.67%
    w_all = by_window[0]
    assert w_all["total_trades"] == 2
    assert w_all["realized_pnl"] == 150.0
    assert w_all["win_rate"] == 66.67


def test_build_bot_leaderboard_window_rows_marks_idle_bot_inactive():
    idle = {
        "id": "bot-idle",
        "name": "Draft Bot",
        "is_live": False,
        "paper_cash": 10000.0,
        "paper_positions": [],
        "paper_trades": [],
        "paper_equity_curve": [],
    }
    rows = build_bot_leaderboard_window_rows(idle)
    assert all(r["has_activity"] is False and r["win_rate"] is None and r["return_pct"] == 0.0 for r in rows)
