"""Hermetic unit tests for government liquidity, debt, and contract ingestion."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingest.government import GovernmentPipeline, run_government_pipeline
from ingest.government_fetchers import (
    _safe_float,
    fetch_canadabuys_contracts,
    fetch_us_treasury_liquidity,
    fetch_usaspending_contracts,
    parse_canadabuys_csv,
    upsert_gov_contracts,
    upsert_gov_macro_liquidity,
)


def test_safe_float():
    """Verify safe float conversion handles strings, nulls, and formatting."""
    assert _safe_float("1,234.56") == 1234.56
    assert _safe_float("$10,000.00") == 10000.0
    assert _safe_float("null") == 0.0
    assert _safe_float(None) == 0.0
    assert _safe_float("invalid", default=5.0) == 5.0
    assert _safe_float(42.5) == 42.5


@pytest.mark.asyncio
async def test_fetch_us_treasury_liquidity_success():
    """Verify fetching and merging DTS cash, debt to penny, and MTS deficit."""
    mock_dts_resp = MagicMock(status_code=200)
    mock_dts_resp.json.return_value = {
        "data": [
            {
                "record_date": "2026-11-05",
                "account_type": "Treasury General Account (TGA) Opening Balance",
                "open_today_bal": "936248",
            }
        ]
    }

    mock_debt_resp = MagicMock(status_code=200)
    mock_debt_resp.json.return_value = {
        "data": [
            {
                "record_date": "2026-11-05",
                "tot_pub_debt_out_amt": "40556120784983.65",
                "debt_held_public_amt": "32766722473715.61",
                "intragov_hold_amt": "7789398311268.04",
            }
        ]
    }

    mock_mts_resp = MagicMock(status_code=200)
    mock_mts_resp.json.return_value = {
        "data": [
            {
                "record_date": "2026-11-05",
                "current_month_dfct_sur_amt": "-257000000.00",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[mock_dts_resp, mock_debt_resp, mock_mts_resp])

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        records = await fetch_us_treasury_liquidity(days=1)

    assert len(records) == 1
    rec = records[0]
    assert rec["record_date"] == "2026-11-05"
    assert rec["tga_balance"] == 936248.0
    assert rec["tot_pub_debt"] == 40556120784983.65
    assert rec["debt_held_public"] == 32766722473715.61
    assert rec["intragov_holdings"] == 7789398311268.04
    assert rec["monthly_deficit_surplus"] == -257000000.0


@pytest.mark.asyncio
async def test_upsert_gov_macro_liquidity():
    """Verify upserting liquidity records to Supabase."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[{"id": "test-uuid"}])

    mock_sb.table.return_value = mock_table
    mock_table.upsert.return_value = mock_execute

    with patch("ingest.government_fetchers.get_supabase_client", return_value=mock_sb):
        count = await upsert_gov_macro_liquidity([{"record_date": "2026-11-05", "tga_balance": 100.0}])

    assert count == 1
    mock_sb.table.assert_called_with("gov_macro_liquidity")


@pytest.mark.asyncio
async def test_fetch_usaspending_contracts():
    """Verify parsing USAspending contract search response."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "results": [
            {
                "Award ID": "AWARD-999",
                "Recipient Name": "LOCKHEED MARTIN CORP",
                "Award Amount": 5000000.0,
                "Description": "F-35 Logistics Support",
                "Action Date": "2026-11-01",
                "Awarding Agency": "Department of Defense",
                "Contract Number": "FA8615-20-C-0001",
                "generated_internal_id": "CONT_AWD_999",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        contracts = await fetch_usaspending_contracts(days=7, limit=10)

    assert len(contracts) == 1
    c = contracts[0]
    assert c["country"] == "US"
    assert c["award_id"] == "AWARD-999"
    assert c["recipient_name"] == "LOCKHEED MARTIN CORP"
    assert c["award_amount"] == 5000000.0
    assert c["agency_name"] == "Department of Defense"
    assert "usaspending.gov/award/CONT_AWD_999" in c["source_url"]


def test_parse_canadabuys_csv():
    """Verify CanadaBuys CSV parsing for Canadian contracts."""
    csv_sample = (
        '"contractNumber-numeroContrat","supplierStandardizedName-nomNormaliseFournisseur",'
        '"contractValue-valeurContrat","contractAwardDate-dateAttributionContrat",'
        '"title-titre-eng","buyerOrganizationName-nomOrganisationAcheteur-eng"\n'
        '"W8486-24-001","CAE INC.","1250000.00","2026-10-15","Pilot Simulation Training","Department of National Defence"\n'
        '"","INVALID SUPPLIER","500.00","2026-10-16","Test","Test Buyer"\n'
    )
    results = parse_canadabuys_csv(csv_sample, limit=10)
    assert len(results) == 1
    ca = results[0]
    assert ca["country"] == "CA"
    assert ca["award_id"] == "W8486-24-001"
    assert ca["recipient_name"] == "CAE INC."
    assert ca["award_amount"] == 1250000.0
    assert ca["currency"] == "CAD"
    assert ca["agency_name"] == "Department of National Defence"


@pytest.mark.asyncio
async def test_fetch_canadabuys_contracts_network_failure():
    """Verify CanadaBuys fetch handles network/status errors gracefully."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection timed out"))

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        res = await fetch_canadabuys_contracts(limit=10)

    assert res == []


@pytest.mark.asyncio
async def test_upsert_gov_contracts():
    """Verify upserting contracts to Supabase."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_upsert.execute.return_value = MagicMock(data=[{"id": "award-1"}])
    mock_table.upsert.return_value = mock_upsert
    mock_sb.table.return_value = mock_table

    with patch("ingest.government_fetchers.get_supabase_client", return_value=mock_sb):
        count = await upsert_gov_contracts(
            [
                {
                    "country": "US",
                    "award_id": "A1",
                    "recipient_name": "CORP",
                    "award_date": "2026-11-01",
                }
            ]
        )

    assert count == 1
    mock_sb.table.assert_called_with("gov_contracts")


@pytest.mark.asyncio
async def test_government_pipeline_orchestration():
    """Verify end-to-end execution of GovernmentPipeline."""
    with (
        patch(
            "ingest.government.fetch_us_treasury_liquidity",
            new_callable=AsyncMock,
            return_value=[{"record_date": "2026-11-05"}],
        ),
        patch(
            "ingest.government.upsert_gov_macro_liquidity",
            new_callable=AsyncMock,
            return_value=1,
        ),
        patch(
            "ingest.government.fetch_usaspending_contracts",
            new_callable=AsyncMock,
            return_value=[{"award_id": "US1"}],
        ),
        patch(
            "ingest.government.fetch_canadabuys_contracts",
            new_callable=AsyncMock,
            return_value=[{"award_id": "CA1"}],
        ),
        patch(
            "ingest.government.upsert_gov_contracts",
            new_callable=AsyncMock,
            return_value=1,
        ),
        patch(
            "ingest.government.GovernmentPipeline.extract_policy_memories",
            new_callable=AsyncMock,
            return_value=2,
        ),
    ):
        pipeline = GovernmentPipeline()
        count = await pipeline.run()
        assert count == 2

        summary = await run_government_pipeline()
        assert summary["status"] == "success"
        assert summary["memories_created"] == 2
