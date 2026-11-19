"""Hermetic tests for the fire-and-forget Alpaca mirror on live recipe fills."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from recipes.alpaca_mirror import compute_fills, mirror_recipe_fills, record_mirror_status
from recipes.portfolio_engine import PortfolioState, apply_portfolio_step


class FakeTradingClient:
    """Records submitted orders; raises for symbols flagged as broker failures."""

    def __init__(self, positions: dict[str, float] | None = None, fail_symbols: tuple[str, ...] = ()) -> None:
        self.positions = dict(positions or {})
        self.fail_symbols = set(fail_symbols)
        self.orders: list[SimpleNamespace] = []

    def get_open_position(self, ticker: str) -> SimpleNamespace:
        if ticker in self.positions:
            return SimpleNamespace(qty=str(self.positions[ticker]))
        raise RuntimeError(f"position does not exist: {ticker}")

    def submit_order(self, request):  # noqa: ANN001 - duck-typed SDK request
        if request.symbol in self.fail_symbols:
            raise RuntimeError("broker exploded")
        self.orders.append(request)
        return SimpleNamespace(id=f"order-{len(self.orders)}")


def _strategy_state() -> PortfolioState:
    state = PortfolioState(cash=10000.0)
    apply_portfolio_step(
        state,
        slot_label="2026-11-19 09:30 ET",
        signals=[
            {"action": "BUY", "ticker": "DIS"},
            {"action": "BUY", "ticker": "NVDA"},
        ],
        prices={"DIS": 122.04, "NVDA": 100.0},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    return state


def test_compute_fills_derives_buys_and_sells_from_position_diff():
    state = _strategy_state()
    before = {"NVDA": 10, "TSLA": 7}

    fills = compute_fills(before, state)
    by_key = {(f["action"], f["ticker"]): f["shares"] for f in fills}

    # New leg and an increased existing leg are BUYs; a vanished ticker is a full SELL
    assert by_key[("BUY", "DIS")] == 20
    assert by_key[("BUY", "NVDA")] == 14  # 10 -> 24
    assert by_key[("SELL", "TSLA")] == 7


@pytest.mark.asyncio
async def test_mirror_submits_whole_share_day_market_buy_with_recipe_client_order_id():
    state = PortfolioState(cash=10000.0)
    apply_portfolio_step(
        state,
        slot_label="2026-11-19 09:30 ET",
        signals=[{"action": "BUY", "ticker": "DIS"}],
        prices={"DIS": 122.04},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    client = FakeTradingClient()

    results = await mirror_recipe_fills(
        recipe_id="0773afba-948e-4b11-a445-1d39934839ad",
        slot_label="2026-11-19 09:30 ET",
        slot_key="20261119T143000Z",
        before={},
        state=state,
        client=client,
    )

    assert len(client.orders) == 1
    order = client.orders[0]
    assert order.symbol == "DIS"
    assert order.qty == 20
    assert "BUY" in str(order.side)
    assert order.client_order_id == "recipe-0773afba__DIS__BUY__20261119T143000Z"
    assert results[0]["status"] == "SUBMITTED"
    assert results[0]["order_id"] == "order-1"


@pytest.mark.asyncio
async def test_mirror_caps_sell_to_alpaca_position_and_skips_when_flat():
    state = PortfolioState(cash=10000.0)
    apply_portfolio_step(
        state,
        slot_label="2026-11-19 09:30 ET",
        signals=[{"action": "BUY", "ticker": "DIS"}, {"action": "BUY", "ticker": "NVDA"}],
        prices={"DIS": 122.04, "NVDA": 100.0},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    before = {"DIS": 20, "NVDA": 25}
    apply_portfolio_step(
        state,
        slot_label="2026-11-19 12:30 ET",
        signals=[{"action": "EXIT", "ticker": "DIS"}, {"action": "EXIT", "ticker": "NVDA"}],
        prices={"DIS": 124.0, "NVDA": 101.0},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )

    capped_client = FakeTradingClient(positions={"DIS": 7})
    capped = await mirror_recipe_fills(
        recipe_id="rec-1",
        slot_label="2026-11-19 12:30 ET",
        slot_key="20261119T173000Z",
        before=before,
        state=state,
        client=capped_client,
    )
    by_ticker = {r["ticker"]: r for r in capped}
    assert by_ticker["DIS"]["status"] == "SUBMITTED"
    assert capped_client.orders[0].qty == 7
    assert by_ticker["NVDA"]["status"] == "SKIPPED_NO_POSITION"
    assert len(capped_client.orders) == 1


@pytest.mark.asyncio
async def test_mirror_failure_never_raises_and_marks_error():
    state = PortfolioState(cash=10000.0)
    apply_portfolio_step(
        state,
        slot_label="2026-11-19 09:30 ET",
        signals=[{"action": "BUY", "ticker": "DIS"}],
        prices={"DIS": 122.04},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    client = FakeTradingClient(fail_symbols=("DIS",))

    results = await mirror_recipe_fills(
        recipe_id="rec-1",
        slot_label="2026-11-19 09:30 ET",
        slot_key="20261119T143000Z",
        before={},
        state=state,
        client=client,
    )

    assert results[0]["status"] == "ERROR"
    assert results[0]["order_id"] is None


@pytest.mark.asyncio
async def test_mirror_is_inert_without_a_client(monkeypatch):
    from recipes import alpaca_mirror

    monkeypatch.setattr(alpaca_mirror, "_build_client", lambda: None)
    state = _strategy_state()

    results = await mirror_recipe_fills(
        recipe_id="rec-1",
        slot_label="2026-11-19 09:30 ET",
        slot_key="20261119T143000Z",
        before={},
        state=state,
    )

    assert results == []
    assert all("alpaca_status" not in pos for pos in state.positions)


def test_record_mirror_status_stamps_positions_and_closed_trades():
    state = PortfolioState(cash=10000.0)
    apply_portfolio_step(
        state,
        slot_label="2026-11-19 09:30 ET",
        signals=[{"action": "BUY", "ticker": "DIS"}],
        prices={"DIS": 122.04},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    buys = [{"action": "BUY", "ticker": "DIS", "shares": 20, "status": "SUBMITTED", "order_id": "order-9"}]
    record_mirror_status(state, buys, slot_label="2026-11-19 09:30 ET")
    assert state.positions[0]["alpaca_status"] == "SUBMITTED"
    assert state.positions[0]["alpaca_order_id"] == "order-9"

    apply_portfolio_step(
        state,
        slot_label="2026-11-19 12:30 ET",
        signals=[{"action": "EXIT", "ticker": "DIS"}],
        prices={"DIS": 124.0},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    sells = [{"action": "SELL", "ticker": "DIS", "shares": 20, "status": "SUBMITTED", "order_id": "order-10"}]
    record_mirror_status(state, sells, slot_label="2026-11-19 12:30 ET")
    assert state.trades[-1]["alpaca_status"] == "SUBMITTED"
    assert state.trades[-1]["alpaca_order_id"] == "order-10"
