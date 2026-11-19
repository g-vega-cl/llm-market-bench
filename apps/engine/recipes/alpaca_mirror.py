"""Fire-and-forget Alpaca paper mirror for live strategy-recipe fills.

`public.strategy_recipes` (paper_cash / paper_positions / paper_trades) stays the
source of truth; the Alpaca paper account is an external audit trail. Every broker
call is guarded so a failure logs and returns instead of blocking the ledger write.

One paper account is shared with the `sys-*` portfolios and the live SPY trader, so
an Alpaca position for a ticker is the aggregate of every strategy: closes are capped
to the shares the broker actually holds and never open an unintended short.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.config import (
    ALPACA_API_KEY,
    ALPACA_ENABLED,
    ALPACA_PAPER_ENDPOINT,
    ALPACA_SECRET_KEY,
    logger,
)


def _build_client() -> Any | None:
    """Return a paper TradingClient, or None when mirroring is not configured."""
    if not ALPACA_ENABLED or not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        return None
    from alpaca.trading.client import TradingClient

    return TradingClient(
        ALPACA_API_KEY,
        ALPACA_SECRET_KEY,
        paper=True,
        url_override=ALPACA_PAPER_ENDPOINT,
    )


def _ticker_of(position: dict[str, Any]) -> str:
    return str(position.get("ticker", "")).upper().strip()


def _whole_shares(position: dict[str, Any]) -> int:
    try:
        return int(float(position.get("shares") or 0))
    except (TypeError, ValueError):
        return 0


def position_snapshot(state: Any) -> dict[str, int]:
    """Snapshot ticker -> whole share count before a portfolio step."""
    return {_ticker_of(p): _whole_shares(p) for p in state.positions if _ticker_of(p)}


def compute_fills(before: dict[str, int], state: Any) -> list[dict[str, Any]]:
    """Derive broker fills from a position snapshot diff (entries and full exits)."""
    after = position_snapshot(state)
    fills: list[dict[str, Any]] = []
    for ticker, shares in before.items():
        if ticker not in after and shares > 0:
            fills.append({"action": "SELL", "ticker": ticker, "shares": int(shares)})
    for ticker, shares in after.items():
        delta = shares - int(before.get(ticker, 0))
        if delta > 0:
            fills.append({"action": "BUY", "ticker": ticker, "shares": delta})
    return sorted(fills, key=lambda f: (f["action"] != "SELL", f["ticker"]))


def _client_order_id(recipe_id: str, ticker: str, action: str, slot_key: str) -> str:
    return f"recipe-{recipe_id[:8]}__{ticker}__{action}__{slot_key}"


def _alpaca_held(client: Any, ticker: str) -> int:
    """Whole shares currently held on Alpaca for ticker (0 when flat or on error)."""
    try:
        position = client.get_open_position(ticker)
        return int(float(position.qty or 0))
    except Exception:
        logger.debug("[Alpaca] No broker position for %s", ticker, exc_info=True)
        return 0


def _submit(client: Any, ticker: str, shares: int, action: str, client_order_id: str) -> str | None:
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    request = MarketOrderRequest(
        symbol=ticker,
        qty=int(shares),
        side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        client_order_id=client_order_id,
    )
    order = client.submit_order(request)
    return str(getattr(order, "id", "") or "") or None


async def mirror_recipe_fills(
    *,
    recipe_id: str,
    slot_label: str,
    slot_key: str,
    before: dict[str, int],
    state: Any,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Mirror this turn's recipe fills to the Alpaca paper account.

    Returns one result dict per fill: {action, ticker, shares, status, order_id}.
    Never raises: broker errors are logged and reported as status="ERROR".
    """
    fills = compute_fills(before, state)
    if not fills:
        return []

    broker = client if client is not None else _build_client()
    if broker is None:
        logger.debug("[Alpaca] Recipe mirror disabled; skipping %d fill(s)", len(fills))
        return []

    results: list[dict[str, Any]] = []
    for fill in fills:
        ticker = fill["ticker"]
        action = fill["action"]
        shares = int(fill["shares"])
        if action == "SELL":
            shares = min(shares, _alpaca_held(broker, ticker))
            if shares <= 0:
                logger.warning(
                    "[Alpaca] SKIPPED SELL %s: broker holds no shares (slot %s)", ticker, slot_label
                )
                results.append({**fill, "status": "SKIPPED_NO_POSITION", "order_id": None})
                continue
        try:
            order_id = _submit(
                broker, ticker, shares, action, _client_order_id(recipe_id, ticker, action, slot_key)
            )
            logger.info("[Alpaca] Recipe %s mirrored %s %s x%d (order %s)", recipe_id, action, ticker, shares, order_id)
            results.append({**fill, "shares": shares, "status": "SUBMITTED", "order_id": order_id})
        except Exception:
            logger.exception("[Alpaca] Recipe %s failed to mirror %s %s x%d", recipe_id, action, ticker, shares)
            results.append({**fill, "shares": shares, "status": "ERROR", "order_id": None})
    return results


def record_mirror_status(state: Any, results: list[dict[str, Any]], *, slot_label: str) -> None:
    """Stamp broker metadata onto the open position (BUY) or closed trade (SELL)."""
    if not results:
        return
    stamp = datetime.now(UTC).isoformat()
    buys = {r["ticker"]: r for r in results if r["action"] == "BUY"}
    sells = {r["ticker"]: r for r in results if r["action"] == "SELL"}
    for position in state.positions:
        result = buys.get(_ticker_of(position))
        if result:
            position["alpaca_status"] = result["status"]
            position["alpaca_order_id"] = result["order_id"]
            position["alpaca_submitted_at"] = stamp
    for trade in reversed(state.trades):
        if trade.get("exit_time") != slot_label:
            continue
        result = sells.get(str(trade.get("ticker", "")).upper().strip())
        if result:
            trade["alpaca_status"] = result["status"]
            trade["alpaca_order_id"] = result["order_id"]
            trade["alpaca_submitted_at"] = stamp
