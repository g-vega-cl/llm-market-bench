"""Hermetic unit tests for insider_tools module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.insider_tools import (
    execute_get_insider_trades_tool,
    fetch_insider_statistics_from_fmp,
    fetch_insider_trades_from_db,
    fetch_insider_trades_from_fmp,
    handle_get_insider_trades,
    normalize_fmp_insider_trade,
    upsert_insider_trades_to_db,
)


def test_normalize_fmp_insider_trade_valid():
    """Verify raw FMP Form 4 payload is normalized into standard schema."""
    raw = {
        "symbol": "NVDA",
        "filingDate": "2026-09-23 18:00:00",
        "transactionDate": "2026-09-21",
        "reportingName": "Teter Timothy S.",
        "typeOfOwner": "officer: EVP, General Counsel",
        "transactionType": "S-Sale",
        "securitiesTransacted": 12483,
        "price": 222.19,
        "securitiesOwned": 2705637,
        "url": "https://www.sec.gov/filing/123",
    }
    normalized = normalize_fmp_insider_trade(raw)
    assert normalized is not None
    assert normalized["symbol"] == "NVDA"
    assert normalized["filing_date"] == "2026-09-23"
    assert normalized["transaction_date"] == "2026-09-21"
    assert normalized["reporting_name"] == "Teter Timothy S."
    assert normalized["type_of_owner"] == "officer: EVP, General Counsel"
    assert normalized["transaction_type"] == "sale"
    assert normalized["securities_transacted"] == 12483.0
    assert normalized["price"] == 222.19
    assert normalized["total_value"] == round(12483.0 * 222.19, 2)
    assert normalized["source_url"] == "https://www.sec.gov/filing/123"


def test_normalize_fmp_insider_trade_purchase():
    """Verify purchase transactions normalize correctly."""
    raw = {
        "symbol": "AAPL",
        "filingDate": "2026-09-10",
        "transactionDate": "2026-09-08",
        "reportingName": "Cook Timothy D.",
        "typeOfOwner": "director, chief executive officer",
        "transactionType": "P-Purchase",
        "securitiesTransacted": "50000",
        "price": "180.50",
    }
    normalized = normalize_fmp_insider_trade(raw)
    assert normalized is not None
    assert normalized["transaction_type"] == "purchase"
    assert normalized["securities_transacted"] == 50000.0
    assert normalized["price"] == 180.50
    assert normalized["total_value"] == 9025000.0


def test_normalize_fmp_insider_trade_invalid():
    """Verify invalid payloads return None."""
    assert normalize_fmp_insider_trade({}) is None
    assert normalize_fmp_insider_trade({"symbol": "NONE"}) is None
    assert normalize_fmp_insider_trade({"symbol": "NVDA"}) is None  # Missing dates


@pytest.mark.asyncio
async def test_fetch_insider_trades_from_fmp_success():
    """Verify FMP fetch parses and filters raw items."""
    mock_payload = [
        {
            "symbol": "NVDA",
            "filingDate": "2026-09-23",
            "transactionDate": "2026-09-21",
            "reportingName": "Teter Timothy S.",
            "transactionType": "S-Sale",
            "securitiesTransacted": 1000,
            "price": 200.0,
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        results = await fetch_insider_trades_from_fmp("NVDA", limit=10)
        assert len(results) == 1
        assert results[0]["reporting_name"] == "Teter Timothy S."
        assert results[0]["transaction_type"] == "sale"


@pytest.mark.asyncio
async def test_fetch_insider_statistics_from_fmp():
    """Verify statistics fetch returns parsed dict."""
    mock_stat = [{"symbol": "NVDA", "quarter": 3, "year": 2026, "acquiredDisposedRatio": 0.15, "totalSales": 10}]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_stat
        mock_get.return_value = mock_resp

        stat = await fetch_insider_statistics_from_fmp("NVDA")
        assert stat is not None
        assert stat["quarter"] == 3
        assert stat["totalSales"] == 10


@pytest.mark.asyncio
async def test_upsert_insider_trades_to_db():
    """Verify upsert invokes Supabase table execute."""
    trades = [
        {
            "symbol": "NVDA",
            "reporting_name": "Teter Timothy",
            "transaction_date": "2026-09-21",
            "filing_date": "2026-09-23",
            "transaction_type": "sale",
            "securities_transacted": 1000.0,
            "price": 200.0,
            "total_value": 200000.0,
        }
    ]

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_exec = MagicMock()
    mock_exec.execute.return_value = MagicMock(data=trades)

    mock_sb.table.return_value = mock_table
    mock_table.upsert.return_value = mock_upsert
    mock_upsert.execute = mock_exec.execute

    with patch("tools.insider_tools.get_supabase_client", return_value=mock_sb):
        count = await upsert_insider_trades_to_db(trades)
        assert count == 1


@pytest.mark.asyncio
async def test_fetch_insider_trades_from_db():
    """Verify DB query executes with filters."""
    trades = [{"symbol": "NVDA", "reporting_name": "Teter", "filing_date": "2026-09-23"}]

    mock_sb = MagicMock()
    mock_query = MagicMock()
    mock_sb.table.return_value.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=trades)

    with patch("tools.insider_tools.get_supabase_client", return_value=mock_sb):
        res = await fetch_insider_trades_from_db("NVDA", days=30)
        assert len(res) == 1
        assert res[0]["symbol"] == "NVDA"


@pytest.mark.asyncio
async def test_handle_get_insider_trades_end_to_end():
    """Verify Markdown formatting with trades and sentiment."""
    mock_db_trades = [
        {
            "symbol": "NVDA",
            "reporting_name": "Huang Jen Hsun",
            "type_of_owner": "CEO",
            "transaction_type": "sale",
            "securities_transacted": 10000.0,
            "price": 220.0,
            "total_value": 2200000.0,
            "transaction_date": "2026-09-20",
            "filing_date": "2026-09-22",
        }
    ]

    with (
        patch("tools.insider_tools.fetch_insider_trades_from_db", new_callable=AsyncMock) as mock_db,
        patch("tools.insider_tools.fetch_insider_statistics_from_fmp", new_callable=AsyncMock) as mock_stat,
    ):
        mock_db.return_value = mock_db_trades
        mock_stat.return_value = {
            "quarter": 3,
            "year": 2026,
            "acquiredDisposedRatio": 0.05,
            "totalSales": 12,
            "totalPurchases": 0,
        }

        out = await handle_get_insider_trades("NVDA", days=60)
        assert "### Corporate Insider Trades (SEC Form 4): NVDA" in out
        assert "Huang Jen Hsun" in out
        assert "CEO" in out
        assert "SALE" in out
        assert "Bearish Net Selling" in out


@pytest.mark.asyncio
async def test_execute_get_insider_trades_tool():
    """Verify execution wrapper."""
    with patch("tools.insider_tools.handle_get_insider_trades", new_callable=AsyncMock) as mock_handle:
        mock_handle.return_value = "Formatted Result"
        res = await execute_get_insider_trades_tool("AAPL", days=45)
        assert res == "Formatted Result"
        mock_handle.assert_called_once_with(symbol="AAPL", days=45, transaction_type="all", limit=15)
