"""Hermetic unit tests for whale_tools module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.whale_tools import (
    execute_get_whale_holdings_tool,
    fetch_beneficial_ownership_from_fmp,
    format_beneficial_ownership_markdown,
    format_fund_holdings_markdown,
    handle_get_whale_holdings,
)


def test_format_beneficial_ownership_markdown():
    """Verify Schedule 13D/13G filings format into scannable table."""
    filings = [
        {
            "nameOfReportingPerson": "Vanguard Capital Management",
            "typeOfReportingPerson": "IA",
            "percentOfClass": "7.31",
            "amountBeneficiallyOwned": "1777408252",
            "filingDate": "2026-04-28",
        },
        {
            "nameOfReportingPerson": "BlackRock, Inc.",
            "typeOfReportingPerson": "HC",
            "percentOfClass": "7.10",
            "amountBeneficiallyOwned": "177858484",
            "filingDate": "2026-02-01",
        },
    ]

    md = format_beneficial_ownership_markdown(filings, "NVDA", limit=5)
    assert "### Institutional Whale & Blockholder Holdings (Schedule 13D/13G): NVDA" in md
    assert "Vanguard Capital Management" in md
    assert "Investment Advisor (Fund)" in md
    assert "7.31%" in md
    assert "BlackRock, Inc." in md
    assert "Holding Company" in md


def test_format_fund_holdings_markdown():
    """Verify 13F portfolio holdings format into ranked table."""
    holdings_info = {
        "fund_name": "BERKSHIRE HATHAWAY INC",
        "filing_date": "2026-08-14",
        "holdings": [
            {
                "name_of_issuer": "APPLE INC",
                "title_of_class": "COM",
                "value_usd": 85000000000.0,
                "shares": 400000000.0,
            },
            {
                "name_of_issuer": "AMERICAN EXPRESS CO",
                "title_of_class": "COM",
                "value_usd": 35000000000.0,
                "shares": 150000000.0,
            },
        ],
    }

    md = format_fund_holdings_markdown("BERKSHIRE_HATHAWAY", holdings_info, limit=5)
    assert "### Form 13F Portfolio: BERKSHIRE HATHAWAY INC (Filed: 2026-08-14)" in md
    assert "#1 | APPLE INC" in md
    assert "$85,000,000,000" in md
    assert "#2 | AMERICAN EXPRESS CO" in md


@pytest.mark.asyncio
async def test_fetch_beneficial_ownership_from_fmp():
    """Verify FMP call handles valid response."""
    mock_data = [{"symbol": "NVDA", "nameOfReportingPerson": "NVIDIA Corporation", "percentOfClass": 9.3}]
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value = mock_resp

        res = await fetch_beneficial_ownership_from_fmp("NVDA")
        assert len(res) == 1
        assert res[0]["nameOfReportingPerson"] == "NVIDIA Corporation"


@pytest.mark.asyncio
async def test_handle_get_whale_holdings_by_ticker():
    """Verify handle_get_whale_holdings fetches and formats ticker blockholders without hidden DB network fallbacks."""
    mock_data = [
        {
            "symbol": "NVDA",
            "nameOfReportingPerson": "Coatue Management LLC",
            "typeOfReportingPerson": "IA",
            "percentOfClass": 5.2,
            "amountBeneficiallyOwned": 50000000,
            "filingDate": "2026-05-15",
        }
    ]
    with (
        patch("tools.whale_tools.fetch_whale_stakes_from_db", new_callable=AsyncMock, return_value=[]),
        patch("tools.whale_tools.fetch_beneficial_ownership_from_fmp", new_callable=AsyncMock) as mock_fetch,
        patch("tools.whale_tools.upsert_whale_stakes_to_db", new_callable=AsyncMock, return_value=1),
    ):
        mock_fetch.return_value = mock_data
        out = await handle_get_whale_holdings(ticker="NVDA")
        assert "Coatue Management LLC" in out
        assert "5.20%" in out


@pytest.mark.asyncio
async def test_handle_get_whale_holdings_by_fund():
    """Verify handle_get_whale_holdings retrieves curated 13F fund portfolio."""
    mock_holdings = {
        "fund_name": "Coatue Management",
        "filing_date": "2026-08-14",
        "holdings": [{"name_of_issuer": "NVIDIA CORP", "value_usd": 1200000000.0, "shares": 10000000.0}],
    }
    with patch("tools.whale_tools.get_fund_holdings", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_holdings
        out = await handle_get_whale_holdings(fund_name="COATUE_MANAGEMENT")
        assert "Coatue Management" in out
        assert "NVIDIA CORP" in out


@pytest.mark.asyncio
async def test_execute_get_whale_holdings_tool():
    """Verify tool wrapper execution."""
    with patch("tools.whale_tools.handle_get_whale_holdings", new_callable=AsyncMock) as mock_handle:
        mock_handle.return_value = "Whale Data"
        res = await execute_get_whale_holdings_tool(ticker="TSLA")
        assert res == "Whale Data"
        mock_handle.assert_called_once_with(ticker="TSLA", fund_name=None, limit=15)


@pytest.mark.asyncio
async def test_handle_get_whale_holdings_db_hit_skips_fmp():
    """Verify DB cache hit returns formatted institutional_whale_stakes rows without calling FMP."""
    from tools.whale_tools import fetch_whale_stakes_from_db  # noqa: F401

    db_rows = [
        {
            "symbol": "NVDA",
            "filer_name": "Vanguard Group Inc",
            "reporting_type": "IA",
            "filing_type": "13G",
            "percent_of_class": 8.45,
            "shares_beneficially_owned": 200000000,
            "filing_date": "2026-10-15",
            "is_exit": False,
        }
    ]
    with (
        patch("tools.whale_tools.fetch_whale_stakes_from_db", new_callable=AsyncMock, return_value=db_rows) as mock_db,
        patch("tools.whale_tools.fetch_beneficial_ownership_from_fmp", new_callable=AsyncMock) as mock_fmp,
    ):
        out = await handle_get_whale_holdings(ticker="NVDA")
        assert "Vanguard Group Inc" in out
        assert "8.45%" in out
        mock_db.assert_awaited_once_with("NVDA", limit=15)
        mock_fmp.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_get_whale_holdings_db_miss_falls_back_and_upserts():
    """Verify DB cache miss fetches from FMP and persists normalized rows to institutional_whale_stakes."""
    fmp_rows = [
        {
            "symbol": "NVDA",
            "nameOfReportingPerson": "BlackRock Inc",
            "typeOfReportingPerson": "HC",
            "percentOfClass": 7.12,
            "amountBeneficiallyOwned": 175000000,
            "filingDate": "2026-10-18",
            "url": "https://www.sec.gov/Archives/edgar/data/1045810/13g.htm",
        }
    ]
    with (
        patch("tools.whale_tools.fetch_whale_stakes_from_db", new_callable=AsyncMock, return_value=[]),
        patch(
            "tools.whale_tools.fetch_beneficial_ownership_from_fmp",
            new_callable=AsyncMock,
            return_value=fmp_rows,
        ) as mock_fmp,
        patch("tools.whale_tools.upsert_whale_stakes_to_db", new_callable=AsyncMock, return_value=1) as mock_upsert,
    ):
        out = await handle_get_whale_holdings(ticker="NVDA")
        assert "BlackRock Inc" in out
        assert "7.12%" in out
        mock_fmp.assert_awaited_once_with("NVDA")
        mock_upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_get_whale_holdings_stale_db_cache_refreshes_from_fmp():
    """Verify DB cache rows older than TTL trigger an FMP refresh."""
    stale_rows = [
        {
            "symbol": "PLTR",
            "filer_name": "Stale Fund LP",
            "reporting_type": "IA",
            "filing_type": "13G",
            "percent_of_class": 5.5,
            "shares_beneficially_owned": 10000000,
            "filing_date": "2026-08-01",
            "created_at": "2026-08-01T00:00:00+00:00",
            "is_exit": False,
        }
    ]
    fresh_fmp_rows = [
        {
            "symbol": "PLTR",
            "nameOfReportingPerson": "Fresh Activist Partners",
            "typeOfReportingPerson": "IA",
            "percentOfClass": 6.4,
            "amountBeneficiallyOwned": 15000000,
            "filingDate": "2026-11-10",
            "url": "https://www.sec.gov/Archives/edgar/data/1321655/13d.htm",
        }
    ]
    with (
        patch("tools.whale_tools.fetch_whale_stakes_from_db", new_callable=AsyncMock, return_value=stale_rows),
        patch(
            "tools.whale_tools.fetch_beneficial_ownership_from_fmp", new_callable=AsyncMock, return_value=fresh_fmp_rows
        ) as mock_fmp,
        patch("tools.whale_tools.upsert_whale_stakes_to_db", new_callable=AsyncMock, return_value=1) as mock_upsert,
    ):
        out = await handle_get_whale_holdings(ticker="PLTR")
        assert "Fresh Activist Partners" in out
        mock_fmp.assert_awaited_once_with("PLTR")
        mock_upsert.assert_awaited_once()
