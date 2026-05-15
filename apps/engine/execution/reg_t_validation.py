"""Regulation T (Reg T) Margin Calculation Module.

This module implements the logic for calculating account equity, margin requirements,
and buying power for a Reg-T margin account. It supports leverage scenarios as
defined in 'raw/docs/engine/account-buying-power-reg-t4-calculations.md'.
"""

from dataclasses import dataclass

from core.config import MIN_TRADE_VALUE, logger


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
    reason: str | None = None
    max_affordable_shares: int = 0


def calculate_reg_t_metrics(
    cash_balance: float,
    positions: dict[str, dict],
    current_prices: dict[str, float],
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
    abs_stock_value = 0.0 # Used for margin requirements
    
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
            # FALLBACK: If market data is missing or invalid, use cost basis to prevent $0 valuation
            # which leads to negative equity for margin accounts.
            if hasattr(pos, "average_cost_basis"):
                price = pos.average_cost_basis
            elif isinstance(pos, dict):
                price = float(pos.get("average_cost_basis", 0.0))
            
            if price > 0:
                logger.warning(f"Market data missing for {ticker}. Falling back to cost basis (${price:.2f}) for margin calc.")
            else:
                logger.warning(f"Invalid price and no cost basis for {ticker}. Using 0 for margin calc.")
                price = 0.0
        
        stock_value += qty * price
        abs_stock_value += abs(qty) * price

    total_equity = cash_balance + stock_value
    
    # Standard Reg T Requirements
    # Initial Margin is usually 50% for new trades, but for existing portfolio state
    # we often track Maintenance Margin (25%).
    
    # For Buying Power calculations, BP = 4 * Excess Liquidity.
    # Excess Liquidity = Equity - Maintenance Margin.
    
    maintenance_margin_req = abs_stock_value * 0.33
    initial_margin_req = abs_stock_value * 0.57
    
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
    # Buying Power = 4 * Available Funds (Equity - IM).
    
    buying_power = max(0.0, available_funds * 4.0)
    
    # SANITY GUARDRAIL: Buying power cannot exceed 4x Total Equity (Theoretical limit)
    # This prevents corrupted states (negative margin) from inflating BP.
    theoretical_limit = max(0.0, total_equity * 4.0)
    if buying_power > theoretical_limit:
        logger.warning(
            f"Reg T Anomaly Detected: Calculated Buying Power (${buying_power:,.2f}) exceeds "
            f"theoretical limit (${theoretical_limit:,.2f}) for equity (${total_equity:,.2f}). Capping."
        )
        buying_power = theoretical_limit

    # Realized Value = Cash + Total Cost Basis
    # We need to sum cost basis from positions
    total_cost_basis = 0.0
    for _ticker, pos in positions.items():
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
    price: float,
    signal: str = "BUY",
    is_sell_tool_used: bool = False
) -> ValidationResult:
    """Checks if a proposed trade is compliant with margin limits and size requirements.
    
    Rules:
        1. Trade Cost must be <= Buying Power (for BUY).
        2. Minimum Trade Value: max($1,000, 10% of Buying Power or Total Equity).
        3. Projected SMA must be >= 10% of Total Equity.
        4. Sell Tool Bypass: If is_sell_tool_used is True, the $1,000 floor is waived for SELL orders.
        
    Args:
        portfolio_metrics: Current RegT metrics.
        estimated_trade_cost: Total cost of the trade (Price * Qty).
        ticker: Ticker symbol.
        price: Price per share.
        signal: "BUY" or "SELL".
        is_sell_tool_used: Whether a specific sell percentage tool was called.
        
    Returns:
        ValidationResult with pass/fail status.
    """
    signal = signal.upper()
    if estimated_trade_cost <= 0:
        return ValidationResult(passed=True)

    # --- BUY Capacity Check ---
    if signal == "BUY" and estimated_trade_cost > portfolio_metrics.buying_power:
        return ValidationResult(
            passed=False,
            reason=(
                f"Insufficient Buying Power for {ticker}. "
                f"Required: ${estimated_trade_cost:,.2f}, "
                f"Available BP: ${portfolio_metrics.buying_power:,.2f}"
            ),
            max_affordable_shares=int(portfolio_metrics.buying_power // price) if price > 0 else 0
        )

    # --- Dynamic Minimum Trade Value Guardrail (BUY only) ---
    if signal == "BUY":
        # Rule: 10% of Total Equity (not buying power) - per user request
        # This ensures meaningful position sizing based on actual account equity
        dynamic_floor = 0.10 * portfolio_metrics.total_equity
        # Ensure it doesn't drop below the global constant MIN_TRADE_VALUE ($1,000)
        final_floor = max(MIN_TRADE_VALUE, dynamic_floor)

        if estimated_trade_cost < final_floor:
            return ValidationResult(
                passed=False,
                reason=(
                    f"Trade value below dynamic minimum threshold of ${final_floor:,.2f} "
                    f"(10% of Equity). Proposed cost: ${estimated_trade_cost:,.2f}. "
                    "Consider increasing quantity to meet the meaningful position size requirement."
                )
            )
    elif signal == "SELL":
        # For SELL, we still enforce the absolute MIN_TRADE_VALUE ($1,000) to avoid dust trades
        # UNLESS a specific sell tool (10%, 25%, etc.) was used, in which case we allow any amount.
        if not is_sell_tool_used and estimated_trade_cost < MIN_TRADE_VALUE:
            return ValidationResult(
                passed=False,
                reason=(
                    f"SELL Trade value below minimum threshold of ${MIN_TRADE_VALUE:,.2f}. "
                    f"Proposed proceeds: ${estimated_trade_cost:,.2f}. "
                    "Bypass this guardrail by using a specific sell percentage tool (e.g., sell 25%)."
                )
            )

    # --- SMA Floor Guardrail (BUY only) ---
    if signal == "BUY":
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
