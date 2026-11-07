"""Hermetic unit tests for institutional whale stakes (Schedule 13D/13G) ingestion."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingest.government import GovernmentPipeline
from ingest.whale_fetchers import (
    _safe_float,
    fetch_beneficial_ownership,
    filter_whale_stakes,
    ingest_institutional_whales,
    upsert_institutional_whale_stakes,
)


def test_safe_float():
    """Verify safe float parsing handles diverse strings, symbols, and nulls."""
    assert _safe_float("7.45%") == 7.45
    assert _safe_float("$1,000,000") == 1000000.0
    assert _safe_float(None) == 0.0
    assert _safe_float("null") == 0.0
    assert _safe_float("bad", default=2.5) == 2.5


def test_filter_whale_stakes():
    """Verify filtering retains high-conviction stakes and exits while dropping low ones."""
    sample_filings = [
        {
            "symbol": "PLTR",
            "nameOfReportingPerson": "Vanguard Capital Management",
            "cik": "0001045810",
            "filingDate": "2026-04-30",
            "acceptedDate": "2026-04-30",
            "percentOfClass": "7.28",
            "amountBeneficiallyOwned": "166908333",
            "typeOfReportingPerson": "IA",
            "url": "https://www.sec.gov/.../xslSCHEDULE_13G_X02/doc.xml",
        },
        {
            "symbol": "PLTR",
            "nameOfReportingPerson": "The Vanguard Group",
            "cik": "0000102909",
            "filingDate": "2026-03-27",
            "percentOfClass": "0.0",
            "amountBeneficiallyOwned": "0",
            "typeOfReportingPerson": "IA",
            "url": "https://www.sec.gov/.../xslSCHEDULE_13G_X02/doc.xml",
        },
        {
            "symbol": "PLTR",
            "nameOfReportingPerson": "Minor Holder",
            "cik": "0000999999",
            "filingDate": "2026-01-15",
            "percentOfClass": "1.2",
            "amountBeneficiallyOwned": "5000",
            "typeOfReportingPerson": "IA",
            "url": "https://www.sec.gov/.../xslSCHEDULE_13G_X02/doc.xml",
        },
        {
            "symbol": "PLTR",
            "nameOfReportingPerson": "Elliott Investment Management",
            "cik": "0001045810",
            "filingDate": "2026-05-01",
            "percentOfClass": "6.50",
            "amountBeneficiallyOwned": "120000000",
            "typeOfReportingPerson": "IA",
            "url": "https://www.sec.gov/.../xslSCHEDULE_13D_X01/doc.xml",
        },
    ]

    filtered = filter_whale_stakes(sample_filings, min_percent=4.0)
    assert len(filtered) == 3

    # Check accumulation
    vanguard = filtered[0]
    assert vanguard["symbol"] == "PLTR"
    assert vanguard["percent_of_class"] == 7.28
    assert vanguard["filing_type"] == "13G"
    assert vanguard["is_exit"] is False

    # Check exit (0%)
    exit_vanguard = filtered[1]
    assert exit_vanguard["percent_of_class"] == 0.0
    assert exit_vanguard["is_exit"] is True

    # Check activist (13D)
    elliott = filtered[2]
    assert elliott["percent_of_class"] == 6.5
    assert elliott["filing_type"] == "13D"
    assert elliott["is_exit"] is False


@pytest.mark.asyncio
async def test_fetch_beneficial_ownership_success():
    """Verify fetching beneficial ownership returns parsed json on 200."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [{"symbol": "NVDA", "percentOfClass": "7.3"}]

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with (
        patch("ingest.whale_fetchers.FMP_API_KEY", "mock-fmp-key"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        data = await fetch_beneficial_ownership("NVDA")

    assert len(data) == 1
    assert data[0]["symbol"] == "NVDA"


@pytest.mark.asyncio
async def test_fetch_beneficial_ownership_missing_key():
    """Verify fetch returns empty list when API key is missing."""
    with patch("ingest.whale_fetchers.FMP_API_KEY", ""):
        data = await fetch_beneficial_ownership("NVDA")
    assert data == []


@pytest.mark.asyncio
async def test_upsert_institutional_whale_stakes():
    """Verify upserting stakes to Supabase."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[{"id": "test-uuid"}])

    mock_sb.table.return_value = mock_table
    mock_table.upsert.return_value = mock_execute

    with patch("ingest.whale_fetchers.get_supabase_client", return_value=mock_sb):
        count = await upsert_institutional_whale_stakes(
            [
                {
                    "symbol": "PLTR",
                    "filer_name": "Vanguard",
                    "filing_date": "2026-04-30",
                    "percent_of_class": 7.28,
                }
            ]
        )

    assert count == 1
    mock_sb.table.assert_called_with("institutional_whale_stakes")


@pytest.mark.asyncio
async def test_ingest_institutional_whales():
    """Verify ingest_institutional_whales pipeline flow."""
    with (
        patch(
            "ingest.whale_fetchers.fetch_beneficial_ownership",
            new_callable=AsyncMock,
            return_value=[
                {
                    "symbol": "NVDA",
                    "nameOfReportingPerson": "Coatue",
                    "filingDate": "2026-05-01",
                    "percentOfClass": "5.5",
                    "amountBeneficiallyOwned": "1000000",
                    "url": "13G",
                }
            ],
        ),
        patch(
            "ingest.whale_fetchers.upsert_institutional_whale_stakes",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        res = await ingest_institutional_whales(symbols=["NVDA"], min_percent=4.0)
        assert res["symbols_processed"] == 1
        assert res["stakes_upserted"] == 1


@pytest.mark.asyncio
async def test_government_pipeline_includes_whales():
    """Verify GovernmentPipeline orchestrates whale ingestion."""
    with (
        patch(
            "ingest.government.fetch_us_treasury_liquidity",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "ingest.government.fetch_usaspending_contracts",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "ingest.government.fetch_canadabuys_contracts",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "ingest.government.ingest_institutional_whales",
            new_callable=AsyncMock,
            return_value={"symbols_processed": 5, "stakes_upserted": 10},
        ) as mock_whales,
        patch(
            "ingest.government.GovernmentPipeline.extract_policy_memories",
            new_callable=AsyncMock,
            return_value=0,
        ),
    ):
        pipeline = GovernmentPipeline()
        await pipeline.run()
        mock_whales.assert_called_once()
