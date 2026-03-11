"""Portfolio management and Reg T4 calculation modules.

This module handles the tracking of cash, positions, and purchasing power
for each LLM agent, utilizing the database for persistence.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List
from uuid import UUID

from core.db import get_supabase_client

logger = logging.getLogger("engine")


@dataclass
class Position:
    ticker: str
    quantity: int
    average_cost_basis: float


from .reg_t_validation import calculate_reg_t_metrics, validate_trade_compliance, RegTMetrics, ValidationResult


class Portfolio:
    """Manages an agent's portfolio state and Reg T calculations."""

    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self.id: Optional[UUID] = None
        self.cash_balance: float = 10000.00
        self.sma: float = 0.0
        self.positions: Dict[str, Position] = {}
        # Metrics cache
        self.metrics: Optional[RegTMetrics] = None

    async def initialize(self):
        """Loads from DB or creates a new portfolio if none exists."""
        supabase = get_supabase_client()
        
        # Try to fetch existing
        res = supabase.table("portfolios").select("*").eq("owner_id", self.owner_id).execute()
        
        if res.data:
            data = res.data[0]
            self.id = data["id"]
            self.cash_balance = float(data["cash_balance"])
            self.sma = float(data.get("sma", 0.0))
            
            # Reconstruct metrics if available in DB
            if data.get("buying_power") is not None:
                self.metrics = RegTMetrics(
                    total_equity=float(data.get("total_equity", 0.0)),
                    initial_margin_req=0.0,  # Not stored in DB
                    maintenance_margin_req=float(data.get("maintenance_margin", 0.0)),
                    available_funds=0.0,     # Not stored in DB
                    excess_liquidity=float(data.get("excess_liquidity", 0.0)),
                    sma=self.sma,
                    realized=float(data.get("realized", self.cash_balance)),
                    buying_power=float(data["buying_power"])
                )
            
            # Load positions
            self._await_load_positions(supabase)
        else:
            # Create new
            # For a new $10k account, SMA starts equal to Cash? 
            # Or 0? Usually SMA starts at 0 and grows with income/interest or is created by excess equity?
            # Reg T: SMA = Cash on deposit. if 10k cash dep, SMA=10k.
            # Let's start with 10k default if cash is 10k
            self.sma = 10000.00
            
            res = supabase.table("portfolios").insert({
                "owner_id": self.owner_id,
                "cash_balance": 10000.00,
                "sma": 10000.00
            }).execute()
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
        for p in pos_res.data:
            ticker = p["ticker"].upper()
            self.positions[ticker] = Position(
                ticker=ticker,
                quantity=p["quantity"],
                average_cost_basis=float(p["average_cost_basis"])
            )

    def calculate_reg_t_metrics(self, current_prices: Dict[str, float]) -> RegTMetrics:
        """Calculates Reg T margin metrics based on current market prices.
        
        Delegates to the granular logic in reg_t_validation.py.
        """
        # Convert to format needed by Reg T module: list or dict of raw values
        # The module expects dict[str, dict] where dict has 'quantity'
        # We have dict[str, Position]
        
        pos_for_calc = {}
        for t, p in self.positions.items():
            pos_for_calc[t] = {
                "quantity": p.quantity,
                "average_cost_basis": p.average_cost_basis
            }
            
        self.metrics = calculate_reg_t_metrics(
            cash_balance=self.cash_balance,
            positions=pos_for_calc,
            current_prices=current_prices,
            previous_sma=self.sma
        )
        # Update our internal state SMA to the result of the calculation (Ratchet Up)
        # BUT: calculate_metrics doesn't include todays trades effects on SMA yet (spend).
        # It calculates the state based on "Current Holdings".
        self.sma = self.metrics.sma 
        
        return self.metrics

    async def get_portfolio_summary(self, current_prices: Dict[str, float]) -> str:
        """Generates a text summary for the LLM prompt."""
        metrics = self.calculate_reg_t_metrics(current_prices)
        
        summary = [
            f"Cash Balance: ${self.cash_balance:,.2f}",
            f"Total Equity: ${metrics.total_equity:,.2f}",
            f"Buying Power: ${metrics.buying_power:,.2f}",
            f"SMA: ${metrics.sma:,.2f}",
            f"Realized Value (Cash + Cost Basis): ${metrics.realized:,.2f}",
            f"Maintenance Margin: ${metrics.maintenance_margin_req:,.2f}",
            "\nCurrent Positions:"
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
            for t in recent_trades:
                # Format: [Date] SIGNAL ticker: qty @ price (Reason: ...)
                date_str = t.get("executed_at", "").split("T")[0]
                reason = t.get("reasoning", "No reasoning stored.")
                if len(reason) > 100:
                    reason = reason[:97] + "..."
                summary.append(
                    f"- [{date_str}] {t['signal']} {t['ticker']}: {t['quantity']} @ ${float(t['price']):.2f} "
                    f"(Reason: {reason})"
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
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            
            # Fetch trades for this portfolio
            response = client.table("trades").select(
                "ticker", "signal", "quantity", "price", "executed_at", "decision_id"
            ).eq("portfolio_id", self.id).gte("executed_at", cutoff).order("executed_at", desc=True).execute()
            
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
        supabase.table("portfolios").update({
            "total_equity": self.metrics.total_equity,
            "buying_power": self.metrics.buying_power,
            "excess_liquidity": self.metrics.excess_liquidity,
            "maintenance_margin": self.metrics.maintenance_margin_req,
            "sma": self.metrics.sma,
            "realized": self.metrics.realized,
            "last_updated_at": "now()"
        }).eq("id", self.id).execute()
        
        logger.info(f"Updated portfolios summary table for {self.owner_id}.")

    def validate_trade(self, ticker: str, quantity: int, price: float, signal: str = "BUY") -> ValidationResult:
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
            signal=signal
        )

    async def execute_trade(self, ticker: str, quantity: int, price: float, signal: str) -> Optional[UUID]:
        """Executes the trade by updating cash, positions, and ledger.
        
        Args:
            ticker: Symbol.
            quantity: Number of shares (always positive).
            price: Execution price.
            signal: "BUY" or "SELL".
            
        Returns:
            The UUID of the generated trade record, or None if failed.
        """
        if not self.id:
            logger.error("Cannot execute trade on uninitialized portfolio.")
            return

        ticker = ticker.upper()
        total_cost = price * quantity
        supabase = get_supabase_client()
        
        # Update local state first
        if signal.upper() == "BUY":
            self.cash_balance -= total_cost
            
            # Update Position
            if ticker in self.positions:
                pos = self.positions[ticker]
                old_cost = pos.average_cost_basis * pos.quantity
                new_cost = old_cost + total_cost
                pos.quantity += quantity
                pos.average_cost_basis = new_cost / pos.quantity
            else:
                self.positions[ticker] = Position(
                    ticker=ticker,
                    quantity=quantity,
                    average_cost_basis=price
                )
            # Update SMA: Buying reduces SMA by 57% of the trade value (Since Reg T IM is 57%)
            # Reg T Rule: SMA is reduced by the Margin Requirement of the new trade.
            margin_req = total_cost * 0.57
            self.sma -= margin_req
                
        elif signal.upper() == "SELL":
            # Update Position
            if ticker in self.positions:
                pos = self.positions[ticker]
                
                # Guardrail: Cannot sell more than owned
                if quantity > pos.quantity:
                    logger.warning(
                        f"Attempted to sell {quantity} shares of {ticker} but only held {pos.quantity}. "
                        "Capping sell to owned quantity."
                    )
                    quantity = pos.quantity
                
                # Recalculate total_cost based on potentially capped quantity
                total_cost = price * quantity
                self.cash_balance += total_cost

                pos.quantity -= quantity
                if pos.quantity == 0:
                    del self.positions[ticker]
            else:
                logger.warning(f"REJECTED: Selling {ticker} but not held in portfolio.")
                return None

            
            # Update SMA: Selling releases margin. SMA increases by 57% of proceeds?
            # Or rather, SMA state is recalculated?
            # If we sell, Cash increases.
            # Reg T: SMA increases by amount of line released?
            # Let's simplify: SMA += 57% of Proceeds (since we got cash back and released 57% req).
            margin_released = total_cost * 0.57
            self.sma += margin_released
        
        # Persist changes
        try:
            # 1. Update/Insert/Delete Position
            current_pos = self.positions.get(ticker)
            if current_pos:
                supabase.table("portfolio_positions").upsert({
                    "portfolio_id": str(self.id),
                    "ticker": ticker,
                    "quantity": current_pos.quantity,
                    "average_cost_basis": current_pos.average_cost_basis
                }, on_conflict="portfolio_id,ticker").execute()
            else:
                 # It was deleted (position closed)
                 supabase.table("portfolio_positions").delete().match({
                     "portfolio_id": str(self.id),
                     "ticker": ticker
                 }).execute()
            
            # 2. Insert into Trades Ledger
            trade_res = supabase.table("trades").insert({
                "portfolio_id": str(self.id),
                "ticker": ticker,
                "signal": signal,
                "quantity": quantity,
                "price": price,
                "total_cost": total_cost,
                "executed_at": "now()"
            }).execute()
            
            trade_id = trade_res.data[0]["id"] if trade_res.data else None
            
            # 3. ONLY NOW update Portfolio Cash & SMA (The "Commit" step)
            # This ensures we don't deduct cash if the ledger or positions failed
            supabase.table("portfolios").update({
                "cash_balance": self.cash_balance,
                "sma": self.sma,
                "last_updated_at": "now()"
            }).eq("id", self.id).execute()
            
            logger.info(f"Executed {signal} {quantity} {ticker} @ ${price:.2f}. New Cash: ${self.cash_balance:,.2f}")
            logger.info(f"Trade successfully ledged. TradeID: {trade_id}")
            
            # 4. Update and save metrics to ensure table consistency
            # Use current prices for all held positions to avoid fallbacks
            current_prices = {t: p.average_cost_basis for t, p in self.positions.items()}
            current_prices[ticker] = price  # Ensure the execution price is used for the current trade
            
            self.calculate_reg_t_metrics(current_prices)
            await self.save_metrics()

            return trade_id
            
        except Exception as e:
            logger.error(f"DB Error executing trade for {ticker}: {e}")
            # In real system: Rollback local state
            return None

    async def record_performance_snapshot(self, current_prices: Dict[str, float]):
        """Records an immutable daily performance snapshot of the portfolio."""
        if not self.id:
            logger.error("Cannot snapshot uninitialized portfolio.")
            return

        # Ensure we have the latest metrics
        metrics = self.calculate_reg_t_metrics(current_prices)
        
        supabase = get_supabase_client()
        try:
            # We use an explicit date and on_conflict to ensure idempotency.
            from datetime import date
            today = date.today().isoformat()

            res = supabase.table("portfolio_performance").upsert({
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
                "date": today
            }, on_conflict="portfolio_id,date").execute()
            
            if res.data:
                logger.info(
                    f"Performance snapshot saved for {self.owner_id}. "
                    f"Equity: ${metrics.total_equity:,.2f}"
                )
        except Exception as e:
            logger.error(f"Failed to save performance snapshot for {self.owner_id}: {e}")

