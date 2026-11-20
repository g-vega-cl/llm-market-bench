"""Portfolio management and Reg T4 calculation modules.

This module handles the tracking of cash, positions, and purchasing power
for each LLM agent, utilizing the database for persistence.
"""

import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from core.db import async_with_retry, get_supabase_client

from .reg_t_validation import (
    RegTMetrics,
    ValidationResult,
    calculate_reg_t_metrics,
    validate_trade_compliance,
)

logger = logging.getLogger("engine")


@dataclass
class Position:
    ticker: str
    quantity: int
    average_cost_basis: float


class Portfolio:
    """Manages an agent's portfolio state and Reg T calculations."""

    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self.id: UUID | None = None
        self.cash_balance: float = 10000.00
        self.sma: float = 0.0
        self.positions: dict[str, Position] = {}
        # Metrics cache
        self.metrics: RegTMetrics | None = None

    @property
    def total_equity(self) -> float:
        if self.metrics:
            return self.metrics.total_equity
        return self.cash_balance

    async def initialize(self):
        """Loads from DB or creates a new portfolio if none exists."""
        supabase = get_supabase_client()

        # Reset cached state to ensure JIT refresh integrity
        self.metrics = None
        self.positions = {}

        # Try to fetch existing
        res = supabase.table("portfolios").select("*").eq("owner_id", self.owner_id).execute()

        if res.data:
            data = res.data[0]
            self.id = data["id"]
            self.cash_balance = float(data.get("cash_balance") or 0.0)
            self.sma = float(data.get("sma") or 0.0)

            # Reconstruct metrics if available in DB
            if data.get("buying_power") is not None:
                self.metrics = RegTMetrics(
                    total_equity=float(data.get("total_equity") or 0.0),
                    initial_margin_req=0.0,  # Not stored in DB
                    maintenance_margin_req=float(data.get("maintenance_margin") or 0.0),
                    available_funds=0.0,  # Not stored in DB
                    excess_liquidity=float(data.get("excess_liquidity") or 0.0),
                    sma=self.sma,
                    realized=float(data.get("realized") if data.get("realized") is not None else self.cash_balance),
                    buying_power=float(data.get("buying_power") or 0.0),
                )
            else:
                self.calculate_reg_t_metrics({})

            # Load positions
            self._await_load_positions(supabase)
        else:
            # Create new portfolio with full initial metrics
            self.sma = self.cash_balance
            self.calculate_reg_t_metrics({})

            res = (
                supabase.table("portfolios")
                .insert(
                    {
                        "owner_id": self.owner_id,
                        "cash_balance": self.cash_balance,
                        "sma": self.sma,
                        "total_equity": self.metrics.total_equity if self.metrics else self.cash_balance,
                        "buying_power": self.metrics.buying_power if self.metrics else self.cash_balance,
                        "excess_liquidity": self.metrics.excess_liquidity if self.metrics else self.cash_balance,
                        "maintenance_margin": self.metrics.maintenance_margin_req if self.metrics else 0.0,
                        "realized": self.metrics.realized if self.metrics else self.cash_balance,
                    }
                )
                .execute()
            )
            if res.data:
                self.id = res.data[0]["id"]
                logger.info(f"Initialized new portfolio for {self.owner_id} with $10,000.")
            else:
                raise Exception(f"Failed to create portfolio for {self.owner_id}")

    def _await_load_positions(self, supabase):
        """Helper to load positions synchronously (since called from async init)."""
        # Note: In a real async flow we'd await this. Supabase python client is synchronous?
        # The 'supabase-py' client is technically synchronous wrapping postgrest,
        # but if we are in an async function we should verify usage.
        # Assuming standard usage here.
        pos_res = supabase.table("portfolio_positions").select("*").eq("portfolio_id", self.id).execute()
        # Note: self.positions is already cleared in initialize() before this call
        for p in pos_res.data:
            ticker = p["ticker"].upper()
            self.positions[ticker] = Position(
                ticker=ticker, quantity=p["quantity"], average_cost_basis=float(p["average_cost_basis"])
            )

    def calculate_reg_t_metrics(self, current_prices: dict[str, float]) -> RegTMetrics:
        """Calculates Reg T margin metrics based on current market prices.

        Delegates to the granular logic in reg_t_validation.py.
        """
        # Convert to format needed by Reg T module: list or dict of raw values
        # The module expects dict[str, dict] where dict has 'quantity'
        # We have dict[str, Position]

        pos_for_calc = {}
        for t, p in self.positions.items():
            pos_for_calc[t] = {"quantity": p.quantity, "average_cost_basis": p.average_cost_basis}

        self.metrics = calculate_reg_t_metrics(
            cash_balance=self.cash_balance, positions=pos_for_calc, current_prices=current_prices, previous_sma=self.sma
        )
        # Update our internal state SMA to the result of the calculation (Ratchet Up)
        # BUT: calculate_metrics doesn't include todays trades effects on SMA yet (spend).
        # It calculates the state based on "Current Holdings".
        self.sma = self.metrics.sma

        return self.metrics

    async def get_portfolio_summary(self, current_prices: dict[str, float]) -> str:
        """Generates a text summary for the LLM prompt."""
        metrics = self.calculate_reg_t_metrics(current_prices)

        summary = [
            f"Cash Balance: ${self.cash_balance:,.2f}",
            f"Total Equity: ${metrics.total_equity:,.2f}",
            f"Buying Power: ${metrics.buying_power:,.2f}",
            f"Realized Value (Cash + Cost Basis): ${metrics.realized:,.2f}",
            "\nCurrent Positions:",
        ]

        if not self.positions:
            summary.append("- None")
        else:
            for ticker, pos in self.positions.items():
                curr_price = current_prices.get(ticker, 0.0)
                pl = (curr_price - pos.average_cost_basis) * pos.quantity
                pl_pct = ((curr_price / pos.average_cost_basis) - 1) * 100 if pos.average_cost_basis else 0
                summary.append(
                    f"- {ticker}: {pos.quantity} shares @ ${pos.average_cost_basis:.2f} "
                    f"(Curr: ${curr_price:.2f}, P/L: ${pl:.2f} / {pl_pct:.1f}%)"
                )

        # Add Recent Trades Section
        recent_trades = await self.get_recent_trades(hours=48)
        if recent_trades:
            summary.append("\nRecently Executed Trades (Last 48h):")
            now = datetime.now(UTC)
            for t in recent_trades:
                # Format: SIGNAL ticker: qty @ price (Time Ago) - Reason: ...
                executed_at_str = t.get("executed_at", "")
                reason = t.get("reasoning", "No reasoning stored.")

                # Calculate Time Ago
                time_ago = "recently"
                if executed_at_str:
                    try:
                        # executed_at is usually ISO format with TZ
                        # 2024-03-24T12:00:00+00:00
                        from dateutil import parser

                        exec_time = parser.isoparse(executed_at_str)
                        if exec_time.tzinfo is None:
                            exec_time = exec_time.replace(tzinfo=UTC)

                        diff = now - exec_time

                        if diff.total_seconds() < 3600:
                            mins = int(diff.total_seconds() / 60)
                            time_ago = f"{mins}m ago"
                        elif diff.total_seconds() < 86400:
                            hrs = int(diff.total_seconds() / 3600)
                            time_ago = f"{hrs}h ago"
                        else:
                            days = int(diff.total_seconds() / 86400)
                            time_ago = f"{days}d ago"
                    except Exception as e:
                        logger.warning(f"Error parsing executed_at '{executed_at_str}': {e}")

                if len(reason) > 100:
                    reason = reason[:97] + "..."

                summary.append(
                    f"- {t['signal']} {t['ticker']}: {t['quantity']} @ ${float(t['price']):.2f} "
                    f"({time_ago}) - Reason: {reason}"
                )

        return "\n".join(summary)

    async def get_recent_trades(self, hours: int = 48) -> list[dict[str, Any]]:
        """Fetches the actual trade ledger for the portfolio from the DB.

        Args:
            hours: How far back to look.

        Returns:
            List of trade records with associated reasoning.
        """
        if not self.id:
            return []

        try:
            client = get_supabase_client()
            cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

            # Fetch trades for this portfolio
            response = (
                client.table("trades")
                .select(
                    "ticker",
                    "signal",
                    "quantity",
                    "price",
                    "executed_at",
                    "decision_id",
                    "realized_pnl",
                    "realized_pnl_pct",
                )
                .eq("portfolio_id", self.id)
                .gte("executed_at", cutoff)
                .order("executed_at", desc=True)
                .execute()
            )

            trades = response.data or []

            # Enrich with reasoning from decisions table
            for trade in trades:
                d_id = trade.get("decision_id")
                if d_id:
                    d_res = client.table("decisions").select("reasoning").eq("id", d_id).execute()
                    if d_res.data:
                        trade["reasoning"] = d_res.data[0].get("reasoning")

            return trades
        except Exception as e:
            logger.error(f"Error fetching recent trades for {self.owner_id}: {e}")
            return []

    async def save_metrics(self):
        """Persists the latest calculated metrics to the DB."""
        if not self.metrics or not self.id:
            return

        supabase = get_supabase_client()
        await async_with_retry(
            lambda: (
                supabase.table("portfolios")
                .update(
                    {
                        "total_equity": self.metrics.total_equity,
                        "buying_power": self.metrics.buying_power,
                        "excess_liquidity": self.metrics.excess_liquidity,
                        "maintenance_margin": self.metrics.maintenance_margin_req,
                        "sma": self.metrics.sma,
                        "realized": self.metrics.realized,
                        "last_updated_at": "now()",
                    }
                )
                .eq("id", self.id)
                .execute()
            ),
            f"save_metrics_{self.owner_id}",
        )

        logger.info(f"Updated portfolios summary table for {self.owner_id}.")

    def validate_trade(
        self, ticker: str, quantity: int, price: float, signal: str = "BUY", is_sell_tool_used: bool = False
    ) -> ValidationResult:
        """Validates a potential trade against current Reg T buying power."""
        if not self.metrics:
            # Should imply we need to calculate
            # For safe usage, assume 0 prices if not provided, or better, fail.
            # But the caller should have updated metrics recently.
            logger.warning("Validating trade with stale metrics (None). Assuming 0 BP.")
            return ValidationResult(passed=False, reason="Metrics not initialized.")

        cost = price * quantity
        return validate_trade_compliance(
            portfolio_metrics=self.metrics,
            estimated_trade_cost=cost,
            ticker=ticker,
            price=price,
            signal=signal,
            is_sell_tool_used=is_sell_tool_used,
        )

    def _validate_trade_preflight(self, ticker: str, quantity: int, price: float, signal: str) -> tuple[int, bool]:
        """Validate trade parameters and local cash/position bounds without mutating state."""
        sig = signal.upper()
        if quantity <= 0 or not math.isfinite(price) or price <= 0:
            logger.error(f"REJECTED: Invalid trade quantity={quantity} or price={price} for {ticker}.")
            return quantity, False

        if sig == "BUY":
            total_cost = price * quantity
            if total_cost > self.cash_balance:
                logger.error(
                    f"REJECTED: Cannot buy {quantity} {ticker} for ${total_cost:,.2f}. "
                    f"Available cash balance is only ${self.cash_balance:,.2f}."
                )
                return quantity, False
            return quantity, True

        if sig == "SELL":
            if ticker not in self.positions:
                logger.warning(f"REJECTED: Selling {ticker} but not held in portfolio.")
                return quantity, False
            held_qty = self.positions[ticker].quantity
            if quantity > held_qty:
                logger.warning(
                    f"Attempted to sell {quantity} shares of {ticker} but only held {held_qty}. "
                    "Capping sell to owned quantity."
                )
                quantity = held_qty
            return quantity, True

        logger.error(f"REJECTED: Invalid trade signal '{signal}' for {ticker}.")
        return quantity, False

    async def execute_trade(
        self,
        ticker: str,
        quantity: int,
        price: float,
        signal: str,
        decision_id: str | None = None,
        current_prices: dict[str, float] = None,
        skip_alpaca_mirror: bool = False,
        reason: str | None = None,
    ) -> UUID | None:
        """Executes the trade atomically via the execute_portfolio_trade Postgres RPC.

        Args:
            ticker: Symbol.
            quantity: Number of shares (always positive).
            price: Execution price.
            signal: "BUY" or "SELL".
            decision_id: Optional ID of the decision that triggered this trade.
            current_prices: Optional map of all portfolio prices to avoid re-fetching.
            skip_alpaca_mirror: Whether to bypass Alpaca paper order mirroring.
            reason: Optional explanation or catalyst justifying this trade.

        Returns:
            The UUID of the generated trade record, or None if failed.
        """
        if not self.id:
            logger.error("Cannot execute trade on uninitialized portfolio.")
            return None

        ticker = ticker.upper()
        sig = signal.upper()
        supabase = get_supabase_client()

        quantity, ok = self._validate_trade_preflight(ticker, quantity, price, sig)
        if not ok:
            return None

        merged_prices = (
            dict(current_prices)
            if current_prices is not None
            else {t: p.average_cost_basis for t, p in self.positions.items()}
        )
        merged_prices[ticker] = price

        idempotency_key = str(uuid4())
        rpc_params = {
            "p_portfolio_id": str(self.id),
            "p_ticker": ticker,
            "p_signal": sig,
            "p_quantity": quantity,
            "p_price": price,
            "p_decision_id": str(decision_id) if decision_id else None,
            "p_reason": reason,
            "p_idempotency_key": idempotency_key,
            "p_mark_prices": merged_prices,
        }

        try:
            rpc_res = await async_with_retry(
                lambda: supabase.rpc("execute_portfolio_trade", rpc_params).execute(),
                f"execute_portfolio_trade_{ticker}",
            )
            payload = rpc_res.data if isinstance(rpc_res.data, dict) else {}
            trade_id = payload.get("trade_id")
            if not trade_id:
                raise RuntimeError(f"execute_portfolio_trade returned no trade_id for {ticker}: {rpc_res.data}")
        except Exception:
            logger.exception(f"Atomic trade execution failed for {ticker}")
            return None

        self._sync_local_state_from_rpc(ticker, payload, merged_prices)
        exec_qty = int(payload.get("quantity") or quantity)
        logger.info(f"Executed {sig} {exec_qty} {ticker} @ ${price:.2f}. New Cash: ${self.cash_balance:,.2f}")
        logger.info(f"Trade successfully ledged. TradeID: {trade_id}")

        if not skip_alpaca_mirror:
            from execution.alpaca_broker import AlpacaBroker

            broker = AlpacaBroker()
            alpaca_limit = round(price * 1.005, 2) if sig == "BUY" else round(price * 0.995, 2)
            asyncio.create_task(
                broker.submit_limit_order(
                    trade_id=trade_id,
                    ticker=ticker,
                    quantity=exec_qty,
                    signal=sig,
                    limit_price=alpaca_limit,
                    agent_id=self.owner_id,
                )
            )

        return trade_id

    def _sync_local_state_from_rpc(
        self, ticker: str, payload: dict[str, Any], current_prices: dict[str, float]
    ) -> None:
        """Align in-memory cash, positions, and metrics with the committed RPC result."""
        if payload.get("cash_balance") is not None:
            self.cash_balance = float(payload["cash_balance"])
        if payload.get("sma") is not None:
            self.sma = float(payload["sma"])
        if "position_quantity" in payload:
            pos_qty = int(payload.get("position_quantity") or 0)
            if pos_qty > 0:
                avg_cost = float(payload.get("position_avg_cost") or 0.0)
                self.positions[ticker] = Position(ticker=ticker, quantity=pos_qty, average_cost_basis=avg_cost)
            else:
                self.positions.pop(ticker, None)
        self.calculate_reg_t_metrics(current_prices)

    async def _check_and_sell_dust_positions(self, current_prices: dict[str, float]):
        """Check all positions and automatically sell any that are below 10% of portfolio equity.

        This prevents portfolio pollution from small 'dust' positions after partial sells.

        Args:
            current_prices: Current market prices for all held positions.
        """
        if not self.metrics or not self.id:
            return

        total_equity = self.metrics.total_equity
        threshold = total_equity * 0.10  # 10% of portfolio equity

        dust_positions_to_sell = []
        for pos_ticker, pos in self.positions.items():
            pos_price = current_prices.get(pos_ticker, 0.0)
            pos_value = pos_price * pos.quantity
            if 0 < pos_value < threshold:
                dust_positions_to_sell.append((pos_ticker, pos.quantity, pos_price))

        for dust_ticker, dust_qty, dust_price in dust_positions_to_sell:
            if dust_qty <= 0 or dust_price <= 0:
                continue

            logger.info(
                f"[DUST CLEANUP] Automatically selling {dust_ticker} position: "
                f"{dust_qty} shares @ ${dust_price:.2f} = ${dust_qty * dust_price:,.2f} "
                f"(below 10% threshold of ${threshold:,.2f} for ${total_equity:,.2f} portfolio)"
            )
            await self.execute_trade(
                ticker=dust_ticker,
                quantity=dust_qty,
                price=dust_price,
                signal="SELL",
                current_prices=current_prices,
                skip_alpaca_mirror=True,
                reason="Automatic dust position cleanup: Position value below 10% of portfolio equity",
            )

    async def record_performance_snapshot(self, current_prices: dict[str, float]):
        """Records an immutable daily performance snapshot of the portfolio."""
        if not self.id:
            logger.error("Cannot snapshot uninitialized portfolio.")
            return

        # Ensure we have the latest metrics
        metrics = self.metrics or self.calculate_reg_t_metrics(current_prices)

        supabase = get_supabase_client()
        try:
            today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()

            res = await async_with_retry(
                lambda: (
                    supabase.table("portfolio_performance")
                    .upsert(
                        {
                            "portfolio_id": str(self.id),
                            "total_equity": metrics.total_equity,
                            "cash_balance": self.cash_balance,
                            "buying_power": metrics.buying_power,
                            "sma": metrics.sma,
                            "initial_margin_req": metrics.initial_margin_req,
                            "maintenance_margin_req": metrics.maintenance_margin_req,
                            "available_funds": metrics.available_funds,
                            "excess_liquidity": metrics.excess_liquidity,
                            "realized": metrics.realized,
                            "date": today,
                        },
                        on_conflict="portfolio_id,date",
                    )
                    .execute()
                ),
                f"record_performance_snapshot_{self.owner_id}",
            )

            if res.data:
                logger.info(f"Performance snapshot saved for {self.owner_id}. Equity: ${metrics.total_equity:,.2f}")
        except Exception:
            logger.exception(f"Failed to save performance snapshot for {self.owner_id}")
