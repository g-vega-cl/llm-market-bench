"""Tests for Congress trading tools and data ingestion."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.congress_tools import (
    fetch_congress_trades_from_db,
    fetch_congress_trades_from_fmp,
    handle_get_congress_trades,
    normalize_fmp_congress_trade,
    parse_amount_range_to_midpoint,
    upsert_congress_trades_to_db,
)


def test_parse_amount_range_to_midpoint():
    """Verify tier ranges parse into calculated midpoints."""
    assert parse_amount_range_to_midpoint("$1,001 - $15,000") == 8000.5
    assert parse_amount_range_to_midpoint("$15,001 - $50,000") == 32500.5
    assert parse_amount_range_to_midpoint("$50,001 - $100,000") == 75000.5
    assert parse_amount_range_to_midpoint("$100,001 - $250,000") == 175000.5
    assert parse_amount_range_to_midpoint("$250,001 - $500,000") == 375000.5
    assert parse_amount_range_to_midpoint("$500,001 - $1,000,000") == 750000.5
    assert parse_amount_range_to_midpoint("$1,000,001 - $5,000,000") == 3000000.5
    assert parse_amount_range_to_midpoint("$5,000,001 - $25,000,000") == 15000000.5
    assert parse_amount_range_to_midpoint("$25,000,001 - $50,000,000") == 37500000.5
    assert parse_amount_range_to_midpoint("> $50,000,000") == 50000000.0
    assert parse_amount_range_to_midpoint("$50,000,000 +") == 50000000.0
    assert parse_amount_range_to_midpoint("Unknown") == 0.0
    assert parse_amount_range_to_midpoint("") == 0.0
    assert parse_amount_range_to_midpoint(None) == 0.0


def test_normalize_fmp_congress_trade_senate():
    """Verify raw Senate payload from FMP is normalized for Supabase."""
    raw_senate = {
        "symbol": "EA",
        "disclosureDate": "2026-09-14",
        "transactionDate": "2026-08-05",
        "firstName": "Angus",
        "lastName": "King",
        "office": "Angus King",
        "district": "ME",
        "owner": "Spouse",
        "assetDescription": "Electronic Arts Inc",
        "assetType": "Stock",
        "type": "Sale (Full)",
        "amount": "$15,001 - $50,000",
        "link": "https://efdsearch.senate.gov/search/view/ptr/123",
    }
    normalized = normalize_fmp_congress_trade(raw_senate, chamber="senate")
    assert normalized is not None
    assert normalized["chamber"] == "senate"
    assert normalized["symbol"] == "EA"
    assert normalized["representative_name"] == "Angus King"
    assert normalized["transaction_type"] == "sale"
    assert normalized["amount_range"] == "$15,001 - $50,000"
    assert normalized["amount_est_midpoint"] == 32500.5
    assert normalized["owner"] == "Spouse"
    assert normalized["district"] == "ME"
    assert normalized["source_url"] == "https://efdsearch.senate.gov/search/view/ptr/123"


def test_normalize_fmp_congress_trade_house():
    """Verify raw House payload from FMP is normalized for Supabase."""
    raw_house = {
        "symbol": "RSG",
        "disclosureDate": "2026-09-15",
        "transactionDate": "2026-08-06",
        "firstName": "Josh",
        "lastName": "Gottheimer",
        "office": "Josh Gottheimer",
        "district": "NJ05",
        "owner": "Joint",
        "assetDescription": "Republic Services Inc",
        "assetType": "Stock",
        "type": "Purchase",
        "amount": "$1,001 - $15,000",
        "link": "https://disclosures-clerk.house.gov/ptr/456.pdf",
    }
    normalized = normalize_fmp_congress_trade(raw_house, chamber="house")
    assert normalized is not None
    assert normalized["chamber"] == "house"
    assert normalized["symbol"] == "RSG"
    assert normalized["representative_name"] == "Josh Gottheimer"
    assert normalized["transaction_type"] == "purchase"
    assert normalized["amount_range"] == "$1,001 - $15,000"
    assert normalized["amount_est_midpoint"] == 8000.5
    assert normalized["district"] == "NJ05"


def test_normalize_fmp_congress_trade_invalid():
    """Invalid trades missing ticker or date return None."""
    assert normalize_fmp_congress_trade({}, chamber="senate") is None
    assert normalize_fmp_congress_trade({"symbol": None}, chamber="house") is None
    assert normalize_fmp_congress_trade({"symbol": "--"}, chamber="house") is None


@pytest.mark.asyncio
async def test_fetch_congress_trades_from_fmp():
    """Verify async fetch from FMP endpoints with mocked HTTP response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "symbol": "NVDA",
            "disclosureDate": "2026-09-10",
            "transactionDate": "2026-08-20",
            "firstName": "Nancy",
            "lastName": "Pelosi",
            "office": "Nancy Pelosi",
            "district": "CA11",
            "owner": "Spouse",
            "type": "Purchase",
            "amount": "$1,000,001 - $5,000,000",
            "link": "https://disclosures-clerk.house.gov/ptr/789.pdf",
        }
    ]

    with (
        patch("tools.congress_tools.FMP_API_KEY", "test-fmp-key"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_get.return_value = mock_response
        trades = await fetch_congress_trades_from_fmp(chamber="house", symbol="NVDA")
        assert len(trades) == 1
        assert trades[0]["symbol"] == "NVDA"
        assert trades[0]["representative_name"] == "Nancy Pelosi"
        assert trades[0]["amount_est_midpoint"] == 3000000.5


@pytest.mark.asyncio
async def test_fetch_congress_trades_missing_api_key():
    """Verify empty list returned when FMP_API_KEY is unset."""
    with patch("tools.congress_tools.FMP_API_KEY", ""):
        trades = await fetch_congress_trades_from_fmp(chamber="house", symbol="NVDA")
        assert trades == []


@pytest.mark.asyncio
async def test_upsert_congress_trades_to_db():
    """Verify Supabase batch upsert call."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = [{"id": "1"}, {"id": "2"}]

    mock_sb.table.return_value = mock_table
    mock_table.upsert.return_value = mock_upsert
    mock_upsert.execute.return_value = mock_execute

    sample_trades = [
        {
            "chamber": "house",
            "symbol": "NVDA",
            "transaction_date": "2026-08-20",
            "disclosure_date": "2026-09-10",
            "representative_name": "Nancy Pelosi",
            "transaction_type": "purchase",
            "amount_range": "$1,000,001 - $5,000,000",
            "amount_est_midpoint": 3000000.5,
        }
    ]

    with patch("tools.congress_tools.get_supabase_client", return_value=mock_sb):
        count = await upsert_congress_trades_to_db(sample_trades)
        assert count == 2
        mock_table.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_congress_trades_from_db():
    """Verify database query construction and execution."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = [
        {
            "chamber": "senate",
            "symbol": "NVDA",
            "transaction_date": "2026-08-15",
            "disclosure_date": "2026-09-08",
            "representative_name": "Mark Kelly",
            "transaction_type": "purchase",
            "amount_range": "$50,001 - $100,000",
            "amount_est_midpoint": 75000.5,
        }
    ]

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = mock_execute

    with patch("tools.congress_tools.get_supabase_client", return_value=mock_sb):
        results = await fetch_congress_trades_from_db(symbol="NVDA", chamber="senate", days=30)
        assert len(results) == 1
        assert results[0]["representative_name"] == "Mark Kelly"


@pytest.mark.asyncio
async def test_handle_get_congress_trades():
    """Verify agent handler formats human and LLM friendly markdown."""
    sample_records = [
        {
            "chamber": "house",
            "symbol": "NVDA",
            "transaction_date": "2026-08-20",
            "disclosure_date": "2026-09-10",
            "representative_name": "Nancy Pelosi",
            "district": "CA11",
            "owner": "Spouse",
            "transaction_type": "purchase",
            "amount_range": "$1,000,001 - $5,000,000",
            "amount_est_midpoint": 3000000.5,
            "source_url": "https://example.com/ptr.pdf",
        }
    ]

    with patch("tools.congress_tools.fetch_congress_trades_from_db", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = sample_records
        output = await handle_get_congress_trades(symbol="NVDA", days=60)
        assert "Congress Trading Disclosures" in output
        assert "NVDA" in output
        assert "Nancy Pelosi" in output
        assert "PURCHASE" in output
        assert "$1,000,001 - $5,000,000" in output


def test_congress_tool_registry():
    """Verify get_congress_trades is registered in canonical tools registry."""
    from core.llm.tools import CANONICAL_TOOLS_REGISTRY, GET_CONGRESS_TRADES_TOOL

    assert "get_congress_trades" in CANONICAL_TOOLS_REGISTRY
    assert CANONICAL_TOOLS_REGISTRY["get_congress_trades"] == GET_CONGRESS_TRADES_TOOL


@pytest.mark.asyncio
async def test_tool_dispatcher_dispatches_congress_trades():
    """Verify execute_tool routes get_congress_trades correctly."""
    from core.llm.tools import execute_tool

    with patch("tools.congress_tools.handle_get_congress_trades", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = "Mocked Congress Trades Markdown"
        res = await execute_tool("get_congress_trades", {"ticker": "NVDA", "days": 30})
        assert res == "Mocked Congress Trades Markdown"
        mock_handler.assert_called_once_with(
            symbol="NVDA",
            chamber=None,
            days=30,
            transaction_type=None,
            limit=20,
        )


@pytest.mark.asyncio
async def test_handle_get_congress_trades_fallback_to_fmp():
    """Verify handler falls back to live FMP fetch when DB returns empty."""
    from datetime import UTC, datetime

    today = datetime.now(UTC).date().isoformat()
    mock_fmp_trades = [
        {
            "chamber": "senate",
            "symbol": "AAPL",
            "transaction_date": today,
            "disclosure_date": today,
            "representative_name": "Sheldon Whitehouse",
            "district": "RI",
            "owner": "Self",
            "transaction_type": "sale",
            "amount_range": "$15,001 - $50,000",
            "amount_est_midpoint": 32500.5,
            "source_url": "https://example.com/ptr2.pdf",
        }
    ]

    with (
        patch("tools.congress_tools.fetch_congress_trades_from_db", new_callable=AsyncMock) as mock_db,
        patch("tools.congress_tools.fetch_congress_trades_from_fmp", new_callable=AsyncMock) as mock_fmp,
        patch("tools.congress_tools.upsert_congress_trades_to_db", new_callable=AsyncMock) as mock_upsert,
    ):
        mock_db.return_value = []
        mock_fmp.side_effect = [mock_fmp_trades, []]
        mock_upsert.return_value = 1

        output = await handle_get_congress_trades(symbol="AAPL", days=30, transaction_type="sale")
        assert "Congress Trading Disclosures" in output
        assert "AAPL" in output
        assert "Sheldon Whitehouse" in output
        assert "SALE" in output
        mock_upsert.assert_called_once()


@pytest.mark.asyncio
async def test_handle_get_congress_trades_no_results():
    """Verify handler returns friendly message when no trades are found."""
    with (
        patch("tools.congress_tools.fetch_congress_trades_from_db", new_callable=AsyncMock) as mock_db,
        patch("tools.congress_tools.fetch_congress_trades_from_fmp", new_callable=AsyncMock) as mock_fmp,
    ):
        mock_db.return_value = []
        mock_fmp.return_value = []

        output = await handle_get_congress_trades(symbol="XYZ", days=30)
        assert "No recent Congress trading disclosures found for XYZ" in output


@pytest.mark.asyncio
async def test_run_congress_update_script():
    """Verify batch update script runs and calls upsert."""
    from scripts.update_congress_trades import run_congress_update

    sample_trades = [
        {
            "chamber": "senate",
            "symbol": "NVDA",
            "transaction_date": "2026-08-20",
            "disclosure_date": "2026-09-10",
            "representative_name": "Angus King",
            "transaction_type": "sale",
            "amount_range": "$15,001 - $50,000",
            "amount_est_midpoint": 32500.5,
        }
    ]

    with (
        patch("scripts.update_congress_trades.fetch_congress_trades_from_fmp", new_callable=AsyncMock) as mock_fmp,
        patch("scripts.update_congress_trades.upsert_congress_trades_to_db", new_callable=AsyncMock) as mock_upsert,
    ):
        mock_fmp.side_effect = [sample_trades, []]
        mock_upsert.return_value = 1

        res = await run_congress_update(symbol="NVDA")
        assert res == 1
        mock_upsert.assert_called_once()
