"""LIN (Linde plc) Renko Hyper-Focused Flow Task.

Standalone single-stock execution pipeline for LIN, running post-consensus or on demand.
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from analysis.lin_agent import LinAgent, LinAgentContext
from analysis.renko import RenkoEngine
from execution.portfolio import Portfolio
from execution.providers.fmp import FMPProvider

logger = logging.getLogger("engine")

PORTFOLIO_OWNER_ID = "lin-renko-agent-deepseek-flash"


async def execute_lin_trade_decision(
    portfolio: Portfolio,
    decision: dict[str, Any],
    current_price: float,
    symbol: str = "LIN",
) -> UUID | None:
    """Executes trade on the isolated LIN portfolio based on LLM decision.

    Guarantees strict single-ticker isolation by rejecting any ticker other than 'LIN'.
    """
    if symbol.upper() != "LIN":
        raise ValueError(f"Strict single-stock isolation violation: {symbol} attempted on LIN portfolio (LIN only).")

    action = decision.get("decision", "HOLD_LONG").upper()
    confidence = float(decision.get("confidence", 0.0))
    target_pos_pct = float(decision.get("target_position_pct", 0.15))

    logger.info(
        f"Processing LIN trade decision: {action} (confidence: {confidence:.2f}, target_pct: {target_pos_pct:.1%}) @ ${current_price:.2f}"
    )

    if current_price <= 0:
        logger.warning(f"Invalid current price for LIN trade execution: ${current_price:.2f}")
        return None

    if action in ("BUY_LONG", "BUY"):
        # Position sizing: rebalance toward target_position_pct (capped at 25% max) based on total equity
        held_pos = portfolio.positions.get("LIN")
        held_qty = held_pos.quantity if held_pos else 0
        total_equity = portfolio.cash_balance + (held_qty * current_price)

        alloc_pct = min(target_pos_pct, 0.25)
        target_val = total_equity * alloc_pct
        target_shares = int(target_val / current_price)
        shares_to_buy = target_shares - held_qty

        if shares_to_buy <= 0:
            logger.info(
                f"LIN position already meets or exceeds target allocation ({held_qty}/{target_shares} shares, target_pct: {alloc_pct:.1%}). Holding."
            )
            return None

        # Ensure we do not exceed available cash balance
        max_affordable = int(portfolio.cash_balance / current_price)
        quantity = min(shares_to_buy, max_affordable)

        if quantity >= 1 and portfolio.cash_balance >= (quantity * current_price):
            logger.info(f"Executing BUY for {quantity} LIN shares (${quantity * current_price:,.2f})...")
            return await portfolio.execute_trade(
                ticker="LIN",
                quantity=quantity,
                price=current_price,
                signal="BUY",
                skip_alpaca_mirror=True,
            )
        else:
            logger.info(
                f"Insufficient cash for BUY {shares_to_buy} LIN shares @ ${current_price:.2f} (cash: ${portfolio.cash_balance:,.2f})."
            )
            return None

    elif action in ("EXIT_LONG", "SELL", "SHORT"):
        # Sell entire held position of LIN
        held_pos = portfolio.positions.get("LIN")
        if held_pos and held_pos.quantity > 0:
            qty_to_sell = held_pos.quantity
            logger.info(f"Executing SELL for {qty_to_sell} LIN shares @ ${current_price:.2f}...")
            return await portfolio.execute_trade(
                ticker="LIN",
                quantity=qty_to_sell,
                price=current_price,
                signal="SELL",
                skip_alpaca_mirror=True,
            )
        else:
            logger.info("No LIN position currently held to exit.")
            return None

    elif action in ("HOLD_LONG", "HOLD"):
        logger.info(f"Holding LIN position. Current held: {portfolio.positions.get('LIN', 'None')}")
        return None

    return None


async def run_lin_renko_flow() -> dict[str, Any]:
    """Executes the full LIN Renko hyper-focused trading flow."""
    logger.info(f"Starting LIN Renko Hyper-Focused Flow for {PORTFOLIO_OWNER_ID}...")

    fmp = FMPProvider()

    # 1. Initialize dedicated LIN portfolio ($10k starting balance)
    portfolio = Portfolio(owner_id=PORTFOLIO_OWNER_ID)
    await portfolio.initialize()

    # 2. Fetch LIN price history & update Renko state
    history = await fmp.get_history("LIN", days=730)
    prices = []
    timestamps = []
    if history:
        bars = sorted(history, key=lambda b: b.get("fetched_at", ""))
        prices = [float(b.get("price", 0.0)) for b in bars if b.get("price")]
        timestamps = [str(b.get("fetched_at", "")) for b in bars if b.get("fetched_at")]

    atr = RenkoEngine.calculate_atr(prices, period=14) if prices else 4.87
    engine = RenkoEngine(symbol="LIN", brick_size=atr)

    for p, ts in zip(prices, timestamps, strict=False):
        engine.process_price(p, timestamp=ts)

    # 3. Query specialized LIN fundamental metrics via FMP tools
    agent = LinAgent(model_name="deepseek-v4-flash")
    lin_metrics = await agent.fetch_lin_fundamentals(fmp)

    # 4. Construct context and execute analysis
    context = LinAgentContext(
        fab_gas_demand="HIGH",
        industrial_pmi=51.2,
        take_or_pay_backlog_billions=4.2,
        recent_news_summary=f"LIN ROIC: {lin_metrics.get('roic', 0.15) * 100:.1f}%, FCF Yield: {lin_metrics.get('freeCashFlowYield', 0.04) * 100:.1f}%, EPS Surprise: +{lin_metrics.get('earnings_surprise_pct', 2.0)}%.",
    )

    decision_res = await agent.analyze(engine.state, context)
    logger.info(
        f"LIN Renko Decision ({agent.model_name}): {decision_res['decision']} (Confidence: {decision_res['confidence']})"
    )

    # 5. Execute trade on isolated portfolio
    current_price = prices[-1] if prices else engine.state.last_brick_price
    if current_price <= 0:
        current_price = 490.61

    trade_id = await execute_lin_trade_decision(
        portfolio=portfolio,
        decision=decision_res,
        current_price=current_price,
        symbol="LIN",
    )

    return {
        "symbol": "LIN",
        "portfolio_owner": PORTFOLIO_OWNER_ID,
        "renko_state": {
            "trend": engine.state.trend_direction,
            "last_price": engine.state.last_brick_price,
            "reversal_threshold": engine.state.reversal_threshold,
            "consecutive_bricks": engine.state.consecutive_bricks,
            "atr_box_size": engine.state.brick_size,
        },
        "lin_metrics": lin_metrics,
        "decision": decision_res,
        "executed_trade_id": str(trade_id) if trade_id else None,
        "trade_executed": trade_id is not None,
    }


if __name__ == "__main__":
    asyncio.run(run_lin_renko_flow())
