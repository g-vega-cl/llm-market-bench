"""Alpaca paper trading broker integration for third-party audit.

Supabase remains the source of truth. Alpaca is fire-and-forget.
Every executed trade is mirrored as a DAY limit order, tagged with agent metadata.
"""

import logging
from uuid import UUID

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest

from core.config import ALPACA_API_KEY, ALPACA_ENABLED, ALPACA_PAPER_ENDPOINT, ALPACA_SECRET_KEY
from core.db import get_supabase_client

logger = logging.getLogger("engine")


class AlpacaBroker:
    """Thin wrapper around Alpaca Trading API for limit order submission."""

    def __init__(self):
        self._client: TradingClient | None = None

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
        trade_id: UUID,
        ticker: str,
        quantity: int,
        signal: str,
        limit_price: float,
        agent_id: str,
    ) -> None:
        """Fire-and-forget DAY limit order submission to Alpaca.

        Tags the order with agent metadata (client_order_id) for audit filtering.
        Updates the trades row asynchronously after submission attempt.

        SELL orders are guarded against shorting: if Alpaca does not hold the
        requested shares, the order is skipped or quantity-capped to the actual
        Alpaca position size.
        """
        if not self._client:
            return

        side = OrderSide.BUY if signal.upper() == "BUY" else OrderSide.SELL
        client_order_id = f"{agent_id}__{ticker}__{signal}__{str(trade_id)}"

        # Guardrail: prevent shorting in Alpaca on SELL orders
        if side == OrderSide.SELL:
            alpaca_qty = self.get_alpaca_position(ticker)
            if alpaca_qty <= 0:
                supabase_qty = self._get_supabase_position(ticker, agent_id)
                if supabase_qty > 0:
                    logger.info(
                        f"[Alpaca] Supabase shows {supabase_qty} {ticker} shares, "
                        f"overriding Alpaca position (0 shares)."
                    )
                    quantity = min(quantity, supabase_qty)
                else:
                    logger.warning(
                        f"[Alpaca] SKIPPED SELL {quantity} {ticker}: "
                        f"Alpaca holds {alpaca_qty} shares. No shorting allowed."
                    )
                    await self._update_trade(trade_id, None, "SKIPPED_NO_POSITION")
                    return
            elif quantity > alpaca_qty:
                logger.warning(
                    f"[Alpaca] CAPPING SELL for {ticker}: "
                    f"requested {quantity}, Alpaca holds {alpaca_qty}. "
                    f"Submitting {alpaca_qty} instead."
                )
                quantity = int(alpaca_qty)

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
            await self._update_trade(trade_id, order_id_str, "SUBMITTED")
            logger.info(
                f"[Alpaca] Submitted {signal} {quantity} {ticker} @ ${limit_price:.2f} "
                f"(OrderID: {order_id_str}, ClientOrderID: {client_order_id})"
            )
        except Exception:
            logger.exception(f"[Alpaca] Failed to submit order for {ticker}")
            await self._update_trade(trade_id, None, "ERROR")

    async def _update_trade(self, trade_id: UUID, order_id: str | None, status: str) -> None:
        """Update the trades row with Alpaca metadata."""
        try:
            supabase = get_supabase_client()
            payload: dict = {
                "alpaca_status": status,
                "alpaca_submitted_at": "now()",
            }
            if order_id:
                payload["alpaca_order_id"] = str(order_id)

            supabase.table("trades").update(payload).eq("id", str(trade_id)).execute()
        except Exception as exc:
            logger.error(f"[Alpaca] Failed to update trade {trade_id} status: {exc}")

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
