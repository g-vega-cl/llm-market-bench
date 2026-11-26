"""Alpaca paper trading broker integration for third-party audit.

Supabase remains the source of truth. Alpaca is fire-and-forget.
Every executed trade is mirrored as a DAY limit order, tagged with agent metadata.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

from core.config import ALPACA_API_KEY, ALPACA_ENABLED, ALPACA_PAPER_ENDPOINT, ALPACA_SECRET_KEY
from core.db import get_supabase_client

logger = logging.getLogger("engine")

_MAX_NOTE_LEN = 240


def _resolve_order_side(signal: str) -> OrderSide:
    """Map an engine signal string onto an Alpaca OrderSide."""
    sig = signal.upper()
    if sig in ("BUY", "LONG", "COVER"):
        return OrderSide.BUY
    if sig in ("SELL", "SHORT"):
        return OrderSide.SELL
    return OrderSide.BUY if "BUY" in sig else OrderSide.SELL


def _is_terminal_rejection(exc: APIError) -> bool:
    """Return True when Alpaca rejected the request before creating an order."""
    status_code = getattr(exc, "status_code", None)
    if not (isinstance(status_code, int) and 400 <= status_code < 500):
        return False
    if status_code in (408, 429):
        return False
    return not (status_code == 422 and "client_order_id" in str(exc).lower())


def _format_alpaca_error(exc: Exception) -> str:
    """Format a concise single-line reason for trades.alpaca_note."""
    status_code = getattr(exc, "status_code", None)
    msg = " ".join(str(exc).split())
    prefix = f"HTTP {status_code}: " if status_code is not None else f"{type(exc).__name__}: "
    detail = f"{prefix}{msg}" if msg else prefix.rstrip(": ")
    return detail[:_MAX_NOTE_LEN]


class AlpacaBroker:
    """Thin wrapper around Alpaca Trading API for limit order submission."""

    def __init__(self, client: TradingClient | None = None, sb_client: Any = None):
        self._client: TradingClient | None = None
        self._sb = sb_client

        # The kill switch governs every path, including an injected client: a caller that
        # builds its own TradingClient must not be able to mirror while ALPACA_ENABLED is off.
        if not ALPACA_ENABLED:
            logger.info("[Alpaca] Disabled via ALPACA_ENABLED constant.")
            return

        if client is not None:
            self._client = client
            return

        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            logger.warning("[Alpaca] API keys missing. Alpaca mirroring disabled.")
            return

        try:
            self._client = TradingClient(
                ALPACA_API_KEY,
                ALPACA_SECRET_KEY,
                paper=True,
                url_override=ALPACA_PAPER_ENDPOINT,
            )
        except Exception:
            # Construction failure must degrade to "no mirror", never abort the caller's
            # startup: ten trading lanes share this path and the ledger does not need it.
            logger.exception("[Alpaca] Trading client construction failed. Alpaca mirroring disabled.")
            self._client = None
            return
        logger.info("[Alpaca] Broker initialized (paper endpoint).")

    @property
    def client(self) -> TradingClient | None:
        """The underlying paper TradingClient (None when disabled or keys missing)."""
        return self._client

    def try_get_alpaca_position(self, ticker: str) -> float | None:
        """Position quantity, or None when the broker cannot answer.

        `get_alpaca_position` collapses every failure to 0.0, which is correct for
        the SELL guard but indistinguishable from a genuinely flat book. Callers
        that record *evidence* (e.g. BROKER_POSITION_MISMATCH) must use this.
        """
        if not self._client:
            return None

        try:
            position = self._client.get_open_position(ticker)
        except APIError as exc:
            if getattr(exc, "status_code", None) == 404:
                return 0.0
            logger.warning(f"[Alpaca] API error reading position for {ticker}: {exc}")
            return None
        except Exception as exc:
            logger.warning(f"[Alpaca] Unexpected error reading position for {ticker}: {exc}")
            return None

        try:
            return float(position.qty) if position.qty else 0.0
        except (TypeError, ValueError):
            return None

    def get_alpaca_position(self, ticker: str) -> float:
        """Query Alpaca for the current quantity held for a ticker (0.0 on flat or error)."""
        qty = self.try_get_alpaca_position(ticker)
        return qty if qty is not None else 0.0

    async def _apply_position_guardrail(
        self,
        trade_id: UUID | str,
        ticker: str,
        quantity: int,
        sig: str,
    ) -> int | None:
        """Prevent unintended shorts on SELL/COVER; returns adjusted qty or None if skipped."""
        alpaca_qty = await asyncio.to_thread(self.get_alpaca_position, ticker)
        if sig == "SELL":
            available = int(alpaca_qty) if alpaca_qty > 0 else 0
        else:
            available = int(abs(alpaca_qty)) if alpaca_qty < 0 else 0

        if available <= 0:
            logger.warning(
                f"[Alpaca] SKIPPED {sig} {quantity} {ticker}: "
                f"Alpaca holds {alpaca_qty} shares ({available} whole shares)."
            )
            await self._update_trade(trade_id, None, "SKIPPED_NO_POSITION")
            return None

        if quantity > available:
            logger.warning(
                f"[Alpaca] CAPPING {sig} for {ticker}: "
                f"requested {quantity}, Alpaca holds {available}. "
                f"Submitting {available} instead."
            )
            return available

        return quantity

    async def _submit_order(
        self,
        *,
        trade_id: UUID | str,
        ticker: str,
        quantity: int,
        signal: str,
        agent_id: str,
        guard_sells: bool,
        build_request: Any,
        log_description: str,
    ) -> dict[str, Any]:
        """Shared submission path for market and limit orders."""
        if not self._client:
            if trade_id:
                await self._update_trade(trade_id, None, "DISABLED")
            return {"status": "DISABLED", "order_id": None}

        sig = signal.upper()
        side = _resolve_order_side(signal)
        client_order_id = f"{agent_id}__{ticker}__{signal}__{str(trade_id)}"

        if guard_sells and sig in ("SELL", "COVER"):
            adjusted_qty = await self._apply_position_guardrail(trade_id, ticker, quantity, sig)
            if adjusted_qty is None:
                return {"status": "SKIPPED_NO_POSITION", "order_id": None}
            quantity = adjusted_qty

        order_request = build_request(quantity, side, client_order_id)

        try:
            order = await asyncio.to_thread(self._client.submit_order, order_request)
            order_id_str = str(order.id) if order.id else None
            persisted = bool(await self._update_trade(trade_id, order_id_str, "SUBMITTED"))
            logger.info(
                f"[Alpaca] Submitted {log_description} {signal} {quantity} {ticker} "
                f"(OrderID: {order_id_str}, ClientOrderID: {client_order_id})"
            )
            return {"status": "SUBMITTED", "order_id": order_id_str, "persisted": persisted}
        except APIError as exc:
            target_status = "REJECTED" if _is_terminal_rejection(exc) else "ERROR"
            reason = _format_alpaca_error(exc)
            logger.warning(f"[Alpaca] {log_description} order {target_status} for {ticker}: {reason}")
            persisted = bool(await self._update_trade(trade_id, None, target_status, note=reason))
            return {"status": target_status, "order_id": None, "persisted": persisted}
        except Exception as exc:
            reason = _format_alpaca_error(exc)
            logger.exception(f"[Alpaca] Failed to submit {log_description} order for {ticker}")
            persisted = bool(await self._update_trade(trade_id, None, "ERROR", note=reason))
            return {"status": "ERROR", "order_id": None, "persisted": persisted}

    async def submit_limit_order(
        self,
        trade_id: UUID | str,
        ticker: str,
        quantity: int,
        signal: str,
        limit_price: float,
        agent_id: str,
        guard_sells: bool = True,
    ) -> dict[str, Any]:
        """Fire-and-forget DAY limit order submission to Alpaca.

        Tags the order with agent metadata (client_order_id) for audit filtering.
        Updates the trades row asynchronously after submission attempt.

        SELL orders are guarded against shorting: if Alpaca does not hold the
        requested shares, the order is skipped or quantity-capped to the actual
        Alpaca position size. Pass ``guard_sells=False`` to mirror the ledger
        attempt verbatim instead (the rejection then becomes the audit record).
        """
        rounded_price = round(limit_price, 2)
        return await self._submit_order(
            trade_id=trade_id,
            ticker=ticker,
            quantity=quantity,
            signal=signal,
            agent_id=agent_id,
            guard_sells=guard_sells,
            build_request=lambda qty, side, cid: LimitOrderRequest(
                symbol=ticker,
                qty=qty,
                side=side,
                limit_price=rounded_price,
                time_in_force=TimeInForce.DAY,
                client_order_id=cid,
            ),
            log_description=f"limit @ ${rounded_price:.2f}",
        )

    async def _update_trade(
        self,
        trade_id: UUID | str,
        order_id: str | None,
        status: str,
        note: str | None = None,
    ) -> bool:
        """Update the trades row with Alpaca metadata. Returns True when persisted."""
        try:
            supabase = self._sb or get_supabase_client()
            payload: dict = {"alpaca_status": status}
            if status != "DISABLED":
                payload["alpaca_submitted_at"] = datetime.now(UTC).isoformat()
            if order_id:
                payload["alpaca_order_id"] = str(order_id)
            if note:
                payload["alpaca_note"] = note

            await asyncio.to_thread(lambda: supabase.table("trades").update(payload).eq("id", str(trade_id)).execute())
            return True
        except Exception as exc:
            logger.error(f"[Alpaca] Failed to update trade {trade_id} status: {exc}")
            return False

    async def submit_market_order(
        self,
        trade_id: UUID | str,
        ticker: str,
        quantity: int,
        signal: str,
        agent_id: str,
        time_in_force: TimeInForce = TimeInForce.DAY,
        guard_sells: bool = True,
    ) -> dict[str, Any]:
        """Fire-and-forget market order submission to Alpaca (supports DAY and OPG).

        Returns the outcome so the caller can record it against the ledger trade:
        ``{"status": SUBMITTED|REJECTED|ERROR|SKIPPED_NO_POSITION|DISABLED, "order_id": str|None}``.
        """
        return await self._submit_order(
            trade_id=trade_id,
            ticker=ticker,
            quantity=quantity,
            signal=signal,
            agent_id=agent_id,
            guard_sells=guard_sells,
            build_request=lambda qty, side, cid: MarketOrderRequest(
                symbol=ticker,
                qty=qty,
                side=side,
                time_in_force=time_in_force,
                client_order_id=cid,
            ),
            log_description=f"market ({time_in_force.value})",
        )

    async def cancel_open_orders_for_agent(self, agent_id: str, ticker: str | None = None) -> int:
        """Cancel open Alpaca orders belonging to a specific agent."""
        if not self._client:
            return 0

        try:
            from alpaca.trading.enums import QueryOrderStatus
            from alpaca.trading.requests import GetOrdersRequest

            req = GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[ticker] if ticker else None)
            open_orders = await asyncio.to_thread(self._client.get_orders, filter=req)
            cancelled_count = 0
            prefix = f"{agent_id}__"
            for order in open_orders:
                client_id = getattr(order, "client_order_id", "") or ""
                if client_id.startswith(prefix):
                    await asyncio.to_thread(self._client.cancel_order_by_id, order.id)
                    cancelled_count += 1
                    logger.info(f"[Alpaca] Cancelled open order {order.id} for agent {agent_id} ({client_id})")
            return cancelled_count
        except Exception:
            logger.exception(f"[Alpaca] Failed to cancel open orders for agent {agent_id}")
            return 0

    def _get_supabase_position(self, ticker: str, agent_id: str) -> int:
        """Check Supabase portfolio_positions for a ticker held by an agent.

        Used as a fallback source of truth when Alpaca shows 0 shares for a SELL.
        Matches the agent_id to a portfolio via the portfolios table, then looks up
        the position quantity for the given ticker.
        """
        try:
            supabase = get_supabase_client()
            portfolio_res = supabase.table("portfolios").select("id").eq("owner_id", agent_id).execute()
            if not portfolio_res.data:
                logger.debug(f"[Alpaca] No portfolio found for agent '{agent_id}'")
                return 0
            portfolio_id = portfolio_res.data[0]["id"]
            pos_res = (
                supabase.table("portfolio_positions")
                .select("quantity")
                .eq("portfolio_id", portfolio_id)
                .eq("ticker", ticker)
                .execute()
            )
            if pos_res.data:
                qty = int(pos_res.data[0]["quantity"])
                logger.debug(f"[Alpaca] Supabase position for {ticker} (agent {agent_id}): {qty}")
                return qty
            return 0
        except Exception as exc:
            logger.warning(f"[Alpaca] Failed to query Supabase position for {ticker}: {exc}")
            return 0
