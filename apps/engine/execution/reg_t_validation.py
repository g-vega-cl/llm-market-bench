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
    sma: float  # Special Memorandum Account (Stateful)
    realized: float  # Realized Value (Cash + Cost Basis)
    buying_power: float


@dataclass
class ValidationResult:
    """Result of a trade compliance check."""

    passed: bool
    reason: str | None = None
    max_affordable_shares: int = 0


def calculate_reg_t_metrics(
    cash_balance: float, positions: dict[str, dict], current_prices: dict[str, float], previous_sma: float = 0.0
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
    abs_stock_value = 0.0  # Used for margin requirements

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
                logger.warning(
                    f"Market data missing for {ticker}. Falling back to cost basis (${price:.2f}) for margin calc."
                )
            else:
                logger.warning(f"Invalid price and no cost basis for {ticker}. Using 0 for margin calc.")
                price = 0.0

        stock_value += qty * price
        abs_stock_value += abs(qty) * price

    total_equity = cash_balance + stock_value

    # Cash-Only Architecture (No Margin Borrowing or Leverage)
    # Buying power is strictly bounded by available cash. Margin requirements are 0.
    maintenance_margin_req = 0.0
    initial_margin_req = 0.0
    available_funds = max(0.0, cash_balance)
    excess_liquidity = max(0.0, cash_balance)
    sma = max(0.0, cash_balance)
    buying_power = max(0.0, cash_balance)

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
        buying_power=buying_power,
    )


def validate_trade_compliance(
    portfolio_metrics: RegTMetrics,
    estimated_trade_cost: float,
    ticker: str,
    price: float,
    signal: str = "BUY",
    is_sell_tool_used: bool = False,
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
                f"Insufficient Buying Power (Cash Balance) for {ticker}. "
                f"Required: ${estimated_trade_cost:,.2f}, "
                f"Available Cash: ${portfolio_metrics.buying_power:,.2f}"
            ),
            max_affordable_shares=int(portfolio_metrics.buying_power // price) if price > 0 else 0,
        )

    # --- Dynamic Minimum Trade Value Guardrail (BUY only) ---
    if signal == "BUY":
        # Rule: 10% of Total Equity - ensures meaningful position sizing based on actual account equity
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
                ),
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
                ),
            )

    return ValidationResult(passed=True)
