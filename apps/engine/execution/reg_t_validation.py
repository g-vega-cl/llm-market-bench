"""Regulation T (Reg T) Margin Calculation Module.

This module implements the logic for calculating account equity, margin requirements,
and buying power for a Reg-T margin account. It supports leverage scenarios as
defined in 'docs/account-buying-power-reg-t4-calculations.md'.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("engine")


@dataclass
class RegTMetrics:
    """Carries the calculated Reg T metrics for an account."""
    total_equity: float
    initial_margin_req: float
    maintenance_margin_req: float
    available_funds: float
    excess_liquidity: float
    sma: float           # Special Memorandum Account (Stateful)
    realized: float      # Realized Value (Cash + Cost Basis)
    buying_power: float


@dataclass
class ValidationResult:
    """Result of a trade compliance check."""
    passed: bool
    reason: Optional[str] = None
    max_affordable_shares: int = 0


def calculate_reg_t_metrics(
    cash_balance: float,
    positions: Dict[str, dict],
    current_prices: Dict[str, float],
    previous_sma: float = 0.0
) -> RegTMetrics:
    """Calculates granular Reg T metrics including stateful SMA.
    
    Args:
        cash_balance: Current cash (positive) or margin loan (negative).
        positions: Dictionary of held positions.
        current_prices: Dictionary of current market prices.
        previous_sma: The SMA value from the end of the previous day (or pre-trade).
        
    Returns:
        RegTMetrics object.
    """
    stock_value = 0.0
    
    for ticker, pos in positions.items():
        # Handle both dicts (from DB) and Position objects (from Portfolio class)
        if hasattr(pos, "quantity"):
            qty = pos.quantity
        elif isinstance(pos, dict):
            qty = pos.get("quantity", 0)
        else:
            qty = 0

        price = current_prices.get(ticker, 0.0)
        if price <= 0:
            logger.warning(f"Invalid price for {ticker}: {price}. Using 0 for margin calc.")
            price = 0.0
        stock_value += qty * price

    total_equity = cash_balance + stock_value
    
    # Standard Reg T Requirements
    # Initial Margin is usually 50% for new trades, but for existing portfolio state
    # we often track Maintenance Margin (25%).
    
    # For Buying Power calculations, BP = 4 * Excess Liquidity.
    # Excess Liquidity = Equity - Maintenance Margin.
    
    maintenance_margin_req = stock_value * 0.33
    initial_margin_req = stock_value * 0.57
    
    # Excess Liquidity = Equity - Maintenance Margin
    excess_liquidity = total_equity - maintenance_margin_req
    
    # Available Funds = Equity - Initial Margin (Regulation T Requirement)
    available_funds = total_equity - initial_margin_req
    
    # SMA Calculation (The Ratchet)
    # SMA is the greater of:
    # 1. Existing SMA (previous state)
    # 2. Current Equity - Initial Margin Requirement (a.k.a current surplus)
    # Note: This logic handles the "Market Gain" (ratchet up) and "Market Loss" (hold steady).
    # It does NOT handle the "Spend" (buying stock reduces SMA). The "Spend" logic happens at Trade Execution.
    # Here we are just calculating the state given current holdings/cash.
    
    # However, if cash changed (deposit/withdrawal), SMA changes. 
    # But here we assume we are calculating "Current State" based on holdings.
    # If the user just deposited cash, total_equity increased, so Eq-IM increased.
    
    # NOTE: In a strict simulation, SMA is a separate ledger. 
    # But for this "snapshot" logic, we follow the "Greater of" rule to determine
    # if the market move improved our condition.
    
    current_surplus = total_equity - initial_margin_req
    sma = max(previous_sma, current_surplus)

    # Buying Power
    # Buying Power = 2 * SMA (for Overnight) or 4 * Excess (intraday)?
    # The doc says "Buying Power = 4 * Excess Liquidity" in Scenario 1.
    # BUT in Scenario 1, Excess (7512) matches SMA (7512) if we assume starting fresh.
    # In Scenario 3 (Loss), Excess is 6328, SMA is 3500.
    # Buying Power should be based on SMA? 
    # Interactive Brokers T-Margin BP is usually based on Excess Liquidity for intraday opening.
    # But SMA limits overnight holds.
    # The User's Doc specifically has a row "Buying Power".
    # Scenario 3: Excess=6328. BP=12875? 6328 * 2 = 12656. 6328 * 4 = 25312.
    # user doc: "Buying Power | $12,875.60 | $3,218.90 x 4"
    # Wait, $3,218.90 is "Available Funds" in their S3 table.
    # So BP = 4 * Available Funds? 
    # Let's check S1 in Doc (Updated one).
    # S1: Avail Funds 5024. BP 20099. (5024 * 4 = 20096). Matches 4x Available Funds.
    # S2: Avail Funds 4218. BP 16875. (4218 * 4 = 16872). Matches.
    # S3: Avail Funds 3218. BP 12875. (3218 * 4 = 12872). Matches.
    
    # OK, REVISION: Buying Power in the user's updated doc is 4 * Available Funds (Equity - IM).
    # NOT 4 * Excess Liquidity (Equity - MM).
    
    buying_power = max(0.0, available_funds * 4.0)

    # Realized Value = Cash + Total Cost Basis
    # We need to sum cost basis from positions
    total_cost_basis = 0.0
    for ticker, pos in positions.items():
        if hasattr(pos, "average_cost_basis"):
            cost_basis = pos.average_cost_basis * (pos.quantity if hasattr(pos, "quantity") else 0)
        elif isinstance(pos, dict):
            cost_basis = float(pos.get("average_cost_basis", 0.0)) * int(pos.get("quantity", 0))
        else:
            cost_basis = 0.0
        total_cost_basis += cost_basis
    
    realized = cash_balance + total_cost_basis

    return RegTMetrics(
        total_equity=total_equity,
        initial_margin_req=initial_margin_req,
        maintenance_margin_req=maintenance_margin_req,
        available_funds=available_funds,
        excess_liquidity=excess_liquidity,
        sma=sma,
        realized=realized,
        buying_power=buying_power
    )


def validate_trade_compliance(
    portfolio_metrics: RegTMetrics,
    estimated_trade_cost: float,
    ticker: str,
    price: float
) -> ValidationResult:
    """Checks if a proposed BUY trade is compliant with margin limits.
    
    Rule:
        Trade Cost (Price * Qty) must be <= Buying Power.
        
    Args:
        portfolio_metrics: Current RegT metrics.
        estimated_trade_cost: Total cost of the trade (Price * Qty).
        ticker: Ticker symbol.
        price: Price per share.
        
    Returns:
        ValidationResult with pass/fail status.
    """
    if estimated_trade_cost <= 0:
        return ValidationResult(passed=True)

    if estimated_trade_cost > portfolio_metrics.buying_power:
        return ValidationResult(
            passed=False,
            reason=(
                f"Insufficient Buying Power for {ticker}. "
                f"Required: ${estimated_trade_cost:,.2f}, "
                f"Available BP: ${portfolio_metrics.buying_power:,.2f}"
            ),
            max_affordable_shares=int(portfolio_metrics.buying_power // price) if price > 0 else 0
        )

    # --- SMA Floor Guardrail ---
    # Rule: Projected SMA after trade must be >= 10% of Total Equity.
    # Buying stock reduces SMA by 57% of the cost.
    projected_sma = portfolio_metrics.sma - (estimated_trade_cost * 0.57)
    sma_floor = portfolio_metrics.total_equity * 0.10

    if projected_sma < sma_floor:
        return ValidationResult(
            passed=False,
            reason=(
                f"SMA Floor Violation for {ticker}. "
                f"Projected SMA: ${projected_sma:,.2f}, "
                f"Required Floor (10% Equity): ${sma_floor:,.2f}. "
                "This trade would risk Reg T compliance."
            ),
            max_affordable_shares=int(max(0, (portfolio_metrics.sma - sma_floor) // (price * 0.57))) if price > 0 else 0
        )
        
    return ValidationResult(passed=True)
