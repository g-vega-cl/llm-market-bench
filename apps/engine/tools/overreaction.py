"""Tool wrappers for market overreaction and structural repricing audit."""

from analytics.overreaction import audit_price_overreaction_report
from core.config import logger


async def execute_audit_price_overreaction_tool(ticker: str, lookback_days: int = 20) -> str:
    """Executes the audit_price_overreaction tool to evaluate statistical overreaction vs structural repricing."""
    ticker = (ticker or "SPY").strip().upper()
    try:
        report = await audit_price_overreaction_report(ticker=ticker, lookback_days=lookback_days)
        return report.get("markdown", f"Overreaction audit completed for {ticker}.")
    except Exception as e:
        logger.exception("Error executing audit_price_overreaction for %s: %s", ticker, e)
        return f"Error executing audit_price_overreaction for {ticker}: {str(e)}"
