"""Alpaca paper trading broker integration for third-party audit.

Supabase remains the source of truth. Alpaca is fire-and-forget.
Every executed trade is mirrored as a DAY limit order, tagged with agent metadata.
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from core.config import ALPACA_ENABLED, ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER_ENDPOINT
from core.db import get_supabase_client

logger = logging.getLogger("engine")


class AlpacaBroker:
    """Thin wrapper around Alpaca Trading API for limit order submission."""

    def __init__(self):
        self._client: Optional[TradingClient] = None

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
        """
        if not self._client:
            return

        side = OrderSide.BUY if signal.upper() == "BUY" else OrderSide.SELL
        client_order_id = f"{agent_id}__{ticker}__{signal}__{str(trade_id)}"

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
            await self._update_trade(trade_id, order_id_str, "PENDING")
            logger.info(
                f"[Alpaca] Submitted {signal} {quantity} {ticker} @ ${limit_price:.2f} "
                f"(OrderID: {order_id_str}, ClientOrderID: {client_order_id})"
            )
        except Exception as exc:
            logger.error(f"[Alpaca] Failed to submit order for {ticker}: {exc}")
            await self._update_trade(trade_id, None, "ERROR")

    async def _update_trade(
        self, trade_id: UUID, order_id: Optional[str], status: str
    ) -> None:
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