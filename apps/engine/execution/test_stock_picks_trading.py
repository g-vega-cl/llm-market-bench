"""Hermetic tests for the Daily Stock Picker Arena system portfolios (sys-picks-*)."""

import os
import sys
from uuid import uuid4

import pytest

sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from datetime import datetime
from zoneinfo import ZoneInfo

from execution.stock_picks_trading import (
    PICKS_MODEL_TRACKS,
    SYS_PICKS_OWNER_PREFIX,
    SYS_PICKS_START_DATE,
    execute_picks_entries,
    execute_picks_exits,
    picks_owner_id,
    within_entry_window,
)

SESSION = "2026-11-19"
LONG_TICKERS = ["AAA", "BBB", "CCC"]
SHORT_TICKERS = ["DDD", "EEE", "FFF"]


class _Response:
    def __init__(self, data):
        self.data = data


class _Query:
    """Minimal PostgREST-style query builder over an in-memory table store."""

    def __init__(self, store, table):
        self.store = store
        self.table = table
        self.filters = []
        self.action = "select"
        self.payload = None
        self.conflict = None

    def select(self, *_args, **_kwargs):
        self.action = "select"
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.action = "upsert"
        self.payload = payload
        self.conflict = on_conflict
        return self

    def delete(self):
        self.action = "delete"
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, set(values)))
        return self

    def is_(self, column, value):
        self.filters.append(("is", column, value))
        return self

    def match(self, mapping):
        for key, value in mapping.items():
            self.filters.append(("eq", key, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def _matches(self, row):
        for op, column, value in self.filters:
            cell = row.get(column)
            if op == "eq" and str(cell) != str(value):
                return False
            if op == "in" and cell not in value:
                return False
            if op == "is" and str(value).lower() == "null" and cell is not None:
                return False
        return True

    def execute(self):
        rows = self.store.rows.setdefault(self.table, [])
        if self.action == "select":
            return _Response([dict(r) for r in rows if self._matches(r)])
        if self.action == "insert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            inserted = []
            for item in items:
                row = dict(item)
                row.setdefault("id", str(uuid4()))
                rows.append(row)
                inserted.append(dict(row))
            return _Response(inserted)
        if self.action == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self.payload)
                    updated.append(dict(row))
            return _Response(updated)
        if self.action == "upsert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            keys = [k.strip() for k in (self.conflict or "id").split(",")]
            stored = []
            for item in items:
                match = next((r for r in rows if all(str(r.get(k)) == str(item.get(k)) for k in keys)), None)
                if match is not None:
                    match.update(item)
                    stored.append(dict(match))
                else:
                    row = dict(item)
                    row.setdefault("id", str(uuid4()))
                    rows.append(row)
                    stored.append(dict(row))
            return _Response(stored)
        if self.action == "delete":
            removed = [dict(r) for r in rows if self._matches(r)]
            self.store.rows[self.table] = [r for r in rows if not self._matches(r)]
            return _Response(removed)
        raise AssertionError(f"unsupported action {self.action}")


class FakeSupabase:
    def __init__(self, rows=None):
        self.rows = {name: [dict(r) for r in data] for name, data in (rows or {}).items()}

    def table(self, name):
        return _Query(self, name)

    def count(self, name, **filters):
        return len([r for r in self.rows.get(name, []) if all(str(r.get(k)) == str(v) for k, v in filters.items())])


class StubPortfolio:
    def __init__(self, owner_id, pid, cash=10000.0):
        self.owner_id = owner_id
        self.id = pid
        self.cash_balance = cash
        self.total_equity = cash


def _seed_session(store, session=SESSION, models=PICKS_MODEL_TRACKS):
    baskets = store.rows.setdefault("daily_stock_baskets", [])
    picks = store.rows.setdefault("daily_stock_picks", [])
    for index, model in enumerate(models):
        basket_id = f"basket-{index}"
        baskets.append(
            {"id": basket_id, "target_date": session, "model_name": model, "status": "pending"}
        )
        for rank, ticker in enumerate(LONG_TICKERS, start=1):
            picks.append(
                {
                    "id": f"pick-{index}-up-{rank}",
                    "basket_id": basket_id,
                    "target_date": session,
                    "model_name": model,
                    "ticker": ticker,
                    "direction": "UP",
                    "rank": rank,
                    "confidence": 70.0,
                    "status": "pending",
                }
            )
        for rank, ticker in enumerate(SHORT_TICKERS, start=1):
            picks.append(
                {
                    "id": f"pick-{index}-down-{rank}",
                    "basket_id": basket_id,
                    "target_date": session,
                    "model_name": model,
                    "ticker": ticker,
                    "direction": "DOWN",
                    "rank": rank,
                    "confidence": 70.0,
                    "status": "pending",
                }
            )
    return store


def _portfolio_getter():
    created: dict[str, StubPortfolio] = {}

    async def _get(owner_id: str) -> StubPortfolio:
        if owner_id not in created:
            created[owner_id] = StubPortfolio(owner_id, f"pf-{len(created)}")
        return created[owner_id]

    return created, _get


def _open_price_map(price=100.0, tickers=None):
    return {t: price for t in (tickers or LONG_TICKERS + SHORT_TICKERS)}


def test_entry_window_bounds():
    et = ZoneInfo("America/New_York")
    assert within_entry_window(datetime(2026, 11, 19, 9, 30, tzinfo=et)) is False
    assert within_entry_window(datetime(2026, 11, 19, 9, 31, tzinfo=et)) is True
    assert within_entry_window(datetime(2026, 11, 19, 10, 0, tzinfo=et)) is True
    assert within_entry_window(datetime(2026, 11, 19, 10, 1, tzinfo=et)) is False


def test_owner_id_preserves_model_case():
    assert SYS_PICKS_OWNER_PREFIX == "sys-picks-"
    assert picks_owner_id("MiniMax-M3.1-Flash") == "sys-picks-MiniMax-M3.1-Flash"
    assert picks_owner_id("consensus") == "sys-picks-consensus"
    assert SYS_PICKS_START_DATE == "2026-11-19"


@pytest.mark.asyncio
async def test_picks_entries_create_six_legs_per_basket():
    store = _seed_session(FakeSupabase())
    portfolios, getter = _portfolio_getter()

    result = await execute_picks_entries(
        SESSION,
        price_map=_open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "success"
    assert len(portfolios) == 4
    assert set(portfolios) == {picks_owner_id(m) for m in PICKS_MODEL_TRACKS}

    trades = store.rows["trades"]
    assert len(trades) == 24  # 4 baskets x 6 legs
    assert len([t for t in trades if t["signal"] == "BUY"]) == 12
    assert len([t for t in trades if t["signal"] == "SHORT"]) == 12
    assert len(store.rows["portfolio_positions"]) == 12  # longs only
    assert all(t["executed_at"] == "2026-11-19T14:30:00Z" for t in trades)
    assert all(t["decision_id"] for t in trades)

    # $10,000 equity -> 50% long budget -> 3 legs, $1,666.67 each, entry 100 * (1 + 5bps)
    entry_long = 100.0 * 1.0005
    shares = int((5000.0 / 3) // entry_long)
    assert shares == 16
    for portfolio in portfolios.values():
        assert portfolio.cash_balance == pytest.approx(10000.0 - 3 * shares * entry_long)
        assert portfolio.total_equity == pytest.approx(10000.0)


@pytest.mark.asyncio
async def test_picks_entries_are_idempotent():
    store = _seed_session(FakeSupabase())
    _, getter = _portfolio_getter()

    first = await execute_picks_entries(
        SESSION,
        price_map=_open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )
    second = await execute_picks_entries(
        SESSION,
        price_map=_open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert first["status"] == "success"
    assert second["status"] == "skipped"
    assert len(store.rows["trades"]) == 24


@pytest.mark.asyncio
async def test_picks_entries_before_inception_are_skipped():
    store = _seed_session(FakeSupabase(), session="2026-11-18")
    _, getter = _portfolio_getter()

    result = await execute_picks_entries(
        "2026-11-18",
        price_map=_open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "skipped"
    assert store.count("trades") == 0


@pytest.mark.asyncio
async def test_picks_entry_skips_leg_without_price():
    store = _seed_session(FakeSupabase())
    _, getter = _portfolio_getter()
    price_map = _open_price_map()
    price_map.pop("CCC")

    result = await execute_picks_entries(
        SESSION,
        price_map=price_map,
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "success"
    assert len(store.rows["trades"]) == 20  # 4 baskets x 5 priced legs
    assert not [t for t in store.rows["trades"] if t["ticker"] == "CCC"]


@pytest.mark.asyncio
async def test_picks_exit_realizes_pnl_and_snapshots_performance():
    store = _seed_session(FakeSupabase())
    portfolios, getter = _portfolio_getter()
    await execute_picks_entries(
        SESSION,
        price_map=_open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    result = await execute_picks_exits(
        SESSION,
        price_map=_open_price_map(price=101.0),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "success"
    exit_trades = [t for t in store.rows["trades"] if t["signal"] in ("SELL", "COVER")]
    assert len(exit_trades) == 24
    assert all(t["executed_at"] == "2026-11-19T21:00:00Z" for t in exit_trades)
    assert all(t["realized_pnl"] is not None for t in exit_trades)

    entry_trades = [t for t in store.rows["trades"] if t["signal"] in ("BUY", "SHORT")]
    assert all(t["realized_pnl"] is not None for t in entry_trades)
    assert store.count("portfolio_positions") == 0

    entry_long = 100.0 * 1.0005
    exit_long = 101.0 * (1 - 0.0005)
    long_pnl = (exit_long - entry_long) * 16
    entry_short = 100.0 * (1 - 0.0005)
    exit_short = 101.0 * (1 + 0.0005)
    short_pnl = (entry_short - exit_short) * 16

    expected_cash = (10000.0 - 3 * 16 * entry_long) + 3 * 16 * exit_long + 3 * short_pnl
    for portfolio in portfolios.values():
        assert portfolio.cash_balance == pytest.approx(expected_cash)
        assert portfolio.total_equity == pytest.approx(expected_cash)

    perf = store.rows["portfolio_performance"]
    assert len(perf) == 4
    assert all(p["date"] == SESSION for p in perf)
    assert all(p["total_equity"] == pytest.approx(expected_cash) for p in perf)
    assert long_pnl > 0 > short_pnl


@pytest.mark.asyncio
async def test_picks_exit_without_open_legs_is_skipped():
    store = _seed_session(FakeSupabase())
    _, getter = _portfolio_getter()

    result = await execute_picks_exits(
        SESSION,
        price_map=_open_price_map(price=101.0),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "skipped"
    assert store.count("trades") == 0
