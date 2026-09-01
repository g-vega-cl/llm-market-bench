"""Tests for Massive.com (Polygon.io) options integration, rate-limiter, analytics deriver, and LLM tools."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.handlers.base import execute_tool
from execution.providers.massive import (
    MassiveOptionsClient,
    calculate_max_pain,
    calculate_options_sentiment,
    filter_option_chain,
)


@pytest.fixture
def sample_options_snapshot():
    """Deterministic sample snapshot data mimicking Massive /v3/snapshot/options/AAPL."""
    today = datetime.datetime.now(datetime.UTC).date()
    exp1 = (today + datetime.timedelta(days=14)).isoformat()
    exp2 = (today + datetime.timedelta(days=35)).isoformat()

    return {
        "status": "OK",
        "results": [
            # Exp 1 Calls
            {
                "details": {
                    "ticker": f"O:AAPL{exp1.replace('-', '')[2:]}C00180000",
                    "contract_type": "call",
                    "strike_price": 180.0,
                    "expiration_date": exp1,
                    "shares_per_contract": 100,
                },
                "day": {"volume": 5000, "close": 22.5, "change": 1.2, "change_percent": 5.6},
                "last_quote": {"bid": 22.3, "ask": 22.7},
                "greeks": {"delta": 0.85, "gamma": 0.02, "theta": -0.05, "vega": 0.12},
                "implied_volatility": 0.26,
                "open_interest": 2000,
            },
            {
                "details": {
                    "ticker": f"O:AAPL{exp1.replace('-', '')[2:]}C00200000",
                    "contract_type": "call",
                    "strike_price": 200.0,
                    "expiration_date": exp1,
                    "shares_per_contract": 100,
                },
                "day": {"volume": 12000, "close": 5.4, "change": 0.5, "change_percent": 10.2},
                "last_quote": {"bid": 5.3, "ask": 5.5},
                "greeks": {"delta": 0.50, "gamma": 0.04, "theta": -0.08, "vega": 0.22},
                "implied_volatility": 0.28,
                "open_interest": 15000,
            },
            {
                "details": {
                    "ticker": f"O:AAPL{exp1.replace('-', '')[2:]}C00220000",
                    "contract_type": "call",
                    "strike_price": 220.0,
                    "expiration_date": exp1,
                    "shares_per_contract": 100,
                },
                "day": {"volume": 8000, "close": 0.8, "change": 0.1, "change_percent": 14.3},
                "last_quote": {"bid": 0.75, "ask": 0.85},
                "greeks": {"delta": 0.18, "gamma": 0.02, "theta": -0.04, "vega": 0.11},
                "implied_volatility": 0.31,
                "open_interest": 1000,  # Unusual volume: 8000 > 3*1000
            },
            # Exp 1 Puts
            {
                "details": {
                    "ticker": f"O:AAPL{exp1.replace('-', '')[2:]}P00180000",
                    "contract_type": "put",
                    "strike_price": 180.0,
                    "expiration_date": exp1,
                    "shares_per_contract": 100,
                },
                "day": {"volume": 3000, "close": 0.9, "change": -0.2, "change_percent": -18.2},
                "last_quote": {"bid": 0.85, "ask": 0.95},
                "greeks": {"delta": -0.15, "gamma": 0.02, "theta": -0.03, "vega": 0.10},
                "implied_volatility": 0.33,
                "open_interest": 5000,
            },
            {
                "details": {
                    "ticker": f"O:AAPL{exp1.replace('-', '')[2:]}P00200000",
                    "contract_type": "put",
                    "strike_price": 200.0,
                    "expiration_date": exp1,
                    "shares_per_contract": 100,
                },
                "day": {"volume": 6000, "close": 4.8, "change": -0.6, "change_percent": -11.1},
                "last_quote": {"bid": 4.7, "ask": 4.9},
                "greeks": {"delta": -0.48, "gamma": 0.04, "theta": -0.07, "vega": 0.21},
                "implied_volatility": 0.29,
                "open_interest": 8000,
            },
            # Exp 2 Calls & Puts
            {
                "details": {
                    "ticker": f"O:AAPL{exp2.replace('-', '')[2:]}C00200000",
                    "contract_type": "call",
                    "strike_price": 200.0,
                    "expiration_date": exp2,
                    "shares_per_contract": 100,
                },
                "day": {"volume": 4000, "close": 7.2, "change": 0.4, "change_percent": 5.9},
                "last_quote": {"bid": 7.1, "ask": 7.3},
                "greeks": {"delta": 0.52, "gamma": 0.03, "theta": -0.06, "vega": 0.28},
                "implied_volatility": 0.27,
                "open_interest": 9000,
            },
        ],
    }


def test_calculate_max_pain(sample_options_snapshot):
    """Test max pain calculation identifies the strike with minimum total loss."""
    contracts = sample_options_snapshot["results"]
    max_pain = calculate_max_pain(contracts)
    assert max_pain is not None
    assert isinstance(max_pain, float | int)
    assert max_pain in [180.0, 200.0, 220.0]


def test_calculate_options_sentiment(sample_options_snapshot):
    """Test calculation of Put/Call ratios, ATM IV, Skew, and unusual activity."""
    sentiment = calculate_options_sentiment("AAPL", sample_options_snapshot["results"], current_price=200.0)

    assert sentiment["ticker"] == "AAPL"
    assert sentiment["put_call_volume_ratio"] == pytest.approx((3000 + 6000) / (5000 + 12000 + 8000 + 4000), 0.01)
    assert sentiment["put_call_oi_ratio"] == pytest.approx((5000 + 8000) / (2000 + 15000 + 1000 + 9000), 0.01)
    assert sentiment["atm_implied_volatility"] is not None
    assert sentiment["atm_implied_volatility"] == pytest.approx(0.28, 0.02)
    assert sentiment["max_pain"] is not None
    assert len(sentiment["unusual_activity"]) >= 1
    assert any(u["strike"] == 220.0 for u in sentiment["unusual_activity"])


def test_filter_option_chain(sample_options_snapshot):
    """Test filtering options chain by strike range, contract type, and expiration."""
    contracts = sample_options_snapshot["results"]

    # Filter calls only within 5% of 200
    filtered = filter_option_chain(
        contracts=contracts,
        current_price=200.0,
        strike_range_pct=5.0,
        contract_type="call",
    )
    for c in filtered:
        assert c["contract_type"] == "call"
        assert 190.0 <= c["strike"] <= 210.0


@pytest.mark.asyncio
async def test_massive_client_cache_and_fetch(sample_options_snapshot):
    """Test MassiveOptionsClient fetches from Supabase cache if fresh or from API if missing."""
    client = MassiveOptionsClient(api_key="test_key")

    mock_sb = MagicMock()
    # Mock Supabase table query returning no cached row
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with (
        patch.object(client, "_get_supabase", return_value=mock_sb),
        patch.object(client, "_fetch_from_api", new_callable=AsyncMock) as mock_fetch,
    ):
        mock_fetch.return_value = sample_options_snapshot

        data = await client.get_options_snapshot("AAPL", current_price=200.0)
        assert data is not None
        assert "metrics" in data
        assert mock_fetch.called


@pytest.mark.asyncio
async def test_execute_tools_integration(sample_options_snapshot):
    """Test tool dispatcher calls get_options_sentiment and get_option_chain cleanly."""
    mock_quote = MagicMock()
    mock_quote.exists = True
    mock_quote.price = 200.0

    with (
        patch(
            "execution.providers.massive.MassiveOptionsClient.get_options_snapshot",
            new_callable=AsyncMock,
        ) as mock_snapshot,
        patch(
            "execution.market_data.MarketDataManager.get_quote",
            new_callable=AsyncMock,
            return_value=mock_quote,
        ),
    ):
        mock_snapshot.return_value = {
            "status": "OK",
            "metrics": calculate_options_sentiment("AAPL", sample_options_snapshot["results"], current_price=200.0),
            "contracts": sample_options_snapshot["results"],
        }

        # 1. Test get_options_sentiment tool execution
        res_sentiment = await execute_tool("get_options_sentiment", {"ticker": "AAPL"}, model_name="test_model")
        assert "Options Sentiment Snapshot: AAPL" in res_sentiment
        assert "Put/Call Volume Ratio" in res_sentiment
        assert "Max Pain" in res_sentiment

        # 2. Test get_option_chain tool execution
        res_chain = await execute_tool(
            "get_option_chain",
            {"ticker": "AAPL", "contract_type": "call", "strike_range_pct": 10.0},
            model_name="test_model",
        )
        assert "Option Chain for AAPL" in res_chain
        assert "Strike" in res_chain
        assert "Delta" in res_chain


@pytest.mark.asyncio
async def test_token_bucket_limiter():
    """Test AsyncTokenBucketLimiter acquires tokens accurately."""
    from execution.providers.massive import AsyncTokenBucketLimiter

    limiter = AsyncTokenBucketLimiter(max_tokens=2.0, refill_period_seconds=1.0)
    # First 2 tokens should acquire immediately
    await limiter.acquire()
    await limiter.acquire()
    assert limiter.tokens < 1.0


@pytest.mark.asyncio
async def test_options_tools_empty_or_error_handling():
    """Test tools gracefully handle missing data or non-existent tickers."""
    with patch(
        "execution.providers.massive.MassiveOptionsClient.get_options_snapshot",
        new_callable=AsyncMock,
    ) as mock_snapshot:
        mock_snapshot.return_value = {"status": "NO_DATA", "metrics": {}, "contracts": []}

        res_sentiment = await execute_tool("get_options_sentiment", {"ticker": "XYZ"}, model_name="test_model")
        assert "No options data available for ticker 'XYZ'" in res_sentiment

        res_chain = await execute_tool("get_option_chain", {"ticker": "XYZ"}, model_name="test_model")
        assert "No options chain data available for ticker 'XYZ'" in res_chain
