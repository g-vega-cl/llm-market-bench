"""Hermetic unit tests for analytics.market_reference module."""

import pytest

from analytics.market_reference import (
    compute_multi_horizon_reference,
    extract_mentioned_single_stocks,
    format_reference_table,
)


def _generate_synthetic_history(n_bars: int = 252, base_price: float = 100.0, step: float = 0.5) -> list[dict]:
    """Generates synthetic price bars sorted newest to oldest (standard MarketDataManager order)."""
    # chronological: day 0 has base_price, day 1 has base_price + step...
    # history[0] is latest (day n_bars - 1)
    bars = []
    for i in range(n_bars - 1, -1, -1):
        price = base_price + (i * step)
        # Format date as YYYY-MM-DD
        day = (i % 28) + 1
        month = ((i // 28) % 12) + 1
        year = 2025 + (i // 336)
        date_str = f"{year:04d}-{month:02d}-{day:02d}T00:00:00+00:00"
        bars.append({"price": price, "fetched_at": date_str})
    return bars


class TestMarketReferenceCalculations:
    """Validates multi-horizon quantitative metrics, SMAs, percentiles, and volatility."""

    def test_insufficient_history_returns_none(self):
        assert compute_multi_horizon_reference("XYZ", []) is None
        assert compute_multi_horizon_reference("XYZ", [{"price": 100.0}]) is None
        assert compute_multi_horizon_reference("XYZ", [{"price": None}] * 10) is None

    def test_full_history_multi_horizon_metrics(self):
        history = _generate_synthetic_history(n_bars=252, base_price=100.0, step=0.5)
        # Latest price = 100 + 251 * 0.5 = 225.5
        # Min price = 100.0, Max price = 225.5
        profile = compute_multi_horizon_reference("TEST", history, live_price=225.5)

        assert profile is not None
        assert profile.ticker == "TEST"
        assert profile.current_price == 225.5
        assert profile.bars_used == 252

        # 52W range: min=100.0, max=225.5, percentile=100.0%
        assert profile.min_52w == 100.0
        assert profile.max_52w == 225.5
        assert pytest.approx(profile.pct_52w, 0.1) == 100.0
        assert profile.regime_tag == "Near 52W High (Top Decile)"
        assert profile.z_score_52w is not None
        assert profile.z_score_52w > 1.5

        # SMAs
        assert profile.sma_20 is not None
        assert profile.sma_50 is not None
        assert profile.sma_200 is not None
        assert profile.dist_sma_20 is not None
        assert profile.dist_sma_20 > 0  # Trading above 20-DMA

        # Volatility
        assert profile.vol_20d is not None
        assert profile.vol_1y is not None
        assert "Normal" in profile.vol_regime or "Compressed" in profile.vol_regime

    def test_point_in_time_zero_lookahead_filtering(self):
        # 10 bars from 2026-10-01 to 2026-10-10
        bars = [
            {"price": 110.0, "fetched_at": "2026-10-10T00:00:00+00:00"},
            {"price": 109.0, "fetched_at": "2026-10-09T00:00:00+00:00"},
            {"price": 108.0, "fetched_at": "2026-10-08T00:00:00+00:00"},
            {"price": 107.0, "fetched_at": "2026-10-07T00:00:00+00:00"},
            {"price": 106.0, "fetched_at": "2026-10-06T00:00:00+00:00"},
            {"price": 105.0, "fetched_at": "2026-10-05T00:00:00+00:00"},
            {"price": 104.0, "fetched_at": "2026-10-04T00:00:00+00:00"},
        ]
        # Target date is 2026-10-08 -> bars with date >= 2026-10-08 must be excluded
        profile = compute_multi_horizon_reference("TEST", bars, target_date="2026-10-08")
        assert profile is not None
        # Latest bar used should be 2026-10-07 ($107.0)
        assert profile.current_price == 107.0
        assert profile.bars_used == 4  # 10-07, 10-06, 10-05, 10-04

    def test_oversold_bottom_decile_classification(self):
        # Monotonically declining series
        history = _generate_synthetic_history(n_bars=252, base_price=200.0, step=-0.5)
        # Latest price = 200 - 251*0.5 = 74.5 (lowest)
        profile = compute_multi_horizon_reference("FALL", history, live_price=74.5)
        assert profile is not None
        assert profile.pct_52w is not None
        assert profile.pct_52w <= 10.0
        assert profile.regime_tag == "Near 52W Low (Bottom Decile)"
        assert profile.z_score_52w is not None
        assert profile.z_score_52w < -1.5

    def test_volatility_expansion_classification(self):
        # 250 flat bars, then 10 extremely volatile bars
        bars = []
        for i in range(10):
            # Alternating wild swings: 100 -> 150 -> 80
            px = 150.0 if i % 2 == 0 else 80.0
            bars.append({"price": px, "fetched_at": f"2026-10-{28 - i:02d}T00:00:00+00:00"})
        for _ in range(240):
            bars.append({"price": 100.0, "fetched_at": "2026-09-01T00:00:00+00:00"})

        profile = compute_multi_horizon_reference("VOL", bars, live_price=150.0)
        assert profile is not None
        assert "Expanding" in profile.vol_regime


class TestFormatAndExtraction:
    """Validates markdown table formatting and single stock extraction."""

    def test_format_reference_table(self):
        history = _generate_synthetic_history(n_bars=60, base_price=50.0, step=0.2)
        p1 = compute_multi_horizon_reference("UUP", history, live_price=62.0)
        p2 = compute_multi_horizon_reference("SPY", history, live_price=62.0)
        assert p1 is not None and p2 is not None

        table_md = format_reference_table([p1, p2])
        assert "| Asset |" in table_md
        assert "| **UUP** |" in table_md
        assert "| **SPY** |" in table_md
        assert "52W Range" in table_md

    def test_extract_mentioned_single_stocks(self):
        chunks = [
            {
                "subject": "Market Wrap: Boeing ($BA) cuts production, Apple (AAPL) launches Duo",
                "content": "Boeing ($BA) fell 10%. Meanwhile Nvidia ($NVDA) and AMD ($AMD) rose. Note the CEO said GDP is up.",
            },
            {
                "subject": "Tech Radar",
                "content": "Broadcom ($AVGO) and $NVDA leading semis. Also watching $TSLA and $BA again.",
            },
        ]
        extracted = extract_mentioned_single_stocks(chunks, max_tickers=4)
        # Should extract BA, NVDA, AAPL, AMD, AVGO, TSLA and order by frequency
        # BA and NVDA are mentioned twice
        assert "BA" in extracted
        assert "NVDA" in extracted
        assert len(extracted) <= 4
        # False positives like CEO, GDP, etc. must not be extracted
        assert "CEO" not in extracted
        assert "GDP" not in extracted
        # Macro proxies must not be extracted as single stocks
        assert "SPY" not in extracted


@pytest.mark.asyncio
class TestNewsletterReferenceContextAsync:
    """Hermetic async tests for get_newsletter_reference_context."""

    async def test_get_newsletter_reference_context_mocked(self):
        from unittest.mock import AsyncMock

        from analytics.market_reference import get_newsletter_reference_context

        history = _generate_synthetic_history(n_bars=60, base_price=50.0, step=0.2)
        mock_mdm = AsyncMock()
        mock_mdm.get_premarket_quote.return_value = {"price": 62.0, "change_pct": 0.5}
        mock_mdm.get_history.return_value = history

        chunks = [{"subject": "Market Focus: $NVDA leaps", "content": "Spotlight on ($NVDA) and earnings."}]
        context = await get_newsletter_reference_context(chunks, mdm=mock_mdm, macro_tickers=["UUP", "SPY"])

        assert "### 📊 Multi-Horizon Reference & Statistical Regime Matrix" in context
        assert "| **UUP** |" in context
        assert "| **SPY** |" in context
        assert "| **NVDA** |" in context
        assert "Key Reference & Statistical Highlights" in context
