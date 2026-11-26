"""Alpaca paper trading broker integration for third-party audit.

Supabase remains the source of truth. Alpaca is fire-and-forget.
Every executed trade is mirrored as a DAY limit order, tagged with agent metadata.
"""

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


class AlpacaBroker:
    """Thin wrapper around Alpaca Trading API for limit order submission."""

    def __init__(self, client: TradingClient | None = None, sb_client: Any = None):
        self._client: TradingClient | None = None
        self._sb = sb_client

        if client is not None:
            self._client = client
            return

        if not ALPACA_ENABLED:
            logger.info("[Alpaca] Disabled via ALPACA_ENABLED constant.")
            return

        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            logger.warning("[Alpaca] API keys missing. Alpaca mirroring disabled.")
            return

        self._client = TradingClient(
            ALPACA_API_KEY,
            ALPACA_SECRET_KEY,
            paper=True,
            url_override=ALPACA_PAPER_ENDPOINT,
        )
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
        """Query Alpaca for the current quantity held for a ticker.

        Returns the quantity as a float (Alpaca may return fractional shares
        for some account types). Returns 0.0 if no position exists or if the
        client is not initialized.
        """
        if not self._client:
            return 0.0

        try:
            position = self._client.get_open_position(ticker)
            qty = float(position.qty) if position.qty else 0.0
            logger.debug(f"[Alpaca] Position for {ticker}: {qty} shares")
            return qty
        except APIError as exc:
            # Alpaca returns 404 when a position does not exist
            if hasattr(exc, "status_code") and exc.status_code == 404:
                logger.debug(f"[Alpaca] No position found for {ticker}")
                return 0.0
            logger.warning(f"[Alpaca] API error checking position for {ticker}: {exc}")
            return 0.0
        except Exception as exc:
            logger.warning(f"[Alpaca] Unexpected error checking position for {ticker}: {exc}")
            return 0.0

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
        if not self._client:
            return {"status": "DISABLED", "order_id": None}

        sig = signal.upper()
        if sig in ("BUY", "LONG", "COVER"):
            side = OrderSide.BUY
        elif sig in ("SELL", "SHORT"):
            side = OrderSide.SELL
        else:
            side = OrderSide.BUY if "BUY" in sig else OrderSide.SELL

        client_order_id = f"{agent_id}__{ticker}__{signal}__{str(trade_id)}"

        # Guardrails:
        # 1. SELL (closing long): only sell shares Alpaca physically holds.
        #    Never sell shares not held on Alpaca to prevent accidental short positions.
        if guard_sells and sig == "SELL":
            alpaca_qty = self.get_alpaca_position(ticker)
            if alpaca_qty <= 0:
                logger.warning(
                    f"[Alpaca] SKIPPED SELL {quantity} {ticker}: "
                    f"Alpaca holds {alpaca_qty} shares. Cannot close position not held."
                )
                await self._update_trade(trade_id, None, "SKIPPED_NO_POSITION")
                return {"status": "SKIPPED_NO_POSITION", "order_id": None}
            elif quantity > alpaca_qty:
                logger.warning(
                    f"[Alpaca] CAPPING SELL for {ticker}: "
                    f"requested {quantity}, Alpaca holds {alpaca_qty}. "
                    f"Submitting {alpaca_qty} instead."
                )
                quantity = int(alpaca_qty)

        # 2. COVER (closing short): only cover shares Alpaca is physically short.
        elif guard_sells and sig == "COVER":
            alpaca_qty = self.get_alpaca_position(ticker)
            if alpaca_qty >= 0:
                logger.warning(
                    f"[Alpaca] SKIPPED COVER {quantity} {ticker}: "
                    f"Alpaca holds {alpaca_qty} shares. Cannot cover without short position."
                )
                await self._update_trade(trade_id, None, "SKIPPED_NO_POSITION")
                return {"status": "SKIPPED_NO_POSITION", "order_id": None}
            short_shares = int(abs(alpaca_qty))
            if quantity > short_shares:
                logger.warning(
                    f"[Alpaca] CAPPING COVER for {ticker}: "
                    f"requested {quantity}, Alpaca is short {short_shares}. "
                    f"Submitting {short_shares} instead."
                )
                quantity = short_shares

        order_request = LimitOrderRequest(
            symbol=ticker,
            qty=quantity,
            side=side,
            limit_price=round(limit_price, 2),
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id,
        )

        try:
            order = self._client.submit_order(order_request)
            order_id_str = str(order.id) if order.id else None
            persisted = bool(await self._update_trade(trade_id, order_id_str, "SUBMITTED"))
            logger.info(
                f"[Alpaca] Submitted {signal} {quantity} {ticker} @ ${limit_price:.2f} "
                f"(OrderID: {order_id_str}, ClientOrderID: {client_order_id})"
            )
            return {"status": "SUBMITTED", "order_id": order_id_str, "persisted": persisted}
        except Exception:
            logger.exception(f"[Alpaca] Failed to submit order for {ticker}")
            persisted = bool(await self._update_trade(trade_id, None, "ERROR"))
            return {"status": "ERROR", "order_id": None, "persisted": persisted}

    async def _update_trade(self, trade_id: UUID | str, order_id: str | None, status: str) -> bool:
        """Update the trades row with Alpaca metadata. Returns True when persisted."""
        try:
            supabase = self._sb or get_supabase_client()
            payload: dict = {
                "alpaca_status": status,
                "alpaca_submitted_at": datetime.now(UTC).isoformat(),
            }
            if order_id:
                payload["alpaca_order_id"] = str(order_id)

            supabase.table("trades").update(payload).eq("id", str(trade_id)).execute()
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
        ``{"status": SUBMITTED|ERROR|SKIPPED_NO_POSITION|DISABLED, "order_id": str|None}``.
        """
        if not self._client:
            return {"status": "DISABLED", "order_id": None}

        sig = signal.upper()
        if sig in ("BUY", "LONG", "COVER"):
            side = OrderSide.BUY
        elif sig in ("SELL", "SHORT"):
            side = OrderSide.SELL
        else:
            side = OrderSide.BUY if "BUY" in sig else OrderSide.SELL

        client_order_id = f"{agent_id}__{ticker}__{signal}__{str(trade_id)}"

        if guard_sells and sig == "SELL":
            alpaca_qty = self.get_alpaca_position(ticker)
            if alpaca_qty <= 0:
                logger.warning(
                    f"[Alpaca] SKIPPED SELL {quantity} {ticker}: "
                    f"Alpaca holds {alpaca_qty} shares. Cannot close position not held."
                )
                await self._update_trade(trade_id, None, "SKIPPED_NO_POSITION")
                return {"status": "SKIPPED_NO_POSITION", "order_id": None}
            elif quantity > alpaca_qty:
                logger.warning(
                    f"[Alpaca] CAPPING SELL for {ticker}: "
                    f"requested {quantity}, Alpaca holds {alpaca_qty}. "
                    f"Submitting {alpaca_qty} instead."
                )
                quantity = int(alpaca_qty)
        elif guard_sells and sig == "COVER":
            alpaca_qty = self.get_alpaca_position(ticker)
            if alpaca_qty >= 0:
                logger.warning(
                    f"[Alpaca] SKIPPED COVER {quantity} {ticker}: "
                    f"Alpaca holds {alpaca_qty} shares. Cannot cover without short position."
                )
                await self._update_trade(trade_id, None, "SKIPPED_NO_POSITION")
                return {"status": "SKIPPED_NO_POSITION", "order_id": None}
            short_shares = int(abs(alpaca_qty))
            if quantity > short_shares:
                logger.warning(
                    f"[Alpaca] CAPPING COVER for {ticker}: "
                    f"requested {quantity}, Alpaca is short {short_shares}. "
                    f"Submitting {short_shares} instead."
                )
                quantity = short_shares

        order_request = MarketOrderRequest(
            symbol=ticker,
            qty=quantity,
            side=side,
            time_in_force=time_in_force,
            client_order_id=client_order_id,
        )

        try:
            order = self._client.submit_order(order_request)
            order_id_str = str(order.id) if order.id else None
            persisted = bool(await self._update_trade(trade_id, order_id_str, "SUBMITTED"))
            logger.info(
                f"[Alpaca] Submitted market order {signal} {quantity} {ticker} ({time_in_force.value}) "
                f"(OrderID: {order_id_str}, ClientOrderID: {client_order_id})"
            )
            return {"status": "SUBMITTED", "order_id": order_id_str, "persisted": persisted}
        except Exception:
            logger.exception(f"[Alpaca] Failed to submit market order for {ticker}")
            persisted = bool(await self._update_trade(trade_id, None, "ERROR"))
            return {"status": "ERROR", "order_id": None, "persisted": persisted}

    async def cancel_open_orders_for_agent(self, agent_id: str, ticker: str | None = None) -> int:
        """Cancel open Alpaca orders belonging to a specific agent."""
        if not self._client:
            return 0

        try:
            from alpaca.trading.enums import QueryOrderStatus
            from alpaca.trading.requests import GetOrdersRequest

            req = GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[ticker] if ticker else None)
            open_orders = self._client.get_orders(filter=req)
            cancelled_count = 0
            prefix = f"{agent_id}__"
            for order in open_orders:
                client_id = getattr(order, "client_order_id", "") or ""
                if client_id.startswith(prefix):
                    self._client.cancel_order_by_id(order.id)
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
