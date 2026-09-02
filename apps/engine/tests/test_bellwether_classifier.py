"""Unit tests for the dynamic sector bellwether classifier and diffusion radar."""

from datetime import date

import pytest

from analytics.bellwether_classifier import (
    BellwetherClassification,
    calculate_sector_margin_surprise_delta,
    classify_sector_constituents,
    evaluate_bellwether_signals,
)


def test_dynamic_bellwether_identification():
    """Verify top 5 market cap constituents reporting in first 14 days are classified as early bellwethers."""
    cycle_start = date(2026, 8, 1)

    constituents = [
        # Rank 1, reports Day 4 -> Bellwether
        {"ticker": "NVDA", "sector": "XLK", "market_cap": 3_000_000_000_000, "report_date": date(2026, 8, 5)},
        # Rank 2, reports Day 8 -> Bellwether
        {"ticker": "MSFT", "sector": "XLK", "market_cap": 2_800_000_000_000, "report_date": date(2026, 8, 9)},
        # Rank 3, reports Day 24 -> Downstream Peer (reports after day 14)
        {"ticker": "AAPL", "sector": "XLK", "market_cap": 2_500_000_000_000, "report_date": date(2026, 8, 25)},
        # Rank 4, reports Day 20 -> Downstream Peer
        {"ticker": "AVGO", "sector": "XLK", "market_cap": 800_000_000_000, "report_date": date(2026, 8, 21)},
        # Rank 5, reports Day 18 -> Downstream Peer
        {"ticker": "ORCL", "sector": "XLK", "market_cap": 400_000_000_000, "report_date": date(2026, 8, 19)},
        # Rank 6, reports Day 3 -> Downstream Peer (outside top 5 market cap rank)
        {"ticker": "SNPS", "sector": "XLK", "market_cap": 80_000_000_000, "report_date": date(2026, 8, 4)},
    ]

    results = classify_sector_constituents(
        constituents=constituents,
        cycle_start_date=cycle_start,
        max_bellwether_rank=5,
        early_cycle_days=14,
    )

    by_ticker = {r.ticker: r for r in results}

    assert by_ticker["NVDA"].classification == "EARLY_BELLWETHER"
    assert by_ticker["NVDA"].market_cap_rank == 1
    assert by_ticker["NVDA"].cycle_report_day == 4

    assert by_ticker["MSFT"].classification == "EARLY_BELLWETHER"
    assert by_ticker["MSFT"].market_cap_rank == 2
    assert by_ticker["MSFT"].cycle_report_day == 8

    assert by_ticker["AAPL"].classification == "DOWNSTREAM_PEER"
    assert by_ticker["AAPL"].market_cap_rank == 3
    assert by_ticker["AAPL"].cycle_report_day == 24

    assert by_ticker["SNPS"].classification == "DOWNSTREAM_PEER"
    assert by_ticker["SNPS"].market_cap_rank == 6


def test_bellwether_signal_recency_window():
    """Verify bellwether report is active within 14 days and expires after 14 days."""
    as_of_date = date(2026, 8, 20)

    classifications = [
        # Reported 6 days ago -> Active Signal
        BellwetherClassification(
            ticker="NVDA",
            sector="XLK",
            market_cap=3e12,
            market_cap_rank=1,
            report_date=date(2026, 8, 14),
            cycle_report_day=5,
            classification="EARLY_BELLWETHER",
        ),
        # Reported 20 days ago -> Expired Signal
        BellwetherClassification(
            ticker="TSM",
            sector="XLK",
            market_cap=8e11,
            market_cap_rank=2,
            report_date=date(2026, 7, 31),
            cycle_report_day=1,
            classification="EARLY_BELLWETHER",
        ),
        # Has not reported yet -> Inactive
        BellwetherClassification(
            ticker="MSFT",
            sector="XLK",
            market_cap=2.8e12,
            market_cap_rank=3,
            report_date=date(2026, 8, 28),
            cycle_report_day=19,
            classification="EARLY_BELLWETHER",
        ),
    ]

    signals = evaluate_bellwether_signals(classifications, as_of_date=as_of_date, max_signal_age_days=14)
    signals_by_ticker = {s.ticker: s for s in signals}

    assert signals_by_ticker["NVDA"].is_reported is True
    assert signals_by_ticker["NVDA"].is_active_bellwether_signal is True

    assert signals_by_ticker["TSM"].is_reported is True
    assert signals_by_ticker["TSM"].is_active_bellwether_signal is False

    assert signals_by_ticker["MSFT"].is_reported is False
    assert signals_by_ticker["MSFT"].is_active_bellwether_signal is False


def test_sector_margin_surprise_delta():
    """Verify calculation of cap-weighted average margin surprise across reported bellwethers."""
    reported_bellwethers = [
        {"ticker": "NVDA", "market_cap": 3_000_000_000_000, "operating_margin_surprise": 2.5},
        {"ticker": "MSFT", "market_cap": 1_000_000_000_000, "operating_margin_surprise": -0.5},
    ]

    # Total market cap = 4T
    # Weighted avg = (3T * 2.5 + 1T * -0.5) / 4T = (7.5 - 0.5) / 4 = 7.0 / 4 = 1.75%
    avg_delta = calculate_sector_margin_surprise_delta(reported_bellwethers)
    assert avg_delta == pytest.approx(1.75, rel=1e-3)
