"""Frontier Technology Supercycle Analytics and Guardrails.

Provides evaluation functions for:
1. 5-point supercycle gestation rubric (cost deflation, pure-play enabler,
   talent migration, regulatory catalyst, early commercial pilot).
2. Small-cap exchange and liquidity guardrails (NASDAQ/NYSE/AMEX, $100M+ cap, $1M+ daily vol).
3. Anti-overpaying and solvency checks (18+ months cash runway, anti-parabolic pump).
4. Fundamental thesis death evaluation.
"""

from dataclasses import dataclass
from typing import Any

ALLOWED_EXCHANGES = {
    "NASDAQ",
    "NYSE",
    "AMEX",
    "NEW YORK STOCK EXCHANGE",
    "NASDAQ GLOBAL SELECT",
    "NASDAQ CAPITAL MARKET",
    "NASDAQ GLOBAL MARKET",
    "NYSE AMERICAN",
}
MIN_MARKET_CAP = 100_000_000.0  # $100M
MIN_DAILY_DOLLAR_VOLUME = 1_000_000.0  # $1M
MIN_CASH_RUNWAY_MONTHS = 18.0
MAX_PRICE_TO_200D_MA = 1.50  # Max 150% of 200-day moving average


@dataclass
class SupercycleRubricCriteria:
    """The 5-point supercycle qualification criteria."""

    cost_deflation: bool = False
    pure_play_enabler: bool = False
    talent_migration: bool = False
    regulatory_catalyst: bool = False
    early_commercial_pilot: bool = False


def evaluate_supercycle_rubric(
    criteria: SupercycleRubricCriteria,
) -> tuple[bool, int, list[str]]:
    """Evaluates whether a frontier technology theme qualifies for supercycle tracking.

    Requires at least 3 of the 5 criteria to be satisfied.
    """
    satisfied: list[str] = []

    if criteria.cost_deflation:
        satisfied.append("cost_deflation")
    if criteria.pure_play_enabler:
        satisfied.append("pure_play_enabler")
    if criteria.talent_migration:
        satisfied.append("talent_migration")
    if criteria.regulatory_catalyst:
        satisfied.append("regulatory_catalyst")
    if criteria.early_commercial_pilot:
        satisfied.append("early_commercial_pilot")

    score = len(satisfied)
    passes = score >= 3
    return passes, score, satisfied


def evaluate_stock_guardrails(
    profile: dict[str, Any],
    quote: dict[str, Any],
    financials: dict[str, Any],
) -> tuple[bool, str]:
    """Evaluates whether a candidate small-cap stock satisfies liquidity and solvency guardrails.

    Rejects OTC/pink sheet stocks, illiquid micro-caps, parabolic hype runners,
    and companies with inadequate cash runway.
    """
    # 1. Exchange verification
    raw_exchange = str(profile.get("exchange") or "").strip().upper()
    if not any(allowed in raw_exchange for allowed in ALLOWED_EXCHANGES):
        return False, f"Rejected exchange: '{raw_exchange}'. Must trade on NASDAQ, NYSE, or AMEX."

    # 2. Market Cap verification
    market_cap = float(profile.get("mktCap") or profile.get("marketCap") or 0.0)
    if market_cap < MIN_MARKET_CAP:
        return False, f"Market cap ${market_cap:,.0f} is below the minimum ${MIN_MARKET_CAP:,.0f} threshold."

    # 3. Liquidity (Daily Dollar Volume)
    price = float(quote.get("price") or 0.0)
    avg_vol = float(quote.get("avgVolume") or quote.get("volume") or 0.0)
    dollar_volume = price * avg_vol
    if dollar_volume < MIN_DAILY_DOLLAR_VOLUME:
        return (
            False,
            f"Daily dollar volume ${dollar_volume:,.0f} is below the ${MIN_DAILY_DOLLAR_VOLUME:,.0f} requirement.",
        )

    # 4. Anti-Overpaying / Parabolic Pump filter
    ma_200 = float(quote.get("priceAvg200") or 0.0)
    if ma_200 > 0.0:
        ratio = price / ma_200
        if ratio > MAX_PRICE_TO_200D_MA:
            return (
                False,
                f"Parabolic pump rejected: Price is {ratio:.1%} of 200-day moving average (ceiling {MAX_PRICE_TO_200D_MA:.0%}).",
            )

    # 5. Solvency and Cash Runway
    is_profitable = bool(financials.get("is_profitable"))
    if not is_profitable:
        cash = float(financials.get("cash") or 0.0)
        opex = float(financials.get("operating_expenses") or financials.get("annual_burn") or 0.0)
        if opex > 0.0:
            runway_months = (cash / opex) * 12.0
            if runway_months < MIN_CASH_RUNWAY_MONTHS:
                return (
                    False,
                    f"Insufficient cash runway: {runway_months:.1f} months (minimum {MIN_CASH_RUNWAY_MONTHS:.0f} months required).",
                )
        elif cash <= 0.0:
            return False, "Insufficient cash reserves for pre-profitability operations."

    return True, "passed"


def evaluate_thesis_death(stock_status: dict[str, Any]) -> tuple[bool, str]:
    """Evaluates whether an existing holding has experienced fundamental thesis death.

    Venture power-law holdings are held through price drawdowns and volatility.
    They are only exited if the company faces bankruptcy, delisting, fraud,
    or the core scientific thesis is canceled or superseded.
    """
    if stock_status.get("is_bankrupt"):
        return True, "Company filed for bankruptcy or severe insolvency."
    if stock_status.get("is_delisted"):
        return True, "Stock was delisted from major US exchanges."
    if stock_status.get("thesis_canceled"):
        return True, "Underlying technological thesis canceled or proven physically non-viable."

    return False, "healthy"
