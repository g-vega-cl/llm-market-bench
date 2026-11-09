"""Fetchers and database persistence for government liquidity, debt, and contract awards.

Integrates:
- US Fiscal Data API (Daily Treasury Statement TGA cash, National Debt, Deficits)
- USAspending API (US Federal contract awards & procurement)
- CanadaBuys / Open Canada (Canadian federal contracts and tenders)
"""

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from core.config import logger
from core.db import get_supabase_client

FISCAL_DATA_BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
USASPENDING_AWARDS_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
CANADABUYS_CSV_URL = "https://canadabuys.canada.ca/opendata/pub/contractHistoryComplete-contratsOctroyesComplet.csv"

DEFAULT_TIMEOUT = 15.0
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "" or str(val).lower() == "null":
        return default
    try:
        clean = str(val).replace("$", "").replace(",", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return default


def _scale_millions(val: float) -> float:
    """Scale DTS values reported in millions of dollars to exact dollars."""
    if 0 < abs(val) < 1e9:
        return val * 1_000_000.0
    return val


def _parse_dts_cash(rows: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> None:
    for row in rows:
        r_date = row.get("record_date")
        acc_type = row.get("account_type", "")
        if not r_date:
            continue
        rec = records.setdefault(r_date, {"record_date": r_date, "raw_metadata": {}})
        meta = rec.setdefault("raw_metadata", {})

        raw_val = row.get("open_today_bal")
        if raw_val is None or str(raw_val).lower() == "null":
            raw_val = row.get("close_today_bal")
        val = _scale_millions(_safe_float(raw_val))

        is_closing_tga = "Closing Balance" in acc_type and "Treasury General Account" in acc_type
        is_fallback_tga = ("Treasury General Account" in acc_type or "Opening Balance" in acc_type) and not rec.get(
            "tga_balance"
        )
        if is_closing_tga or is_fallback_tga:
            rec["tga_balance"] = val
        elif "Total TGA Deposits" in acc_type:
            meta["tga_deposits"] = val
        elif "Total TGA Withdrawals" in acc_type:
            meta["tga_withdrawals"] = val


def _parse_debt_to_penny(rows: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> None:
    for row in rows:
        r_date = row.get("record_date")
        if not r_date:
            continue
        rec = records.setdefault(r_date, {"record_date": r_date, "raw_metadata": {}})
        rec["tot_pub_debt"] = _safe_float(row.get("tot_pub_debt_out_amt"))
        rec["debt_held_public"] = _safe_float(row.get("debt_held_public_amt"))
        rec["intragov_holdings"] = _safe_float(row.get("intragov_hold_amt"))


def _parse_mts_deficit(rows: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> None:
    latest_month_dfct: float | None = None
    latest_month_name: str | None = None
    fytd_meta: dict[str, Any] = {}

    for row in rows:
        r_date = row.get("record_date")
        dfct = row.get("current_month_dfct_sur_amt")
        if not r_date or dfct is None or str(dfct).lower() == "null":
            continue

        rec = records.setdefault(r_date, {"record_date": r_date, "raw_metadata": {}})
        meta = rec.setdefault("raw_metadata", {})
        rec_type = str(row.get("record_type_cd") or "")
        desc = str(row.get("classification_desc") or "")
        dfct_val = _safe_float(dfct)

        if rec_type == "SL" or "Year-to-Date" in desc:
            meta["fytd_deficit_surplus"] = dfct_val
            if row.get("current_month_rcpt_amt") is not None:
                meta["fytd_receipts"] = _safe_float(row.get("current_month_rcpt_amt"))
            if row.get("current_month_outly_amt") is not None:
                meta["fytd_outlays"] = _safe_float(row.get("current_month_outly_amt"))
            if not fytd_meta:
                fytd_meta = dict(meta)
        else:
            if rec.get("monthly_deficit_surplus") is None:
                rec["monthly_deficit_surplus"] = dfct_val
                if desc:
                    meta["mts_month"] = desc
            if latest_month_dfct is None:
                latest_month_dfct = dfct_val
                latest_month_name = desc

    # Attach latest monthly deficit and FYTD summary to the most recent daily record if not already set
    if records and (latest_month_dfct is not None or fytd_meta):
        latest_date = max(records.keys())
        latest_rec = records[latest_date]
        if latest_rec.get("monthly_deficit_surplus") is None and latest_month_dfct is not None:
            latest_rec["monthly_deficit_surplus"] = latest_month_dfct
        latest_meta = latest_rec.setdefault("raw_metadata", {})
        if latest_month_name and "mts_month" not in latest_meta:
            latest_meta["mts_month"] = latest_month_name
        for k, v in fytd_meta.items():
            latest_meta.setdefault(k, v)


async def fetch_us_treasury_liquidity(days: int = 14) -> list[dict[str, Any]]:
    """Fetch daily Treasury General Account balance, national debt, and recent deficit."""
    records_by_date: dict[str, dict[str, Any]] = {}

    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
        # 1. Daily Treasury Statement - Operating Cash (TGA)
        try:
            url_cash = (
                f"{FISCAL_DATA_BASE_URL}/v1/accounting/dts/operating_cash_balance"
                f"?page[size]={days * 4}&sort=-record_date"
            )
            resp = await client.get(url_cash)
            if resp.status_code == 200:
                _parse_dts_cash(resp.json().get("data", []), records_by_date)
        except Exception as e:
            logger.warning("Failed to fetch DTS operating cash balance: %s", e)

        # 2. Debt to Penny (Total Public Debt Outstanding)
        try:
            url_debt = f"{FISCAL_DATA_BASE_URL}/v2/accounting/od/debt_to_penny?page[size]={days}&sort=-record_date"
            resp = await client.get(url_debt)
            if resp.status_code == 200:
                _parse_debt_to_penny(resp.json().get("data", []), records_by_date)
        except Exception as e:
            logger.warning("Failed to fetch Debt to the Penny: %s", e)

        # 3. Monthly Treasury Statement (Deficit / Surplus)
        try:
            url_mts = f"{FISCAL_DATA_BASE_URL}/v1/accounting/mts/mts_table_1?page[size]=15&sort=-record_date"
            resp = await client.get(url_mts)
            if resp.status_code == 200:
                _parse_mts_deficit(resp.json().get("data", []), records_by_date)
        except Exception as e:
            logger.warning("Failed to fetch MTS deficit table: %s", e)

    results = []
    for rec in records_by_date.values():
        rec.setdefault("tga_balance", None)
        rec.setdefault("tot_pub_debt", None)
        rec.setdefault("debt_held_public", None)
        rec.setdefault("intragov_holdings", None)
        rec.setdefault("monthly_deficit_surplus", None)
        rec.setdefault("raw_metadata", {})
        results.append(rec)

    results.sort(key=lambda x: x["record_date"], reverse=True)
    return results


async def upsert_gov_macro_liquidity(records: list[dict[str, Any]]) -> int:
    """Upsert macro liquidity and debt records into Supabase."""
    if not records:
        return 0
    try:
        sb = get_supabase_client()
        res = sb.table("gov_macro_liquidity").upsert(records, on_conflict="record_date").execute()
        data = getattr(res, "data", None)
        return len(data) if data else len(records)
    except Exception as e:
        logger.error("Failed to upsert gov_macro_liquidity records: %s", e)
        return 0


async def fetch_usaspending_contracts(
    days: int = 14,
    limit: int = 50,
    recipient_query: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent US federal contract awards from USAspending, sorted by largest Award Amount."""
    end_dt = datetime.now(UTC)
    start_dt = end_dt - timedelta(days=days)

    filters: dict[str, Any] = {
        "time_period": [
            {
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
            }
        ],
        "award_type_codes": ["A", "B", "C", "D"],
    }
    if recipient_query:
        filters["recipient_search_text"] = [recipient_query.strip()]

    payload = {
        "filters": filters,
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Description",
            "Action Date",
            "Awarding Agency",
            "Contract Number",
        ],
        "sort": "Award Amount",
        "order": "desc",
        "limit": limit,
        "page": 1,
    }

    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"}
    contracts = []

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
            resp = await client.post(USASPENDING_AWARDS_URL, json=payload)
            if resp.status_code == 200:
                raw_results = resp.json().get("results", [])
                for item in raw_results:
                    award_id = str(item.get("Award ID") or item.get("internal_id") or "")
                    recip = (item.get("Recipient Name") or "").strip()
                    amount = _safe_float(item.get("Award Amount"))
                    award_date = (item.get("Action Date") or end_dt.strftime("%Y-%m-%d"))[:10]

                    if not award_id or not recip:
                        continue

                    contracts.append(
                        {
                            "country": "US",
                            "award_id": award_id,
                            "recipient_name": recip,
                            "award_amount": amount,
                            "currency": "USD",
                            "description": item.get("Description") or "",
                            "agency_name": item.get("Awarding Agency") or "U.S. Federal Government",
                            "award_date": award_date,
                            "contract_number": item.get("Contract Number") or award_id,
                            "source_url": (
                                f"https://www.usaspending.gov/award/{item.get('generated_internal_id', '')}"
                                if item.get("generated_internal_id")
                                else "https://www.usaspending.gov"
                            ),
                            "raw_metadata": {"internal_id": item.get("internal_id")},
                        }
                    )
    except Exception as e:
        logger.warning("Failed to fetch USAspending contracts: %s", e)

    return contracts


def parse_canadabuys_csv(content: str, limit: int = 50) -> list[dict[str, Any]]:
    """Parse CanadaBuys contract history CSV text into structured records."""
    contracts = []
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        if len(contracts) >= limit:
            break

        contract_no = (
            row.get("contractNumber-numeroContrat") or row.get("referenceNumber-numeroReference") or ""
        ).strip()
        recip = (
            row.get("supplierStandardizedName-nomNormaliseFournisseur-eng")
            or row.get("supplierStandardizedName-nomNormaliseFournisseur")
            or row.get("supplierLegalName-nomLegalFournisseur-eng")
            or row.get("supplierLegalName-nomLegalFournisseur")
            or row.get("supplierOperatingName-nomCommercialFournisseur-eng")
            or row.get("supplierOperatingName-nomCommercialFournisseur")
            or ""
        ).strip()
        val = _safe_float(
            row.get("contractAmount-montantContrat")
            or row.get("totalContractValue-valeurTotaleContrat")
            or row.get("contractValue-valeurContrat")
        )
        award_date = (
            row.get("contractAwardDate-dateAttributionContrat")
            or row.get("publicationDate-datePublication")
            or today_str
        )[:10]
        desc = (
            row.get("title-titre-eng")
            or row.get("gsinDescription-nibsDescription-eng")
            or row.get("description-description-eng")
            or row.get("title-titre-fra")
            or ""
        ).strip()
        buyer = (
            row.get("contractingEntityName-nomEntitContractante-eng")
            or row.get("endUserEntitiesName-nomEntitesUtilisateurFinal-eng")
            or row.get("buyerOrganizationName-nomOrganisationAcheteur-eng")
            or "Government of Canada"
        ).strip()

        if not contract_no or not recip:
            continue

        contracts.append(
            {
                "country": "CA",
                "award_id": contract_no,
                "recipient_name": recip,
                "award_amount": val,
                "currency": "CAD",
                "description": desc,
                "agency_name": buyer,
                "award_date": award_date,
                "contract_number": contract_no,
                "source_url": "https://canadabuys.canada.ca",
                "raw_metadata": {"procurementNumber": row.get("procurementNumber-numeroApprovisionnement")},
            }
        )

    return contracts


async def fetch_canadabuys_contracts(limit: int = 50, max_bytes: int = 131072) -> list[dict[str, Any]]:
    """Fetch recent Canadian federal contract awards from CanadaBuys using chunked streaming."""
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "text/csv,text/plain,*/*"}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers, follow_redirects=True) as client:
            if isinstance(client, httpx.AsyncClient):
                chunks: list[bytes] = []
                total = 0
                async with client.stream("GET", CANADABUYS_CSV_URL) as resp:
                    if resp.status_code != 200:
                        logger.warning("CanadaBuys returned non-200 status: %s", resp.status_code)
                        return []
                    async for chunk in resp.aiter_bytes():
                        chunks.append(chunk)
                        total += len(chunk)
                        if total >= max_bytes:
                            break
                raw_text = b"".join(chunks).decode("utf-8", errors="ignore")
                # Trim incomplete trailing line
                if "\n" in raw_text:
                    raw_text = raw_text.rsplit("\n", 1)[0]
                return parse_canadabuys_csv(raw_text, limit=limit)

            resp = await client.get(CANADABUYS_CSV_URL)
            if resp.status_code == 200:
                return parse_canadabuys_csv(resp.text, limit=limit)
            logger.warning("CanadaBuys returned non-200 status: %s", resp.status_code)
    except Exception as e:
        logger.warning("Failed to fetch CanadaBuys contracts: %s", e)

    return []


async def upsert_gov_contracts(contracts: list[dict[str, Any]]) -> int:
    """Upsert federal contract awards into Supabase."""
    if not contracts:
        return 0
    try:
        sb = get_supabase_client()
        res = (
            sb.table("gov_contracts")
            .upsert(
                contracts,
                on_conflict="country,award_id,recipient_name,award_date",
            )
            .execute()
        )
        data = getattr(res, "data", None)
        return len(data) if data else len(contracts)
    except Exception as e:
        logger.error("Failed to upsert gov_contracts: %s", e)
        return 0
