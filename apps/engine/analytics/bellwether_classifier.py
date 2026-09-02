"""Dynamic sector bellwether classification and earnings diffusion radar."""

from dataclasses import dataclass
from datetime import date


@dataclass
class BellwetherClassification:
    """Classification record for a sector constituent."""

    ticker: str
    sector: str
    market_cap: float
    market_cap_rank: int
    report_date: date | None
    cycle_report_day: int
    classification: str  # 'EARLY_BELLWETHER' or 'DOWNSTREAM_PEER'


@dataclass
class BellwetherSignal:
    """Evaluated diffusion signal for a sector bellwether."""

    ticker: str
    sector: str
    market_cap: float
    market_cap_rank: int
    report_date: date | None
    cycle_report_day: int
    classification: str
    is_reported: bool
    is_active_bellwether_signal: bool


def classify_sector_constituents(
    constituents: list[dict],
    cycle_start_date: date,
    max_bellwether_rank: int = 5,
    early_cycle_days: int = 14,
) -> list[BellwetherClassification]:
    """Classify sector constituents into early bellwethers vs downstream peers.

    Rules:
    - Top `max_bellwether_rank` by market cap in the sector.
    - Reports within `early_cycle_days` from the start of the quarterly reporting window.
    """
    if not constituents:
        return []

    # Sort constituents by market cap descending
    sorted_constituents = sorted(constituents, key=lambda c: float(c.get("market_cap", 0.0)), reverse=True)

    results: list[BellwetherClassification] = []

    for rank, item in enumerate(sorted_constituents, start=1):
        ticker = item["ticker"]
        sector = item.get("sector", "UNKNOWN")
        market_cap = float(item.get("market_cap", 0.0))
        report_date = item.get("report_date")

        cycle_day = 999
        if report_date and isinstance(report_date, date):
            delta = (report_date - cycle_start_date).days
            cycle_day = max(1, delta)

        is_early_reporter = cycle_day <= early_cycle_days
        is_top_rank = rank <= max_bellwether_rank

        classification = "EARLY_BELLWETHER" if is_top_rank and is_early_reporter else "DOWNSTREAM_PEER"

        results.append(
            BellwetherClassification(
                ticker=ticker,
                sector=sector,
                market_cap=market_cap,
                market_cap_rank=rank,
                report_date=report_date,
                cycle_report_day=cycle_day,
                classification=classification,
            )
        )

    return results


def evaluate_bellwether_signals(
    classifications: list[BellwetherClassification],
    as_of_date: date,
    max_signal_age_days: int = 14,
) -> list[BellwetherSignal]:
    """Evaluate whether early bellwethers have reported and are within the active diffusion window."""
    signals: list[BellwetherSignal] = []

    for c in classifications:
        is_reported = False
        is_active = False

        if c.report_date:
            days_since_report = (as_of_date - c.report_date).days
            if days_since_report >= 0:
                is_reported = True
                if c.classification == "EARLY_BELLWETHER" and days_since_report <= max_signal_age_days:
                    is_active = True

        signals.append(
            BellwetherSignal(
                ticker=c.ticker,
                sector=c.sector,
                market_cap=c.market_cap,
                market_cap_rank=c.market_cap_rank,
                report_date=c.report_date,
                cycle_report_day=c.cycle_report_day,
                classification=c.classification,
                is_reported=is_reported,
                is_active_bellwether_signal=is_active,
            )
        )

    return signals


def calculate_sector_margin_surprise_delta(reported_bellwethers: list[dict]) -> float:
    """Calculate cap-weighted average operating margin surprise across reported bellwethers."""
    if not reported_bellwethers:
        return 0.0

    total_weight = sum(float(b.get("market_cap", 0.0)) for b in reported_bellwethers)
    if total_weight <= 0.0:
        return float(
            sum(float(b.get("operating_margin_surprise", 0.0)) for b in reported_bellwethers)
            / len(reported_bellwethers)
        )

    weighted_sum = sum(
        float(b.get("market_cap", 0.0)) * float(b.get("operating_margin_surprise", 0.0)) for b in reported_bellwethers
    )

    return float(weighted_sum / total_weight)
