"""Hermetic unit tests for Congress trades and Insider trades ingestion pipelines.

Zero external network calls, zero sleep, fully mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingest.congress_fetchers import (
    fetch_latest_congress_trades,
    upsert_congress_trades,
)
from ingest.government import GovernmentPipeline
from ingest.insider_fetchers import (
    fetch_latest_insider_trades,
    fetch_universe_insider_trades,
    upsert_insider_trades,
)


@pytest.fixture
def mock_fmp_congress_response():
    return [
        {
            "firstName": "Nancy",
            "lastName": "Pelosi",
            "office": "House",
            "district": "CA11",
            "symbol": "NVDA",
            "transactionDate": "2026-11-01",
            "disclosureDate": "2026-11-05",
            "type": "Purchase",
            "amount": "$1,000,001 - $5,000,000",
            "owner": "Spouse",
            "assetDescription": "NVIDIA Corporation - Common Stock",
            "link": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20025000.pdf",
        },
        {
            "firstName": "Mark",
            "lastName": "Warner",
            "office": "Senate",
            "district": "VA",
            "symbol": "MSFT",
            "transactionDate": "2026-11-02",
            "disclosureDate": "2026-11-06",
            "type": "Sale (Full)",
            "amount": "$250,001 - $500,000",
            "owner": "Self",
            "assetDescription": "Microsoft Corp",
            "link": "https://efdsearch.senate.gov/search/view/ptr/12345",
        },
    ]


@pytest.fixture
def mock_fmp_insider_response():
    return [
        {
            "symbol": "SHOP",
            "filingDate": "2026-11-05",
            "transactionDate": "2026-11-04",
            "reportingName": "Tobi Lutke",
            "typeOfOwner": "Chief Executive Officer, 10% Owner",
            "transactionType": "P-Purchase",
            "securitiesTransacted": 25000,
            "price": 105.50,
            "securitiesOwned": 1500000,
            "url": "https://www.sec.gov/Archives/edgar/data/1594633/000159463326000012/xslF345X03/wf-form4_1730825000.xml",
        },
        {
            "symbol": "NVDA",
            "filingDate": "2026-11-06",
            "transactionDate": "2026-11-05",
            "reportingName": "Jensen Huang",
            "typeOfOwner": "CEO and Director",
            "transactionType": "S-Sale",
            "securitiesTransacted": 50000,
            "price": 140.25,
            "securitiesOwned": 75000000,
            "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000045/xslF345X03/wf-form4_1730911000.xml",
        },
    ]


@pytest.mark.asyncio
async def test_fetch_latest_congress_trades(mock_fmp_congress_response):
    """Verify fetching and normalizing Congress disclosures across chambers."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_fmp_congress_response

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_resp

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("ingest.congress_fetchers.FMP_API_KEY", "mock_key"),
    ):
        records = await fetch_latest_congress_trades(limit=10)

        assert len(records) > 0
        symbols = [r["symbol"] for r in records]
        assert "NVDA" in symbols or "MSFT" in symbols
        for r in records:
            assert r["chamber"] in ("senate", "house")
            assert "transaction_date" in r
            assert "disclosure_date" in r
            assert "amount_est_midpoint" in r
            assert r["amount_est_midpoint"] > 0


@pytest.mark.asyncio
async def test_upsert_congress_trades():
    """Verify batch upserting Congress disclosures to the database."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
        {"id": "c1"},
        {"id": "c2"},
    ]

    records = [
        {
            "chamber": "house",
            "symbol": "NVDA",
            "transaction_date": "2026-11-01",
            "disclosure_date": "2026-11-05",
            "representative_name": "Nancy Pelosi",
            "district": "CA11",
            "owner": "Spouse",
            "transaction_type": "purchase",
            "amount_range": "$1,000,001 - $5,000,000",
            "amount_est_midpoint": 3000000.50,
            "asset_description": "NVIDIA Corporation",
            "source_url": "https://example.com",
        }
    ]

    with patch("ingest.congress_fetchers.get_supabase_client", return_value=mock_sb):
        upserted = await upsert_congress_trades(records)
        assert upserted == 2
        mock_sb.table.assert_called_with("congress_trades")


@pytest.mark.asyncio
async def test_fetch_latest_insider_trades(mock_fmp_insider_response):
    """Verify fetching and normalizing market-wide Form 4 insider filings."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_fmp_insider_response

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_resp

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("ingest.insider_fetchers.FMP_API_KEY", "mock_key"),
    ):
        records = await fetch_latest_insider_trades(limit=10)

        assert len(records) == 2
        symbols = [r["symbol"] for r in records]
        assert "SHOP" in symbols
        assert "NVDA" in symbols
        shop = next(r for r in records if r["symbol"] == "SHOP")
        assert shop["transaction_type"] == "purchase"
        assert shop["securities_transacted"] == 25000.0
        assert shop["total_value"] == 25000 * 105.50


@pytest.mark.asyncio
async def test_fetch_universe_insider_trades(mock_fmp_insider_response):
    """Verify targeted insider trades fetching for active universe tickers."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_fmp_insider_response

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_resp

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("ingest.insider_fetchers.FMP_API_KEY", "mock_key"),
    ):
        records = await fetch_universe_insider_trades(symbols=["SHOP"], limit_per_symbol=10)

        assert len(records) == 2
        assert records[0]["symbol"] in ("SHOP", "NVDA")


@pytest.mark.asyncio
async def test_upsert_insider_trades():
    """Verify batch upserting insider disclosures to the database."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "i1"}]

    records = [
        {
            "symbol": "SHOP",
            "filing_date": "2026-11-05",
            "transaction_date": "2026-11-04",
            "reporting_name": "Tobi Lutke",
            "type_of_owner": "CEO",
            "transaction_type": "purchase",
            "securities_transacted": 25000.0,
            "price": 105.50,
            "total_value": 2637500.0,
            "securities_owned": 1500000.0,
            "source_url": "https://example.com",
        }
    ]

    with patch("ingest.insider_fetchers.get_supabase_client", return_value=mock_sb):
        upserted = await upsert_insider_trades(records)
        assert upserted == 1
        mock_sb.table.assert_called_with("insider_trades")


@pytest.mark.asyncio
async def test_government_pipeline_orchestrates_all_five():
    """Verify GovernmentPipeline orchestrates liquidity, contracts, whales, congress, and insiders."""
    pipeline = GovernmentPipeline()

    with (
        patch.object(pipeline, "ingest_liquidity", AsyncMock(return_value=5)),
        patch.object(pipeline, "ingest_contracts", AsyncMock(return_value={"us_contracts": 10, "ca_contracts": 5})),
        patch.object(
            pipeline, "ingest_whales", AsyncMock(return_value={"stakes_upserted": 8, "symbols_processed": 10})
        ),
        patch.object(pipeline, "ingest_congress", AsyncMock(return_value=12)),
        patch.object(pipeline, "ingest_insiders", AsyncMock(return_value=25)),
        patch.object(pipeline, "extract_policy_memories", AsyncMock(return_value=3)),
    ):
        result = await pipeline.run()

        assert result == 3
        pipeline.ingest_liquidity.assert_called_once()
        pipeline.ingest_contracts.assert_called_once()
        pipeline.ingest_whales.assert_called_once()
        pipeline.ingest_congress.assert_called_once()
        pipeline.ingest_insiders.assert_called_once()
        pipeline.extract_policy_memories.assert_called_once()
