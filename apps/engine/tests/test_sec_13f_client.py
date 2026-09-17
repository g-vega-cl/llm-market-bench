"""Hermetic unit tests for sec_13f_client module.

Zero outbound network calls. All SEC EDGAR API and file fetches are mocked.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from analysis.sec_13f_client import (
    fetch_latest_13f_metadata,
    get_fund_holdings,
    match_co_ownership,
    parse_13f_infotable_xml,
)

SAMPLE_13F_XML = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>NVIDIA CORP</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>67066G104</cusip>
    <value>1500000000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>12000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
  </infoTable>
  <infoTable>
    <nameOfIssuer>VERTIV HOLDINGS CO</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>92537N108</cusip>
    <value>450000000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>5000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
  </infoTable>
  <infoTable>
    <nameOfIssuer>MICRON TECHNOLOGY INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>595112103</cusip>
    <value>800000000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>8000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
  </infoTable>
</informationTable>
"""


def test_parse_13f_infotable_xml_valid():
    """Verify XML parsing extracts holdings cleanly with issuer names and dollar values."""
    holdings = parse_13f_infotable_xml(SAMPLE_13F_XML)
    assert len(holdings) == 3

    nvda = holdings[0]
    assert nvda["name_of_issuer"] == "NVIDIA CORP"
    assert nvda["cusip"] == "67066G104"
    assert nvda["value_usd"] == 1500000000.0
    assert nvda["shares"] == 12000000.0

    vrt = holdings[1]
    assert vrt["name_of_issuer"] == "VERTIV HOLDINGS CO"
    assert vrt["value_usd"] == 450000000.0


def test_parse_13f_infotable_xml_empty_or_invalid():
    """Verify safe fallback for empty or malformed XML."""
    assert len(parse_13f_infotable_xml("")) == 0
    assert len(parse_13f_infotable_xml("<invalid>xml")) == 0


@pytest.mark.asyncio
async def test_fetch_latest_13f_metadata():
    """Verify metadata resolution for latest Form 13F-HR."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "cik": "1067983",
        "name": "BERKSHIRE HATHAWAY INC",
        "filings": {
            "recent": {
                "form": ["10-Q", "13F-HR", "13F-HR"],
                "accessionNumber": ["0001-00-1", "0001193125-26-352200", "0001193125-26-100000"],
                "filingDate": ["2026-09-01", "2026-08-14", "2026-05-15"],
                "primaryDocument": ["doc1.htm", "primary_doc.xml", "old.xml"],
            }
        },
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    meta = await fetch_latest_13f_metadata("1067983", http_client=mock_client)
    assert meta is not None
    assert meta["accession_clean"] == "000119312526352200"
    assert meta["filing_date"] == "2026-08-14"
    assert meta["cik"] == "0001067983"


@pytest.mark.asyncio
async def test_get_fund_holdings_end_to_end():
    """Verify get_fund_holdings pulls metadata, directory index, and parses target XML."""
    submissions_resp = MagicMock(status_code=200)
    submissions_resp.json.return_value = {
        "cik": "1067983",
        "name": "SAMPLE FUND",
        "filings": {
            "recent": {
                "form": ["13F-HR"],
                "accessionNumber": ["0001193125-26-352200"],
                "filingDate": ["2026-08-14"],
                "primaryDocument": ["primary_doc.xml"],
            }
        },
    }

    dir_resp = MagicMock(status_code=200)
    dir_resp.text = 'href="infotable.xml" href="primary_doc.xml"'

    xml_resp = MagicMock(status_code=200)
    xml_resp.content = SAMPLE_13F_XML.encode("utf-8")

    async def mock_get(url, **kwargs):
        if "submissions" in url:
            return submissions_resp
        elif "infotable.xml" in url:
            return xml_resp
        else:
            return dir_resp

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=mock_get)

    result = await get_fund_holdings("1067983", http_client=mock_client)
    assert result["fund_name"] == "SAMPLE FUND"
    assert len(result["holdings"]) == 3


def test_match_co_ownership():
    """Verify co-ownership matching when fund holds anchor and candidate peers."""
    fund_holdings_map = {
        "SAMPLE FUND A": [
            {"name_of_issuer": "NVIDIA CORP", "value_usd": 1500000000.0},
            {"name_of_issuer": "VERTIV HOLDINGS CO", "value_usd": 450000000.0},
            {"name_of_issuer": "MICRON TECHNOLOGY INC", "value_usd": 800000000.0},
        ],
        "SAMPLE FUND B": [
            {"name_of_issuer": "MICROSOFT CORP", "value_usd": 2000000000.0},
            {"name_of_issuer": "VERTIV HOLDINGS CO", "value_usd": 300000000.0},
        ],
    }

    candidates = {
        "VRT": "VERTIV",
        "MU": "MICRON",
        "CEG": "CONSTELLATION",
    }

    co_holdings = match_co_ownership(
        anchor_keywords=["NVIDIA", "NVDA"],
        candidates=candidates,
        fund_holdings_map=fund_holdings_map,
    )

    # Fund B does not hold Nvidia, so only Fund A should count
    assert "VRT" in co_holdings
    assert co_holdings["VRT"]["co_owning_fund_count"] == 1
    assert co_holdings["VRT"]["total_co_owned_value_usd"] == 450000000.0

    assert "MU" in co_holdings
    assert co_holdings["MU"]["co_owning_fund_count"] == 1

    assert "CEG" not in co_holdings
