"""Government fiscal deficits, money creation, sovereign budgets, and contract award tools."""

import asyncio
import csv
import io
from typing import Any

import httpx

from core.config import logger
from core.db import get_supabase_client
from ingest.government_fetchers import (
    BROWSER_USER_AGENT,
    DEFAULT_TIMEOUT,
    FISCAL_DATA_BASE_URL,
    _safe_float,
    _scale_millions,
    fetch_canadabuys_contracts,
    fetch_us_treasury_liquidity,
    fetch_usaspending_contracts,
)

USASPENDING_AGENCIES_URL = (
    "https://api.usaspending.gov/api/v2/references/toptier_agencies/?sort=budget_authority_amount&order=desc"
)
CANADA_BUDGET_CSV_URL = "https://donnees-data.tpsgc-pwgsc.gc.ca/ba1/budgetaires-budgetary/budgetaires-budgetary.csv"
WORLDBANK_BASE_URL = "https://api.worldbank.org/v2/country/USA;CAN;GBR;DEU;FRA;JPN;CHN;IND/indicator"
EUROSTAT_FISCAL_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10dd_edpt1"
    "?geo=EA20&geo=DE&geo=FR&geo=IT&na_item=B9&na_item=GD&sector=S13&unit=PC_GDP&lastTimePeriod=1"
)

TICKER_CONTRACTOR_MAP: dict[str, str] = {
    "PLTR": "PALANTIR",
    "LMT": "LOCKHEED MARTIN",
    "RTX": "RAYTHEON",
    "GD": "GENERAL DYNAMICS",
    "NOC": "NORTHROP GRUMMAN",
    "BA": "BOEING",
    "LHX": "L3HARRIS",
    "HII": "HUNTINGTON INGALLS",
    "LDOS": "LEIDOS",
    "BAH": "BOOZ ALLEN",
    "SAIC": "SCIENCE APPLICATIONS",
    "CACI": "CACI",
    "MSFT": "MICROSOFT",
    "AMZN": "AMAZON",
    "GOOGL": "GOOGLE",
    "GOOG": "GOOGLE",
    "ORCL": "ORACLE",
    "IBM": "INTERNATIONAL BUSINESS MACHINES",
    "CSCO": "CISCO",
    "DELL": "DELL",
    "HPE": "HEWLETT PACKARD",
    "ANDR": "ANDURIL",
    "KTOS": "KRATOS",
    "AVAV": "AEROVIRONMENT",
    "RKLB": "ROCKET LAB",
    "LUNR": "INTUITIVE MACHINES",
    "CAE": "CAE INC",
    "MDA": "MDA SPACE",
    "LLY": "ELI LILLY",
    "PFE": "PFIZER",
    "MRK": "MERCK",
    "JNJ": "JOHNSON & JOHNSON",
    "UNH": "UNITEDHEALTH",
    "MCK": "MCKESSON",
    "CAT": "CATERPILLAR",
    "PWR": "QUANTA SERVICES",
    "URI": "UNITED RENTALS",
    "VMC": "VULCAN MATERIALS",
    "MLM": "MARTIN MARIETTA",
    "FLR": "FLUOR",
    "J": "JACOBS",
    "ACM": "AECOM",
}


def _fmt_usd(val: float | None, prefix: str = "$") -> str:
    if val is None:
        return "N/A"
    sign = "-" if val < 0 else ""
    a = abs(val)
    if a >= 1e12:
        return f"{sign}{prefix}{a / 1e12:.2f}T"
    if a >= 1e9:
        return f"{sign}{prefix}{a / 1e9:.2f}B"
    if a >= 1e6:
        return f"{sign}{prefix}{a / 1e6:.2f}M"
    if a >= 1e3:
        return f"{sign}{prefix}{a / 1e3:.1f}K"
    return f"{sign}{prefix}{a:,.0f}"


async def _get_liquidity_records(limit: int = 14) -> list[dict[str, Any]]:
    try:
        sb = get_supabase_client()
        res = sb.table("gov_macro_liquidity").select("*").order("record_date", desc=True).limit(limit).execute()
        rows = getattr(res, "data", None) or []
        if rows:
            for r in rows:
                if r.get("tga_balance") is not None:
                    r["tga_balance"] = _scale_millions(float(r["tga_balance"]))
            return rows
    except Exception as e:
        logger.debug("Supabase gov_macro_liquidity lookup fell back to live API: %s", e)
    return await fetch_us_treasury_liquidity(days=limit)


async def _fetch_fed_liquidity_snapshot() -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        from core.fred import fetch_fred_series_observations

        m2_res, walcl_res, rrp_res = await asyncio.gather(
            fetch_fred_series_observations("m2", lookback_periods=2),
            fetch_fred_series_observations("fed_balance_sheet", lookback_periods=2),
            fetch_fred_series_observations("reverse_repo", lookback_periods=2),
            return_exceptions=True,
        )
        if isinstance(m2_res, dict) and m2_res.get("latest_value") is not None:
            out["m2_billions"] = float(m2_res["latest_value"])
        if isinstance(walcl_res, dict) and walcl_res.get("latest_value") is not None:
            out["walcl_millions"] = float(walcl_res["latest_value"])
        if isinstance(rrp_res, dict) and rrp_res.get("latest_value") is not None:
            out["rrp_billions"] = float(rrp_res["latest_value"])
    except Exception as e:
        logger.debug("FRED snapshot in government_tools skipped: %s", e)

    try:
        url = f"{FISCAL_DATA_BASE_URL}/v2/accounting/od/avg_interest_rates?page[size]=10&sort=-record_date"
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": BROWSER_USER_AGENT}) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                rates = {}
                for row in resp.json().get("data", []):
                    desc = row.get("security_desc", "")
                    if desc in ("Treasury Bills", "Treasury Notes", "Treasury Bonds", "Total Marketable"):
                        rates.setdefault(desc, _safe_float(row.get("avg_interest_rate_amt")))
                out["avg_rates"] = rates
    except Exception as e:
        logger.debug("Treasury avg interest rates fetch skipped: %s", e)
    return out


async def _fetch_us_budget_categories() -> list[dict[str, Any]]:
    url = f"{FISCAL_DATA_BASE_URL}/v1/accounting/mts/mts_table_9?page[size]=50&sort=-record_date"
    target_cats = {
        "Social Security",
        "Medicare",
        "Net Interest",
        "Health",
        "National Defense",
        "Income Security",
        "Veterans Benefits and Services",
        "Education, Training, Employment, and Social Services",
        "Transportation",
        "General Science, Space, and Technology",
        "Energy",
        "Individual Income Taxes",
        "Corporation Income Taxes",
        "Customs Duties",
    }
    results = []
    seen = set()
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": BROWSER_USER_AGENT}) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                for row in resp.json().get("data", []):
                    desc = (row.get("classification_desc") or "").strip()
                    if desc in target_cats and desc not in seen:
                        seen.add(desc)
                        results.append(
                            {
                                "classification_desc": desc,
                                "record_date": row.get("record_date"),
                                "current_month_rcpt_outly_amt": _safe_float(row.get("current_month_rcpt_outly_amt")),
                                "current_fytd_rcpt_outly_amt": _safe_float(row.get("current_fytd_rcpt_outly_amt")),
                                "prior_fytd_rcpt_outly_amt": _safe_float(row.get("prior_fytd_rcpt_outly_amt")),
                            }
                        )
    except Exception as e:
        logger.warning("Failed to fetch US MTS Table 9 budget categories: %s", e)
    return results


async def _fetch_us_agency_budgets(limit: int = 10) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": BROWSER_USER_AGENT}) as client:
            resp = await client.get(USASPENDING_AGENCIES_URL)
            if resp.status_code == 200:
                return resp.json().get("results", [])[:limit]
    except Exception as e:
        logger.warning("Failed to fetch USAspending top agencies: %s", e)
    return []


async def _fetch_canada_ministry_budgets(limit: int = 8) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT, headers={"User-Agent": BROWSER_USER_AGENT}, follow_redirects=True
        ) as client:
            resp = await client.get(CANADA_BUDGET_CSV_URL)
            if resp.status_code != 200:
                return []
            rows = list(csv.DictReader(io.StringIO(resp.text.lstrip("\ufeff"))))
            if not rows:
                return []
            fy_key = "Fscl-yr_Ex-fin"
            latest_fy = max(r.get(fy_key, "") for r in rows)
            by_min: dict[str, dict[str, float]] = {}
            for r in rows:
                if r.get(fy_key) != latest_fy or "Budgetary" not in (r.get("Auth-type_Type-aut") or ""):
                    continue
                min_name = (r.get("Min-portfolio_Portefeuille-min-eng") or "Other").strip()
                curr = _safe_float(r.get("Net-exp-curr-yr_Dep-nettes-ex-en-cours")) * 1000.0
                prev = _safe_float(r.get("Net-exp-prev-yr_Dep-nettes-ex-prec")) * 1000.0
                slot = by_min.setdefault(min_name, {"curr": 0.0, "prev": 0.0})
                slot["curr"] += curr
                slot["prev"] += prev

            ranked = sorted(by_min.items(), key=lambda x: x[1]["curr"], reverse=True)[:limit]
            out = []
            for min_name, vals in ranked:
                yoy = ((vals["curr"] - vals["prev"]) / vals["prev"] * 100.0) if vals["prev"] > 0 else 0.0
                out.append(
                    {
                        "fiscal_year": latest_fy,
                        "ministry": min_name,
                        "curr_cad": vals["curr"],
                        "prev_cad": vals["prev"],
                        "yoy_pct": yoy,
                    }
                )
            return out
    except Exception as e:
        logger.warning("Failed to fetch Canadian ministry budgets: %s", e)
        return []


async def _fetch_global_sovereign_spending() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"defense": [], "infrastructure_gcf": [], "eurostat_fiscal": []}
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
        for key, ind in (("defense", "MS.MIL.XPND.CD"), ("infrastructure_gcf", "NE.GDI.TOTL.CD")):
            try:
                url = f"{WORLDBANK_BASE_URL}/{ind}?format=json&date=2022:2026&per_page=100"
                resp = await client.get(url)
                if resp.status_code == 200:
                    payload = resp.json()
                    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
                    by_country: dict[str, list[tuple[str, float, str]]] = {}
                    for r in rows or []:
                        if r.get("value") is not None:
                            code = r.get("countryiso3code") or ""
                            cname = (r.get("country") or {}).get("value") or code
                            by_country.setdefault(code, []).append((str(r.get("date")), float(r["value"]), cname))
                    for code, pts in by_country.items():
                        pts.sort(key=lambda x: x[0], reverse=True)
                        yr, val, cname = pts[0]
                        yoy = ((val - pts[1][1]) / pts[1][1] * 100.0) if len(pts) > 1 and pts[1][1] else 0.0
                        out[key].append({"country": cname, "code": code, "year": yr, "val_usd": val, "yoy_pct": yoy})
                    out[key].sort(key=lambda x: x["yoy_pct"], reverse=True)
            except Exception as e:
                logger.debug("World Bank %s fetch skipped: %s", key, e)

        try:
            resp = await client.get(EUROSTAT_FISCAL_URL)
            if resp.status_code == 200:
                d = resp.json()
                vals = d.get("value", {})
                geos = d.get("dimension", {}).get("geo", {}).get("category", {}).get("index", {})
                items = d.get("dimension", {}).get("na_item", {}).get("category", {}).get("index", {})
                times = list(d.get("dimension", {}).get("time", {}).get("category", {}).get("index", {}).keys())
                period = times[0] if times else "Latest"
                num_geos = max(len(geos), 1)
                for g_code, g_idx in geos.items():
                    b9_idx = items.get("B9", 0) * num_geos + g_idx
                    gd_idx = items.get("GD", 1) * num_geos + g_idx
                    out["eurostat_fiscal"].append(
                        {
                            "geo": g_code,
                            "period": period,
                            "deficit_pct_gdp": vals.get(str(b9_idx)),
                            "debt_pct_gdp": vals.get(str(gd_idx)),
                        }
                    )
        except Exception as e:
            logger.debug("Eurostat fiscal fetch skipped: %s", e)
    return out


async def _get_contract_deals(
    country: str = "ALL",
    query: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    country_upper = (country or "ALL").upper()
    try:
        sb = get_supabase_client()
        q = sb.table("gov_contracts").select("*").order("award_amount", desc=True).limit(limit)
        if country_upper in ("US", "CA"):
            q = q.eq("country", country_upper)
        if query:
            q = q.ilike("recipient_name", f"%{query}%")
        res = q.execute()
        contracts = list(getattr(res, "data", None) or [])
    except Exception as e:
        logger.debug("Supabase gov_contracts query fell back to live fetchers: %s", e)

    if len(contracts) < min(limit, 3):
        tasks = []
        if country_upper in ("ALL", "US"):
            tasks.append(fetch_usaspending_contracts(days=90 if query else 14, limit=limit, recipient_query=query))
        if country_upper in ("ALL", "CA") and not query:
            tasks.append(fetch_canadabuys_contracts(limit=limit))
        if tasks:
            fetched_lists = await asyncio.gather(*tasks, return_exceptions=True)
            seen_ids = {c.get("award_id") for c in contracts}
            for lst in fetched_lists:
                if isinstance(lst, list):
                    for item in lst:
                        if item.get("award_id") not in seen_ids:
                            contracts.append(item)
                            seen_ids.add(item.get("award_id"))

    contracts.sort(key=lambda x: _safe_float(x.get("award_amount")), reverse=True)
    return contracts[:limit]


def _format_us_liquidity_section(liq_rows: list[dict[str, Any]], fed_snap: dict[str, Any]) -> list[str]:
    if not liq_rows:
        return []
    latest = liq_rows[0]
    oldest = liq_rows[-1]
    tga_now = _safe_float(latest.get("tga_balance"))
    tga_old = _safe_float(oldest.get("tga_balance"))
    debt_now = _safe_float(latest.get("tot_pub_debt"))
    debt_old = _safe_float(oldest.get("tot_pub_debt"))
    meta = latest.get("raw_metadata") or {}

    tga_delta = tga_now - tga_old if (tga_now and tga_old) else 0.0
    debt_delta = debt_now - debt_old if (debt_now and debt_old) else 0.0
    impulse_label = (
        "LIQUIDITY INJECTION (TGA Drawdown)"
        if tga_delta < 0
        else "LIQUIDITY DRAIN (TGA Refill)"
        if tga_delta > 0
        else "NEUTRAL"
    )

    lines = [
        "",
        f"#### 1. US Treasury Liquidity, Debt Issuance & Money Creation (As of {latest.get('record_date')})",
        f"- **Total Public Debt Outstanding**: {_fmt_usd(debt_now)} "
        f"(Public Held: {_fmt_usd(_safe_float(latest.get('debt_held_public')))} | "
        f"14d Net Issuance: {_fmt_usd(debt_delta)})",
        f"- **Treasury General Account (TGA Cash)**: {_fmt_usd(tga_now)} "
        f"(14d Change: {_fmt_usd(tga_delta)} -> {impulse_label})",
    ]
    if meta.get("tga_deposits") or meta.get("tga_withdrawals"):
        lines.append(
            f"- **Daily Treasury Cash Flows**: Deposits {_fmt_usd(_safe_float(meta.get('tga_deposits')))} | "
            f"Withdrawals {_fmt_usd(_safe_float(meta.get('tga_withdrawals')))}"
        )
    if latest.get("monthly_deficit_surplus") is not None or meta.get("fytd_deficit_surplus") is not None:
        m_dfct = latest.get("monthly_deficit_surplus")
        fytd_dfct = meta.get("fytd_deficit_surplus")
        lines.append(
            f"- **US Federal Deficit**: Latest Month {_fmt_usd(_safe_float(m_dfct) if m_dfct is not None else None)} | "
            f"FYTD Deficit {_fmt_usd(_safe_float(fytd_dfct) if fytd_dfct is not None else None)} "
            f"(FYTD Outlays: {_fmt_usd(_safe_float(meta.get('fytd_outlays')))} vs "
            f"Receipts: {_fmt_usd(_safe_float(meta.get('fytd_receipts')))})"
        )
    rates = (fed_snap or {}).get("avg_rates") or {}
    rate_parts = [f"{k}: {v:.2f}%" for k, v in rates.items() if v]
    if rate_parts:
        lines.append(f"- **Treasury Debt Funding Rates**: {' | '.join(rate_parts)}")
    return lines


def _format_budgets_and_global_section(
    us_budget: list[dict[str, Any]],
    us_agencies: list[dict[str, Any]],
    ca_budget: list[dict[str, Any]],
    global_spend: dict[str, list[dict[str, Any]]],
) -> list[str]:
    lines: list[str] = []
    if us_budget:
        lines.extend(
            [
                "",
                "#### 2. US Federal Budget Outlays & Tax Receipts by Category (MTS Table 9)",
                "| Budget Function / Category | FYTD Amount | Current Month | YoY Change |",
                "| :--- | :---: | :---: | :---: |",
            ]
        )
        us_budget_sorted = sorted(us_budget, key=lambda x: abs(x.get("current_fytd_rcpt_outly_amt", 0.0)), reverse=True)
        for b in us_budget_sorted[:12]:
            fytd = b.get("current_fytd_rcpt_outly_amt", 0.0)
            prev = b.get("prior_fytd_rcpt_outly_amt", 0.0)
            cur_m = b.get("current_month_rcpt_outly_amt", 0.0)
            yoy_str = f"{((fytd - prev) / prev * 100.0):+.1f}%" if prev > 0 else "-"
            lines.append(f"| {b['classification_desc']} | {_fmt_usd(fytd)} | {_fmt_usd(cur_m)} | {yoy_str} |")

    if us_agencies:
        lines.extend(
            [
                "",
                "#### 3. Top US Federal Agencies by Budget Authority (USAspending)",
                "| Agency | Budget Authority | Obligated | Outlays |",
                "| :--- | :---: | :---: | :---: |",
            ]
        )
        for ag in us_agencies[:8]:
            lines.append(
                f"| {ag.get('agency_name')} | {_fmt_usd(_safe_float(ag.get('budget_authority_amount')))} | "
                f"{_fmt_usd(_safe_float(ag.get('obligated_amount')))} | "
                f"{_fmt_usd(_safe_float(ag.get('outlay_amount')))} |"
            )

    if ca_budget:
        fy_label = ca_budget[0].get("fiscal_year", "Latest")
        lines.extend(
            [
                "",
                f"#### 4. Canadian Federal Budget by Ministry (Public Accounts {fy_label})",
                "| Ministry Portfolio | Current FY (CAD) | Prior FY (CAD) | YoY Growth |",
                "| :--- | :---: | :---: | :---: |",
            ]
        )
        for row in ca_budget:
            lines.append(
                f"| {row['ministry']} | {_fmt_usd(row['curr_cad'], 'C$')} | "
                f"{_fmt_usd(row['prev_cad'], 'C$')} | {row['yoy_pct']:+.1f}% |"
            )

    if global_spend:
        def_rows = global_spend.get("defense") or []
        gcf_rows = global_spend.get("infrastructure_gcf") or []
        eu_rows = global_spend.get("eurostat_fiscal") or []
        if def_rows:
            lines.extend(
                [
                    "",
                    "#### 5. Global G7/G20 Defense & Military Spending Surge (World Bank)",
                    "| Country | Defense Spend (USD) | YoY Growth | Year |",
                    "| :--- | :---: | :---: | :---: |",
                ]
            )
            for r in def_rows[:8]:
                lines.append(
                    f"| {r['country']} ({r['code']}) | {_fmt_usd(r['val_usd'])} | {r['yoy_pct']:+.1f}% | {r['year']} |"
                )
        if gcf_rows:
            lines.extend(
                [
                    "",
                    "**Global Gross Capital Formation / Infrastructure Investment YoY**: "
                    + ", ".join(
                        f"{r['country']} {_fmt_usd(r['val_usd'])} ({r['yoy_pct']:+.1f}% YoY)" for r in gcf_rows[:6]
                    ),
                ]
            )
        eu_parts = [
            f"{r['geo']} Deficit {r['deficit_pct_gdp']}% GDP (Debt {r['debt_pct_gdp']}% GDP)"
            for r in eu_rows
            if r.get("deficit_pct_gdp") is not None
        ]
        if eu_parts:
            lines.append(f"**Eurostat Sovereign Fiscal Deficits & Debt**: {' | '.join(eu_parts)}")
    return lines


def _format_contracts_section(contracts: list[dict[str, Any]], search_query: str | None, limit: int) -> list[str]:
    filter_note = f" (Filtered by '{search_query}')" if search_query else ""
    lines = ["", f"#### 6. Recent Federal Contract Deals & Procurement Winners{filter_note}"]
    if not contracts:
        lines.append("No matching government contract awards found for the specified filter.")
        return lines

    lines.extend(
        [
            "| Date | Country | Recipient / Company | Award Amount | Awarding Agency | Description |",
            "| :--- | :---: | :--- | :---: | :--- | :--- |",
        ]
    )
    for c in contracts[:limit]:
        prefix = "C$" if c.get("currency") == "CAD" else "$"
        amt = _fmt_usd(_safe_float(c.get("award_amount")), prefix=prefix)
        desc = (c.get("description") or "")[:65].replace("\n", " ").replace("|", "/")
        lines.append(
            f"| {c.get('award_date')} | {c.get('country', 'US')} | {c.get('recipient_name')} | "
            f"{amt} | {c.get('agency_name')} | {desc} |"
        )
    return lines


async def execute_get_government_fiscal_and_spending_tool(
    country: str = "ALL",
    ticker: str | None = None,
    recipient: str | None = None,
    limit: int = 10,
) -> str:
    """Retrieve government money creation, fiscal deficits, ministry/agency budgets, and contract deals."""
    country_norm = (country or "ALL").upper()
    search_query = recipient
    if not search_query and ticker:
        t_clean = ticker.strip().upper()
        search_query = TICKER_CONTRACTOR_MAP.get(t_clean, t_clean)

    liq_task = _get_liquidity_records(limit=14)
    fed_task = _fetch_fed_liquidity_snapshot()
    us_bud_task = _fetch_us_budget_categories() if country_norm in ("ALL", "US") else asyncio.sleep(0, result=[])
    us_ag_task = _fetch_us_agency_budgets(limit=8) if country_norm in ("ALL", "US") else asyncio.sleep(0, result=[])
    ca_bud_task = (
        _fetch_canada_ministry_budgets(limit=8) if country_norm in ("ALL", "CA") else asyncio.sleep(0, result=[])
    )
    global_task = (
        _fetch_global_sovereign_spending()
        if country_norm in ("ALL", "EU", "INTL", "GLOBAL")
        else asyncio.sleep(0, result={})
    )
    contracts_task = _get_contract_deals(country=country_norm, query=search_query, limit=limit)

    liq_rows, fed_snap, us_budget, us_agencies, ca_budget, global_spend, contracts = await asyncio.gather(
        liq_task, fed_task, us_bud_task, us_ag_task, ca_bud_task, global_task, contracts_task
    )

    lines = ["### 🏛️ Sovereign Money Creation, Fiscal Deficits, Budgets & Contract Deals"]
    lines.extend(_format_us_liquidity_section(liq_rows, fed_snap))
    lines.extend(_format_budgets_and_global_section(us_budget, us_agencies, ca_budget, global_spend))
    lines.extend(_format_contracts_section(contracts, search_query, limit))
    return "\n".join(lines)
