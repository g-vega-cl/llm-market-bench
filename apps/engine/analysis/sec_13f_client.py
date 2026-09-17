"""SEC Form 13F-HR Institutional Holdings Client.

Retrieves and parses quarterly Form 13F portfolio disclosures from the SEC EDGAR system
to detect institutional co-ownership clusters across thematic anchor assets and supplier peers.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from core.config import logger

SEC_EDGAR_USER_AGENT = "MarketBench research@benchify.com"

# Curated institutional managers with significant thematic equity exposure
DEFAULT_THEMATIC_FUNDS = {
    "COATUE_MANAGEMENT": "0001135730",
    "APPALOOSA": "0001656456",
    "WHALE_ROCK": "0001387322",
    "DUQUESNE": "0001536411",
    "BERKSHIRE_HATHAWAY": "0001067983",
}


def parse_13f_infotable_xml(xml_content: str | bytes) -> list[dict[str, Any]]:
    """Parses Form 13F information table XML into structured holding records."""
    if not xml_content:
        return []

    try:
        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        logger.debug("Failed parsing 13F XML content: %s", e)
        return []

    holdings: list[dict[str, Any]] = []
    for row in root.findall("{*}infoTable"):
        issuer = row.find("{*}nameOfIssuer")
        title = row.find("{*}titleOfClass")
        cusip = row.find("{*}cusip")
        val = row.find("{*}value")
        shrs_elem = row.find("{*}shrsOrPrnAmt")

        issuer_name = issuer.text.strip().upper() if issuer is not None and issuer.text else ""
        class_title = title.text.strip().upper() if title is not None and title.text else ""
        cusip_val = cusip.text.strip().upper() if cusip is not None and cusip.text else ""
        value_usd = float(val.text) if val is not None and val.text else 0.0

        shares = 0.0
        if shrs_elem is not None:
            shrs_val = shrs_elem.find("{*}sshPrnamt")
            if shrs_val is not None and shrs_val.text:
                shares = float(shrs_val.text)

        if issuer_name:
            holdings.append(
                {
                    "name_of_issuer": issuer_name,
                    "title_of_class": class_title,
                    "cusip": cusip_val,
                    "value_usd": value_usd,
                    "shares": shares,
                }
            )

    return holdings


async def fetch_latest_13f_metadata(
    cik: str,
    user_agent: str = SEC_EDGAR_USER_AGENT,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Fetches submission metadata for an institutional manager and finds the latest Form 13F-HR."""
    clean_cik = cik.strip().zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{clean_cik}.json"
    headers = {"User-Agent": user_agent}

    client = http_client or httpx.AsyncClient(timeout=12.0)
    try:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            logger.debug("SEC EDGAR submissions query returned HTTP %s for CIK %s", resp.status_code, clean_cik)
            return None

        data = resp.json()
        fund_name = data.get("name", "Unknown Fund")
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])

        # Find newest 13F-HR or 13F-HR/A
        target_idx = None
        for i, f in enumerate(forms):
            if "13F-HR" in f:
                target_idx = i
                break

        if target_idx is None:
            return None

        acc_raw = filings["accessionNumber"][target_idx]
        acc_clean = acc_raw.replace("-", "")
        filing_date = filings.get("filingDate", [])[target_idx]
        primary_doc = filings.get("primaryDocument", [])[target_idx]

        return {
            "cik": clean_cik,
            "fund_name": fund_name,
            "accession_raw": acc_raw,
            "accession_clean": acc_clean,
            "filing_date": filing_date,
            "primary_doc": primary_doc,
        }
    except Exception as e:
        logger.debug("Error fetching SEC 13F metadata for CIK %s: %s", clean_cik, e)
        return None
    finally:
        if http_client is None:
            await client.aclose()


async def get_fund_holdings(
    cik: str,
    user_agent: str = SEC_EDGAR_USER_AGENT,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Retrieves full portfolio holdings from the latest Form 13F-HR filing for a given CIK."""
    meta = await fetch_latest_13f_metadata(cik, user_agent=user_agent, http_client=http_client)
    if not meta:
        return {"fund_name": "Unknown", "holdings": [], "filing_date": None}

    clean_cik_unpadded = str(int(meta["cik"]))
    acc_clean = meta["accession_clean"]
    dir_url = f"https://www.sec.gov/Archives/edgar/data/{clean_cik_unpadded}/{acc_clean}/"
    headers = {"User-Agent": user_agent}

    client = http_client or httpx.AsyncClient(timeout=15.0)
    try:
        dir_resp = await client.get(dir_url, headers=headers)
        if dir_resp.status_code != 200:
            return {"fund_name": meta["fund_name"], "holdings": [], "filing_date": meta["filing_date"]}

        xml_files = re.findall(r"href=[\"\']([^\"\']+\.xml)[\"\']", dir_resp.text, re.IGNORECASE)
        if not xml_files:
            return {"fund_name": meta["fund_name"], "holdings": [], "filing_date": meta["filing_date"]}

        # Locate information table XML file
        infotable = [x for x in xml_files if "infotable" in x.lower() or "table" in x.lower()]
        target_file = infotable[0] if infotable else xml_files[0]

        if target_file.startswith("http"):
            target_url = target_file
        elif target_file.startswith("/"):
            target_url = f"https://www.sec.gov{target_file}"
        else:
            target_url = f"{dir_url}{target_file}"

        xml_resp = await client.get(target_url, headers=headers)
        if xml_resp.status_code != 200:
            return {"fund_name": meta["fund_name"], "holdings": [], "filing_date": meta["filing_date"]}

        holdings = parse_13f_infotable_xml(xml_resp.content)
        return {
            "fund_name": meta["fund_name"],
            "filing_date": meta["filing_date"],
            "holdings": holdings,
        }
    except Exception as e:
        logger.debug("Failed retrieving 13F XML table for CIK %s: %s", cik, e)
        return {"fund_name": meta["fund_name"], "holdings": [], "filing_date": meta["filing_date"]}
    finally:
        if http_client is None:
            await client.aclose()


def match_co_ownership(
    anchor_keywords: list[str],
    candidates: dict[str, str],
    fund_holdings_map: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Calculates institutional co-ownership when a fund holds the anchor asset alongside candidates."""
    anchor_keys = [k.upper() for k in anchor_keywords]
    co_holdings: dict[str, dict[str, Any]] = {}

    for fund_name, holdings in fund_holdings_map.items():
        # Step 1: Check if fund holds the anchor stock
        anchor_held = any(any(k in h.get("name_of_issuer", "") for k in anchor_keys) for h in holdings)
        if not anchor_held:
            continue

        # Step 2: Check which candidate peers this fund also holds
        for sym, keyword in candidates.items():
            kw = keyword.upper()
            cand_matches = [h for h in holdings if kw in h.get("name_of_issuer", "")]
            if cand_matches:
                total_val = sum(m.get("value_usd", 0.0) for m in cand_matches)
                if sym not in co_holdings:
                    co_holdings[sym] = {
                        "symbol": sym,
                        "co_owning_fund_count": 0,
                        "total_co_owned_value_usd": 0.0,
                        "funds": [],
                    }
                co_holdings[sym]["co_owning_fund_count"] += 1
                co_holdings[sym]["total_co_owned_value_usd"] += total_val
                co_holdings[sym]["funds"].append(fund_name)

    return co_holdings
