"""LIN (Linde plc) Renko Hyper-Focused Flow Task.

Standalone single-stock execution pipeline for LIN, running post-consensus or on demand.
"""

import asyncio
import logging
from typing import Any

from analysis.lin_agent import LinAgent, LinAgentContext
from analysis.renko import RenkoEngine
from execution.portfolio import Portfolio
from execution.providers.fmp import FMPProvider

logger = logging.getLogger("engine")

PORTFOLIO_OWNER_ID = "lin-renko-agent-deepseek-flash"


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
    }


if __name__ == "__main__":
    asyncio.run(run_lin_renko_flow())
