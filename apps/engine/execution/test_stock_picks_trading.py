"""Hermetic tests for the Daily Stock Picker Arena system portfolios (sys-picks-*)."""

import os
import sys

import pytest

sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from datetime import datetime
from zoneinfo import ZoneInfo

from execution.picks_fakes import (
    SESSION,
    FakeSupabase,
    open_price_map,
    portfolio_getter,
    seed_session,
    stored_portfolio_getter,
)
from execution.stock_picks_trading import (
    PICKS_MODEL_TRACKS,
    SYS_PICKS_OWNER_PREFIX,
    SYS_PICKS_START_DATE,
    execute_picks_entries,
    execute_picks_exits,
    picks_owner_id,
    within_entry_window,
)


@pytest.fixture(autouse=True)
def alpaca_mirror(monkeypatch):
    """Keep tests off the shared Alpaca paper account and record the mirror calls."""
    from execution import stock_picks_trading

    mirrored: dict[str, list[dict]] = {}

    async def _record(legs, owner_id):
        mirrored.setdefault(owner_id, []).extend(legs)

    monkeypatch.setattr(stock_picks_trading, "_mirror_long_legs_to_alpaca", _record)
    return mirrored


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
async def test_picks_entries_create_six_legs_per_basket(alpaca_mirror):
    store = seed_session(FakeSupabase())
    portfolios, getter = portfolio_getter()

    result = await execute_picks_entries(
        SESSION,
        price_map=open_price_map(),
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

    # All legs are handed to the mirror, which drops shorts; long legs carry the order.
    mirrored_legs = [leg for legs in alpaca_mirror.values() for leg in legs]
    assert len(mirrored_legs) == 24
    assert len([leg for leg in mirrored_legs if leg["side"] == "LONG"]) == 12
    assert all(leg["trade_id"] for leg in mirrored_legs if leg["side"] == "LONG")


@pytest.mark.asyncio
async def test_picks_entries_are_idempotent():
    store = seed_session(FakeSupabase())
    _, getter = portfolio_getter()

    first = await execute_picks_entries(
        SESSION,
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )
    second = await execute_picks_entries(
        SESSION,
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert first["status"] == "success"
    assert second["status"] == "skipped"
    assert len(store.rows["trades"]) == 24


@pytest.mark.asyncio
async def test_picks_entries_before_inception_are_skipped():
    store = seed_session(FakeSupabase(), session="2026-11-18")
    _, getter = portfolio_getter()

    result = await execute_picks_entries(
        "2026-11-18",
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "skipped"
    assert store.count("trades") == 0


@pytest.mark.asyncio
async def test_picks_entry_skips_leg_without_price():
    store = seed_session(FakeSupabase())
    _, getter = portfolio_getter()
    price_map = open_price_map()
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
    store = seed_session(FakeSupabase())
    portfolios, getter = stored_portfolio_getter(store)
    await execute_picks_entries(
        SESSION,
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    result = await execute_picks_exits(
        SESSION,
        price_map=open_price_map(price=101.0),
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
        row = next(r for r in store.rows["portfolios"] if r["id"] == portfolio.id)
        assert row["cash_balance"] == pytest.approx(expected_cash)
        assert row["total_equity"] == pytest.approx(expected_cash)
        assert row["realized"] == pytest.approx(expected_cash)
        assert row["buying_power"] == pytest.approx(expected_cash)

    perf = store.rows["portfolio_performance"]
    assert len(perf) == 4
    assert all(p["date"] == SESSION for p in perf)
    assert all(p["total_equity"] == pytest.approx(expected_cash) for p in perf)
    assert long_pnl > 0 > short_pnl


@pytest.mark.asyncio
async def test_picks_exit_with_a_missing_close_price_writes_nothing():
    store = seed_session(FakeSupabase())
    portfolios, getter = stored_portfolio_getter(store)
    await execute_picks_entries(
        SESSION,
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )
    cash_after_entry = {portfolio.id: portfolio.cash_balance for portfolio in portfolios.values()}

    price_map = open_price_map(price=101.0)
    price_map.pop("CCC")
    result = await execute_picks_exits(
        SESSION,
        price_map=price_map,
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    # Fail closed: no partial session, no wrong equity snapshot.
    assert result["status"] == "skipped"
    assert set(result["skipped"]) == set(portfolios)
    assert all("CCC" in reason for reason in result["skipped"].values())
    assert store.count("trades") == 24  # entries only, no exits
    assert all(t.get("realized_pnl") is None for t in store.rows["trades"])
    assert store.count("portfolio_positions") == 12
    assert not store.rows.get("portfolio_performance")
    for portfolio in portfolios.values():
        row = next(r for r in store.rows["portfolios"] if r["id"] == portfolio.id)
        assert row["cash_balance"] == pytest.approx(cash_after_entry[portfolio.id])


@pytest.mark.asyncio
async def test_picks_exit_resumes_a_partially_written_session():
    store = seed_session(FakeSupabase())
    portfolios, getter = stored_portfolio_getter(store)
    await execute_picks_entries(
        SESSION,
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    # Simulate a crash after the first leg of the first portfolio was committed.
    victim = portfolios[picks_owner_id(PICKS_MODEL_TRACKS[0])]
    entry = next(t for t in store.rows["trades"] if t["portfolio_id"] == victim.id and t["signal"] == "BUY")
    store.rows["trades"].append(
        {
            "id": "exit-already-written",
            "portfolio_id": victim.id,
            "ticker": entry["ticker"],
            "signal": "SELL",
            "quantity": entry["quantity"],
            "price": 101.0,
            "realized_pnl": 1.0,
            "executed_at": "2026-11-19T21:00:00Z",
        }
    )

    result = await execute_picks_exits(
        SESSION,
        price_map=open_price_map(price=101.0),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "success"
    victim_exits = [
        t for t in store.rows["trades"] if t["portfolio_id"] == victim.id and t["signal"] in ("SELL", "COVER")
    ]
    assert len(victim_exits) == 6  # the pre-existing row plus the five it still owed
    assert len([t for t in victim_exits if t["ticker"] == entry["ticker"]]) == 1
    for owner, portfolio in portfolios.items():
        exits = [
            t for t in store.rows["trades"] if t["portfolio_id"] == portfolio.id and t["signal"] in ("SELL", "COVER")
        ]
        assert len(exits) == 6, owner


@pytest.mark.asyncio
async def test_picks_exit_without_open_legs_is_skipped():
    store = seed_session(FakeSupabase())
    _, getter = portfolio_getter()

    result = await execute_picks_exits(
        SESSION,
        price_map=open_price_map(price=101.0),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )

    assert result["status"] == "skipped"
    assert store.count("trades") == 0


@pytest.mark.asyncio
async def test_picks_entries_skip_when_prior_session_has_unclosed_legs():
    store = seed_session(FakeSupabase(), session="2026-11-19")
    portfolios, getter = stored_portfolio_getter(store)

    first = await execute_picks_entries(
        "2026-11-19",
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )
    assert first["status"] == "success"
    cash_after_first = {pid: p.cash_balance for pid, p in portfolios.items()}

    # Seed 2026-11-20 with distinct basket IDs so picks_by_basket stays isolated from 2026-11-19.
    for index, model in enumerate(PICKS_MODEL_TRACKS):
        bid = f"basket-next-{index}"
        store.rows["daily_stock_baskets"].append(
            {"id": bid, "target_date": "2026-11-20", "model_name": model, "status": "pending"}
        )
        store.rows["daily_stock_picks"].append(
            {
                "id": f"pick-next-{index}",
                "basket_id": bid,
                "target_date": "2026-11-20",
                "model_name": model,
                "ticker": "AAA",
                "direction": "UP",
                "rank": 1,
                "confidence": 70.0,
                "status": "pending",
            }
        )

    second = await execute_picks_entries(
        "2026-11-20",
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )
    assert second["status"] == "skipped"
    assert all("unclosed prior legs (2026-11-19)" in reason for reason in second["skipped"].values())
    assert store.count("trades") == 24
    for pid, p in portfolios.items():
        assert p.cash_balance == pytest.approx(cash_after_first[pid])


@pytest.mark.asyncio
async def test_picks_exit_with_later_open_session_snapshots_true_historical_equity():
    store = seed_session(FakeSupabase(), session="2026-11-19")
    portfolios, getter = stored_portfolio_getter(store)
    await execute_picks_entries(
        "2026-11-19",
        price_map=open_price_map(),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )
    # Simulate a later session's open BUY leg already deducting cash before 2026-11-19 was closed.
    consensus_pf = portfolios[picks_owner_id("consensus")]
    later_long_cost = 2000.0
    consensus_pf.cash_balance -= later_long_cost
    store.rows["trades"].append(
        {
            "id": "later-buy",
            "portfolio_id": consensus_pf.id,
            "ticker": "ZZZ",
            "signal": "BUY",
            "quantity": 20,
            "price": 100.0,
            "total_cost": later_long_cost,
            "realized_pnl": None,
            "executed_at": "2026-11-20T14:30:00Z",
        }
    )

    result = await execute_picks_exits(
        "2026-11-19",
        price_map=open_price_map(price=101.0),
        get_supabase_client_fn=lambda: store,
        get_or_create_system_portfolio_fn=getter,
    )
    assert result["status"] == "success"

    entry_long = 100.0 * 1.0005
    exit_long = 101.0 * (1 - 0.0005)
    entry_short = 100.0 * (1 - 0.0005)
    exit_short = 101.0 * (1 + 0.0005)
    pnl_1119 = 3 * 16 * (exit_long - entry_long) + 3 * 16 * (entry_short - exit_short)
    expected_1119_eq = 10000.0 + pnl_1119

    perf = next(
        r
        for r in store.rows["portfolio_performance"]
        if r["portfolio_id"] == consensus_pf.id and r["date"] == "2026-11-19"
    )
    assert perf["total_equity"] == pytest.approx(expected_1119_eq)
    pf_row = next(r for r in store.rows["portfolios"] if r["id"] == consensus_pf.id)
    assert pf_row["cash_balance"] == pytest.approx(expected_1119_eq - later_long_cost)
    assert pf_row["total_equity"] == pytest.approx(expected_1119_eq)
