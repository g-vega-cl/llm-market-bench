"""Unit tests for the update_earnings_alpha daily/batch pipeline script."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from scripts.update_earnings_alpha import process_ticker_earnings_alpha


@pytest.mark.asyncio
async def test_process_ticker_earnings_alpha_successful():
    """Verify single ticker processing generates valid snapshot dict."""
    ticker = "NVDA"
    sector = "XLK"
    as_of = date(2026, 8, 30)

    mock_earnings = [
        {
            "symbol": "NVDA",
            "date": "2026-08-26",
            "epsActual": 2.22,
            "epsEstimated": 2.09,
            "revenueActual": 96221000000,
            "revenueEstimated": 92270940000,
        },
        {
            "symbol": "NVDA",
            "date": "2026-05-22",
            "epsActual": 0.61,
            "epsEstimated": 0.56,
            "revenueActual": 26044000000,
            "revenueEstimated": 24646000000,
        },
        {
            "symbol": "NVDA",
            "date": "2026-02-21",
            "epsActual": 0.52,
            "epsEstimated": 0.46,
            "revenueActual": 22103000000,
            "revenueEstimated": 20621000000,
        },
        {
            "symbol": "NVDA",
            "date": "2025-11-21",
            "epsActual": 0.40,
            "epsEstimated": 0.34,
            "revenueActual": 18120000000,
            "revenueEstimated": 16182000000,
        },
        {
            "symbol": "NVDA",
            "date": "2025-08-23",
            "epsActual": 0.27,
            "epsEstimated": 0.21,
            "revenueActual": 13507000000,
            "revenueEstimated": 11224000000,
        },
    ]

    mock_metrics = [
        {
            "symbol": "NVDA",
            "incomeQuality": 1.05,
            "totalAssets": 100_000_000_000,
            "netIncome": 30_000_000_000,
            "operatingCashFlow": 32_000_000_000,
        }
    ]

    mock_grades = [
        {"symbol": "NVDA", "strongBuy": 2, "buy": 58, "hold": 16, "sell": 3, "strongSell": 0, "consensus": "Buy"}
    ]
    mock_targets = [
        {"symbol": "NVDA", "targetHigh": 515.0, "targetLow": 270.0, "targetConsensus": 345.21, "targetMedian": 322.5}
    ]
    mock_quote = {"price": 300.0}

    mock_fmp_client = AsyncMock()

    with patch("scripts.update_earnings_alpha.fetch_fmp_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [
            mock_earnings,  # stable/earnings
            mock_metrics,  # stable/key-metrics
            mock_grades,  # stable/grades-consensus
            mock_targets,  # stable/price-target-consensus
            [mock_quote],  # stable/quote
        ]

        snapshot = await process_ticker_earnings_alpha(
            client=mock_fmp_client,
            ticker=ticker,
            sector=sector,
            api_key="test-api-key",
            as_of_date=as_of,
        )

        assert snapshot is not None
        assert snapshot["ticker"] == "NVDA"
        assert snapshot["sector"] == "XLK"
        assert snapshot["report_date"] == "2026-08-26"
        assert snapshot["actual_eps"] == 2.22
        assert snapshot["estimated_eps"] == 2.09
        assert snapshot["revenue_surprise_pct"] == pytest.approx(4.28, rel=1e-1)
        assert snapshot["sue_score"] > 2.0
        assert snapshot["is_top_decile_sue"] is True
        assert snapshot["has_sufficient_earnings_history"] is True
        assert snapshot["analyst_consensus"] == "Buy"
        assert snapshot["analyst_coverage_count"] == 79


@pytest.mark.asyncio
async def test_process_ticker_handles_error_gracefully():
    """Verify single ticker error returns None and logs warning without throwing."""
    mock_fmp_client = AsyncMock()

    with patch("scripts.update_earnings_alpha.fetch_fmp_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = Exception("FMP Connection timeout")

        snapshot = await process_ticker_earnings_alpha(
            client=mock_fmp_client,
            ticker="BROKEN",
            sector="XLK",
            api_key="test-api-key",
            as_of_date=date(2026, 8, 30),
        )

        assert snapshot is None
