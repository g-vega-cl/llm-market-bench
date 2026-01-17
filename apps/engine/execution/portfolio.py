"""Portfolio management and Reg T4 calculation modules.

This module handles the tracking of cash, positions, and purchasing power
for each LLM agent, utilizing the database for persistence.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import UUID

from core.db import get_supabase_client

logger = logging.getLogger("engine")


@dataclass
class Position:
    ticker: str
    quantity: int
    average_cost_basis: float


@dataclass
class RegTMetrics:
    total_equity: float
    maintenance_margin: float
    excess_liquidity: float
    buying_power: float


class Portfolio:
    """Manages an agent's portfolio state and Reg T calculations."""

    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self.id: Optional[UUID] = None
        self.cash_balance: float = 10000.00
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
            # Load positions
            self._await_load_positions(supabase)
        else:
            # Create new
            res = supabase.table("portfolios").insert({
                "owner_id": self.owner_id,
                "cash_balance": 10000.00
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
            self.positions[p["ticker"]] = Position(
                ticker=p["ticker"],
                quantity=p["quantity"],
                average_cost_basis=float(p["average_cost_basis"])
            )

    def calculate_reg_t_metrics(self, current_prices: Dict[str, float]) -> RegTMetrics:
        """Calculates Reg T margin metrics based on current market prices.
        
        Logic reference: docs/account-buying-power-reg-t4-calculations.md
        """
        stock_value = 0.0
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, 0.0)
            if price == 0.0:
                logger.warning(f"No price found for {ticker}, assuming $0 for margin calc.")
            stock_value += pos.quantity * price

        total_equity = self.cash_balance + stock_value
        
        # Reg T Initial Margin is typically 50% for Longs
        # Maintenance Margin is typically 25% for Longs
        # The doc suggests Maintenance Margin is what drives Excess Liquidity for BP?
        # Let's align with the Doc's Scenario 1:
        # Stock Value: $9950.24. MM: $2487.56. (This is 25%)
        
        maintenance_margin = stock_value * 0.25
        
        # Excess Liquidity = Equity - Maintenance Margin
        # (Note: In strict Reg T, it's Euity - Reg T Margin, but IBKR/Docs use MM for some internal calculations.
        # However, Scenario 1 BP is 4x Excess. If Excess = Equity - IM, then BP = 4 * (Equity-IM)?
        # Doc S1: Equity 10k, IM 2487. Excess 7512. BP 30049.
        # 30049 / 7512 = ~4.0.
        # Excess there is Equity - MM.
        # So we use MM = 0.25 * Stock Value.
        
        excess_liquidity = total_equity - maintenance_margin
        
        # Buying Power = 4 * Excess Liquidity
        # (Capped at 0 if negative)
        buying_power = max(0.0, excess_liquidity * 4.0)

        # Update detailed metrics
        self.metrics = RegTMetrics(
            total_equity=total_equity,
            maintenance_margin=maintenance_margin,
            excess_liquidity=excess_liquidity,
            buying_power=buying_power
        )
        return self.metrics

    def get_portfolio_summary(self, current_prices: Dict[str, float]) -> str:
        """Generates a text summary for the LLM prompt."""
        metrics = self.calculate_reg_t_metrics(current_prices)
        
        summary = [
            f"Cash Balance: ${self.cash_balance:,.2f}",
            f"Total Equity: ${metrics.total_equity:,.2f}",
            f"Buying Power: ${metrics.buying_power:,.2f}",
            f"Maintenance Margin: ${metrics.maintenance_margin:,.2f}",
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
                
        return "\n".join(summary)

    async def save_metrics(self):
        """Persists the latest calculated metrics to the DB."""
        if not self.metrics or not self.id:
            return

        supabase = get_supabase_client()
        supabase.table("portfolios").update({
            "total_equity": self.metrics.total_equity,
            "buying_power": self.metrics.buying_power,
            "excess_liquidity": self.metrics.excess_liquidity,
            "maintenance_margin": self.metrics.maintenance_margin,
            "last_updated_at": "now()"
        }).eq("id", self.id).execute()
