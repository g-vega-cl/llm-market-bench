"""Hermetic unit tests for thematic_beneficiaries module.

Zero external network calls allowed. All external APIs (FMP, Massive, Supabase)
are strictly mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from analysis.thematic_beneficiaries import (
    calculate_returns,
    compute_pair_metrics,
    compute_thematic_beneficiaries,
    fetch_screener_candidates,
    format_thematic_beneficiaries_markdown,
)


def test_calculate_returns():
    """Verify returns calculation handles normal and edge cases."""
    assert len(calculate_returns([])) == 0
    assert len(calculate_returns([100.0])) == 0

    prices = [100.0, 105.0, 102.9]
    returns = calculate_returns(prices)
    assert len(returns) == 2
    assert pytest.approx(returns[0], 0.0001) == 0.05
    assert pytest.approx(returns[1], 0.0001) == -0.02


def test_compute_pair_metrics_perfect_correlation():
    """Verify metrics for perfectly correlated series."""
    anchor_ret = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02])
    candidate_ret = anchor_ret * 2.0  # beta should be 2.0, correlation 1.0

    metrics = compute_pair_metrics(anchor_ret, candidate_ret)
    assert pytest.approx(metrics["correlation"], 0.001) == 1.0
    assert pytest.approx(metrics["beta"], 0.001) == 2.0
    assert metrics["sample_count"] == 12


def test_compute_pair_metrics_zero_variance():
    """Verify safe fallback when variance is zero."""
    anchor_ret = np.array([0.0] * 15)
    candidate_ret = np.array([0.01] * 15)

    metrics = compute_pair_metrics(anchor_ret, candidate_ret)
    assert metrics["correlation"] == 0.0
    assert metrics["beta"] == 0.0
    assert metrics["sample_count"] == 15


def test_compute_pair_metrics_short_series():
    """Verify safe fallback for series shorter than 5 days."""
    anchor_ret = np.array([0.01, 0.02])
    candidate_ret = np.array([0.01, 0.02])

    metrics = compute_pair_metrics(anchor_ret, candidate_ret)
    assert metrics["correlation"] == 0.0
    assert metrics["beta"] == 0.0
    assert metrics["sample_count"] == 2


@pytest.mark.asyncio
async def test_fetch_screener_candidates_mocked():
    """Verify candidate screening with mocked HTTP response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "symbol": "VST",
            "companyName": "Vistra Corp",
            "industry": "Regulated Electric",
            "sector": "Utilities",
            "marketCap": 50000000000,
        },
        {
            "symbol": "CEG",
            "companyName": "Constellation Energy",
            "industry": "Regulated Electric",
            "sector": "Utilities",
            "marketCap": 60000000000,
        },
    ]

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    results = await fetch_screener_candidates(
        industries=["Regulated Electric"],
        fmp_api_key="test_key",
        http_client=mock_client,
    )

    assert len(results) == 2
    assert results[0]["symbol"] == "VST"
    assert results[1]["symbol"] == "CEG"


@pytest.mark.asyncio
async def test_compute_thematic_beneficiaries_custom_tickers():
    """Verify end-to-end thematic beneficiaries ranking with custom candidate tickers."""
    # Generate deterministic fluctuating price trends (25 days)
    base_returns = [0.02, -0.01, 0.03, -0.015, 0.025, -0.02, 0.01, -0.005, 0.03, -0.01] * 3
    base_returns = base_returns[:24]

    anchor_prices = [100.0]
    vst_prices = [50.0]
    mu_prices = [80.0]

    for r in base_returns:
        anchor_prices.append(anchor_prices[-1] * (1.0 + r))
        vst_prices.append(vst_prices[-1] * (1.0 + r * 1.5))  # Highly correlated, higher beta
        mu_prices.append(mu_prices[-1] * (1.0 - r * 0.8))  # Inversely correlated

    async def mock_get_history(ticker, days=60, force_refresh=False):
        if ticker == "NVDA":
            return [{"price": p} for p in reversed(anchor_prices)]
        elif ticker == "VST":
            return [{"price": p} for p in reversed(vst_prices)]
        elif ticker == "MU":
            return [{"price": p} for p in reversed(mu_prices)]
        return []

    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(side_effect=mock_get_history)

    mock_options_client = MagicMock()
    mock_options_client.get_options_snapshot = AsyncMock(
        return_value={
            "status": "OK",
            "contracts": [
                {
                    "details": {"contract_type": "call", "strike_price": 100.0, "expiration_date": "2026-10-01"},
                    "day": {"volume": 1000},
                    "implied_volatility": 0.25,
                },
                {
                    "details": {"contract_type": "put", "strike_price": 100.0, "expiration_date": "2026-10-01"},
                    "day": {"volume": 100},
                    "implied_volatility": 0.26,
                },
            ],
        }
    )

    result = await compute_thematic_beneficiaries(
        anchor_ticker="NVDA",
        theme="AI Data Center Power",
        candidate_tickers=["VST", "MU"],
        lookback_days=25,
        options_top_n=1,
        mdm=mock_mdm,
        options_client=mock_options_client,
    )

    assert result["anchor_ticker"] == "NVDA"
    assert result["theme"] == "AI Data Center Power"
    assert len(result["beneficiaries"]) == 2

    # VST should rank higher due to positive correlation & beta
    top_pick = result["beneficiaries"][0]
    assert top_pick["symbol"] == "VST"
    assert top_pick["correlation"] > 0.9
    assert top_pick["beta"] > 1.0
    # Options data should be enriched on top 1 pick
    assert top_pick.get("options_sentiment") is not None
    assert top_pick["options_sentiment"]["put_call_volume_ratio"] == 0.1

    # Format markdown
    md = format_thematic_beneficiaries_markdown(result)
    assert "NVDA" in md
    assert "VST" in md
    assert "AI Data Center Power" in md


def test_analyze_thematic_beneficiaries_in_canonical_registry():
    """Verify tool is declared in CANONICAL_TOOLS_REGISTRY."""
    from core.llm.tools import CANONICAL_TOOLS_REGISTRY

    assert "analyze_thematic_beneficiaries" in CANONICAL_TOOLS_REGISTRY
    tool = CANONICAL_TOOLS_REGISTRY["analyze_thematic_beneficiaries"]
    assert tool["function"]["name"] == "analyze_thematic_beneficiaries"
    assert "anchor_ticker" in tool["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_execute_analyze_thematic_beneficiaries_tool():
    """Verify tool execution wrapper dispatches and formats output."""
    with patch(
        "analysis.thematic_beneficiaries.compute_thematic_beneficiaries",
        new_callable=AsyncMock,
        return_value={
            "anchor_ticker": "LLY",
            "theme": "GLP-1 Apparel",
            "beneficiaries": [
                {
                    "symbol": "LULU",
                    "industry": "Apparel Retail",
                    "market_cap": 35000000000,
                    "correlation": 0.45,
                    "beta": 0.65,
                    "momentum_20d": 0.08,
                    "score": 0.35,
                }
            ],
            "summary": "Analyzed 1 related beneficiary for LLY.",
        },
    ):
        from core.llm.tools import execute_tool

        output = await execute_tool(
            "analyze_thematic_beneficiaries",
            {"anchor_ticker": "LLY", "theme": "GLP-1 Apparel", "candidate_tickers": ["LULU"]},
        )
        assert "Thematic Beneficiaries Analysis: LLY" in output
        assert "LULU" in output
        assert "GLP-1 Apparel" in output


def test_calculate_fundamental_transmission_positive():
    """Verify transmission metrics when anchor capex and candidate revenue both surge."""
    from analysis.thematic_beneficiaries import calculate_fundamental_transmission

    anchor_cf = [
        {"date": "2026-07-26", "capitalExpenditure": -2677000000},
        {"date": "2026-04-26", "capitalExpenditure": -1757000000},
    ]
    candidate_inc = [
        {"date": "2026-06-30", "revenue": 3274300000, "operatingIncome": 637900000},
        {"date": "2026-03-31", "revenue": 2649500000, "operatingIncome": 440100000},
    ]

    metrics = calculate_fundamental_transmission(anchor_cf, candidate_inc)
    assert pytest.approx(metrics["anchor_capex_growth_qoq"], 0.001) == 0.524
    assert pytest.approx(metrics["candidate_rev_growth_qoq"], 0.001) == 0.236
    assert pytest.approx(metrics["candidate_op_inc_growth_qoq"], 0.001) == 0.449
    assert metrics["transmission_score"] > 0.0


def test_calculate_fundamental_transmission_edge_cases():
    """Verify safe fallback for empty or zero financial statements."""
    from analysis.thematic_beneficiaries import calculate_fundamental_transmission

    metrics = calculate_fundamental_transmission([], [])
    assert metrics["anchor_capex_growth_qoq"] is None
    assert metrics["candidate_rev_growth_qoq"] is None
    assert metrics["transmission_score"] == 0.0


@pytest.mark.asyncio
async def test_enrich_institutional_support():
    """Verify institutional enrichment maps co-owning funds and adjusts scores."""
    from analysis.thematic_beneficiaries import _enrich_institutional_support

    beneficiaries = [
        {"symbol": "VRT", "company_name": "Vertiv Holdings", "score": 0.50},
        {"symbol": "MU", "company_name": "Micron Tech", "score": 0.40},
    ]

    mock_fund_data = {
        "fund_name": "TEST FUND CAPITAL",
        "holdings": [
            {"name_of_issuer": "NVIDIA CORP", "value_usd": 1000000.0},
            {"name_of_issuer": "VERTIV HOLDINGS CO", "value_usd": 500000.0},
        ],
    }

    with patch(
        "analysis.thematic_beneficiaries.get_fund_holdings", new_callable=AsyncMock, return_value=mock_fund_data
    ):
        co_ownership = await _enrich_institutional_support(
            "NVDA",
            beneficiaries,
            top_n=2,
            fund_ciks={"TEST_FUND": "0001234567"},
        )

    assert "VRT" in co_ownership
    assert co_ownership["VRT"]["co_owning_fund_count"] == 1
    assert "institutional_co_ownership" in beneficiaries[0]
    assert beneficiaries[0]["institutional_co_ownership"]["co_owning_fund_count"] == 1
    assert beneficiaries[0]["score"] == 0.70  # 0.50 + 0.20


def test_format_thematic_beneficiaries_markdown_with_institutional():
    """Verify markdown output correctly renders institutional co-holding column and details."""
    from analysis.thematic_beneficiaries import format_thematic_beneficiaries_markdown

    data = {
        "anchor_ticker": "NVDA",
        "theme": "AI Power & Cooling",
        "lookback_days": 60,
        "anchor_capex_growth_qoq": 0.524,
        "beneficiaries": [
            {
                "symbol": "VRT",
                "industry": "Electrical Equipment",
                "market_cap": 32000000000,
                "correlation": 0.78,
                "beta": 1.25,
                "score": 0.95,
                "fundamentals": {
                    "candidate_rev_growth_qoq": 0.236,
                    "candidate_op_inc_growth_qoq": 0.449,
                },
                "institutional_co_ownership": {
                    "symbol": "VRT",
                    "co_owning_fund_count": 2,
                    "total_co_owned_value_usd": 1200000000.0,
                    "funds": ["BERKSHIRE HATHAWAY", "COATUE"],
                },
            }
        ],
        "summary": "Analyzed 1 related beneficiary for NVDA.",
    }

    md = format_thematic_beneficiaries_markdown(data)
    assert "| Inst Co-Hold |" in md
    assert "| VRT |" in md
    assert "Co-Holding Institutional Funds:" in md
    assert "- VRT: Co-held by BERKSHIRE HATHAWAY, COATUE" in md
