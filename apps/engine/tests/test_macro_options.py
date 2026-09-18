"""Hermetic tests for macro options sentiment aggregation and rate-limit resilience."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analytics.macro_options import (
    fetch_macro_options_sentiment,
    format_macro_options_markdown_table,
    get_macro_options_summary,
)


def _make_sample_metrics(
    ticker: str,
    price: float = 500.0,
    pv_ratio: float = 1.25,
    poi_ratio: float = 1.35,
    atm_iv: float = 0.185,
    skew: float = 2.1,
    max_pain: float = 495.0,
    unusual_count: int = 0,
) -> dict:
    return {
        "ticker": ticker,
        "underlying_price": price,
        "as_of_timestamp": "2026-09-17T13:30:00Z",
        "session_status": "PRE_MARKET",
        "staleness_note": "Pre-market session. Data reflects prior closing settlement.",
        "put_call_volume_ratio": pv_ratio,
        "put_call_oi_ratio": poi_ratio,
        "atm_implied_volatility": atm_iv,
        "volatility_skew_25d_diff_pct": skew,
        "max_pain": max_pain,
        "unusual_activity": [{"ticker": f"O:{ticker}_{i}"} for i in range(unusual_count)],
    }


def test_format_macro_options_markdown_table_multiple_tickers():
    """Verify table formatting renders headers, rows, prices, and skew correctly."""
    metrics_list = [
        _make_sample_metrics(
            "SPY", price=560.10, pv_ratio=1.25, poi_ratio=1.45, atm_iv=0.142, skew=2.10, max_pain=555.0
        ),
        _make_sample_metrics(
            "QQQ", price=485.20, pv_ratio=0.95, poi_ratio=1.10, atm_iv=0.185, skew=1.80, max_pain=480.0
        ),
        _make_sample_metrics(
            "IWM", price=215.40, pv_ratio=1.60, poi_ratio=1.80, atm_iv=0.210, skew=3.40, max_pain=212.0
        ),
        _make_sample_metrics(
            "GLD",
            price=235.50,
            pv_ratio=0.70,
            poi_ratio=0.85,
            atm_iv=0.130,
            skew=-0.50,
            max_pain=235.0,
            unusual_count=2,
        ),
    ]

    table_md = format_macro_options_markdown_table(metrics_list)

    assert "### 📊 Macro Options Sentiment (SPY, QQQ, IWM, GLD)" in table_md
    assert "- **Market Session**: PRE_MARKET" in table_md
    assert "| Ticker | Spot Price | P/C Vol | P/C OI | ATM IV | 25Δ Skew | Max Pain | Outlier Flow |" in table_md
    assert "| SPY | $560.10 | 1.25 | 1.45 | 14.2% | +2.10% | $555.00 | None |" in table_md
    assert "| QQQ | $485.20 | 0.95 | 1.10 | 18.5% | +1.80% | $480.00 | None |" in table_md
    assert "| IWM | $215.40 | 1.60 | 1.80 | 21.0% | +3.40% | $212.00 | None |" in table_md
    assert "| GLD | $235.50 | 0.70 | 0.85 | 13.0% | -0.50% | $235.00 | 2 alerts |" in table_md


def test_format_macro_options_markdown_table_empty():
    """Verify empty input returns clean fallback string."""
    table_md = format_macro_options_markdown_table([])
    assert table_md == "No macro options data available."


@pytest.mark.asyncio
async def test_fetch_macro_options_sentiment_all_cached():
    """Verify hermetic DB cache hits return without invoking any external API calls."""
    mock_client = MagicMock()
    mock_client.get_options_snapshot = AsyncMock()

    # Pre-cache responses
    mock_client.get_options_snapshot.side_effect = [
        {"status": "OK", "source": "db_cache", "metrics": _make_sample_metrics("SPY")},
        {"status": "OK", "source": "db_cache", "metrics": _make_sample_metrics("QQQ")},
        {"status": "OK", "source": "db_cache", "metrics": _make_sample_metrics("IWM")},
        {"status": "OK", "source": "db_cache", "metrics": _make_sample_metrics("GLD")},
    ]

    with patch("analytics.macro_options.MassiveOptionsClient", return_value=mock_client):
        results = await fetch_macro_options_sentiment(tickers=["SPY", "QQQ", "IWM", "GLD"])

    assert len(results) == 4
    assert [r["ticker"] for r in results] == ["SPY", "QQQ", "IWM", "GLD"]
    assert mock_client.get_options_snapshot.call_count == 4


@pytest.mark.asyncio
async def test_fetch_macro_options_sentiment_error_isolation():
    """Verify that a single ticker error or rate-limit 429 does not fail remaining tickers."""
    mock_client = MagicMock()
    mock_client.get_options_snapshot = AsyncMock()

    # SPY and QQQ succeed, IWM raises an exception, GLD succeeds
    mock_client.get_options_snapshot.side_effect = [
        {"status": "OK", "source": "db_cache", "metrics": _make_sample_metrics("SPY")},
        {"status": "OK", "source": "api", "metrics": _make_sample_metrics("QQQ")},
        RuntimeError("429 Too Many Requests"),
        {"status": "OK", "source": "db_cache", "metrics": _make_sample_metrics("GLD")},
    ]

    with patch("analytics.macro_options.MassiveOptionsClient", return_value=mock_client):
        results = await fetch_macro_options_sentiment(tickers=["SPY", "QQQ", "IWM", "GLD"])

    assert len(results) == 3
    assert [r["ticker"] for r in results] == ["SPY", "QQQ", "GLD"]


@pytest.mark.asyncio
async def test_fetch_macro_options_sentiment_timeout_per_ticker():
    """Verify slow tickers time out quickly without blocking the entire pipeline."""
    mock_client = MagicMock()

    async def slow_fetch(ticker, **kwargs):
        if ticker == "GLD":
            await asyncio.sleep(0.3)
        return {"status": "OK", "metrics": _make_sample_metrics(ticker)}

    mock_client.get_options_snapshot = AsyncMock(side_effect=slow_fetch)

    with patch("analytics.macro_options.MassiveOptionsClient", return_value=mock_client):
        # Set a very low per-ticker timeout of 0.02s
        results = await fetch_macro_options_sentiment(
            tickers=["SPY", "GLD"],
            timeout_per_ticker=0.02,
        )

    # Only SPY should have completed within timeout
    assert len(results) == 1
    assert results[0]["ticker"] == "SPY"


@pytest.mark.asyncio
async def test_get_macro_options_summary_integration():
    """Verify get_macro_options_summary orchestrates fetch and markdown formatting."""
    mock_client = MagicMock()
    mock_client.get_options_snapshot = AsyncMock(
        side_effect=lambda ticker, **kwargs: {"status": "OK", "metrics": _make_sample_metrics(ticker, price=100.0)}
    )

    with patch("analytics.macro_options.MassiveOptionsClient", return_value=mock_client):
        summary = await get_macro_options_summary(tickers=["SPY", "QQQ"])

    assert "### 📊 Macro Options Sentiment (SPY, QQQ)" in summary
    assert "| SPY | $100.00 |" in summary
    assert "| QQQ | $100.00 |" in summary


@pytest.mark.asyncio
async def test_massive_options_client_bypasses_snapshot_on_free_tier():
    """Verify that once 403 is received on snapshot, subsequent calls bypass snapshot to save tokens."""
    from execution.providers.massive import MassiveOptionsClient

    # Reset class attribute
    MassiveOptionsClient._snapshot_supported = None

    client = MassiveOptionsClient(api_key="test_key")

    mock_resp_403 = MagicMock()
    mock_resp_403.status_code = 403

    with (
        patch("httpx.AsyncClient.get", return_value=mock_resp_403) as mock_get,
        patch.object(client, "_fetch_free_tier_contracts", new_callable=AsyncMock) as mock_free_tier,
    ):
        mock_free_tier.return_value = []

        # Call 1: should attempt snapshot, receive 403, set _snapshot_supported = False
        res1 = await client._fetch_from_api("SPY")
        assert res1["status"] == "OK"
        assert MassiveOptionsClient._snapshot_supported is False
        assert mock_get.call_count == 1

        # Call 2: should directly invoke _fetch_free_tier_contracts WITHOUT calling snapshot
        res2 = await client._fetch_from_api("QQQ")
        assert res2["status"] == "OK"
        assert mock_get.call_count == 1  # Still 1! No new snapshot request made
        assert mock_free_tier.call_count == 2
