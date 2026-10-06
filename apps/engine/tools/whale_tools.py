"""Tool handlers for Institutional Whale Holdings (Schedule 13D/13G and Form 13F)."""

import httpx

from analysis.sec_13f_client import DEFAULT_THEMATIC_FUNDS, get_fund_holdings
from core.config import FMP_API_KEY, logger

FMP_STABLE_URL = "https://financialmodelingprep.com/stable"


async def fetch_beneficial_ownership_from_fmp(symbol: str) -> list[dict]:
    """Fetch Schedule 13D/13G >5% beneficial ownership disclosures from FMP."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing, skipping beneficial ownership fetch.")
        return []

    url = f"{FMP_STABLE_URL}/acquisition-of-beneficial-ownership"
    params = {"symbol": symbol.upper(), "apikey": FMP_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("FMP beneficial ownership returned HTTP %d for %s", resp.status_code, symbol)
                return []

            data = resp.json()
            if not isinstance(data, list):
                return []
            return data
    except Exception as e:
        logger.warning("Failed to fetch beneficial ownership from FMP: %s", e)
        return []


def format_beneficial_ownership_markdown(filings: list[dict], symbol: str, limit: int = 15) -> str:
    """Format Schedule 13D/13G institutional blockholders as Markdown table."""
    if not filings:
        return f"No Schedule 13D/13G whale or institutional blockholder filings found for {symbol.upper()}."

    deduped = {}
    for f in filings:
        name = f.get("nameOfReportingPerson") or "Unknown"
        if name not in deduped:
            deduped[name] = f

    whales = list(deduped.values())[:limit]
    total_pct = sum(float(w.get("percentOfClass") or 0.0) for w in whales)

    lines = [
        f"### Institutional Whale & Blockholder Holdings (Schedule 13D/13G): {symbol.upper()}",
        f"Top Tracked Whale Block: {len(whales)} major filers representing approx {total_pct:.1f}% ownership",
        "",
        "| Whale / Institution | Type | % Ownership | Shares Beneficially Owned | Filing Date |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for w in whales:
        name = w.get("nameOfReportingPerson", "Unknown")
        rpt_type = w.get("typeOfReportingPerson", "-")
        type_desc = {
            "IA": "Investment Advisor (Fund)",
            "HC": "Holding Company",
            "CO": "Corporation",
            "IN": "Individual Investor",
            "BK": "Bank",
            "EP": "Employee Benefit Plan",
        }.get(rpt_type, rpt_type)

        pct = float(w.get("percentOfClass") or 0.0)
        pct_str = f"{pct:.2f}%"
        try:
            shares = int(float(w.get("amountBeneficiallyOwned") or 0))
            shares_str = f"{shares:,d}"
        except (ValueError, TypeError):
            shares_str = str(w.get("amountBeneficiallyOwned") or "-")

        f_date = w.get("filingDate", "")
        lines.append(f"| {name} | {type_desc} | {pct_str} | {shares_str} | {f_date} |")

    return "\n".join(lines)


def format_fund_holdings_markdown(fund_name: str, holdings_info: dict, limit: int = 15) -> str:
    """Format 13F portfolio holdings for a specific whale fund."""
    holdings = holdings_info.get("holdings", [])
    filing_date = holdings_info.get("filing_date") or "Latest Filing"
    canonical_name = holdings_info.get("fund_name") or fund_name

    if not holdings:
        return f"No Form 13F holdings found for whale fund '{fund_name}'."

    sorted_holdings = sorted(holdings, key=lambda x: float(x.get("value_usd", 0.0)), reverse=True)
    total_aum = sum(float(x.get("value_usd", 0.0)) for x in holdings)

    lines = [
        f"### Form 13F Portfolio: {canonical_name} (Filed: {filing_date})",
        f"Total Tracked Equity AUM: ${total_aum:,.0f} across {len(holdings)} positions",
        "",
        "| Rank | Issuer / Company | Class | Value ($) | Shares Held | Portfolio % |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for i, h in enumerate(sorted_holdings[:limit], 1):
        issuer = h.get("name_of_issuer", "Unknown")
        cls_title = h.get("title_of_class", "COM")
        val = float(h.get("value_usd", 0.0))
        shares = float(h.get("shares", 0.0))
        pct = (val / total_aum * 100.0) if total_aum > 0 else 0.0

        val_str = f"${val:,.0f}"
        shrs_str = f"{int(shares):,d}" if shares else "-"
        lines.append(f"| #{i} | {issuer} | {cls_title} | {val_str} | {shrs_str} | {pct:.2f}% |")

    return "\n".join(lines)


async def handle_get_whale_holdings(
    ticker: str | None = None,
    fund_name: str | None = None,
    limit: int = 15,
) -> str:
    """Entry point for retrieving institutional whale ownership data."""
    if not ticker and not fund_name:
        return (
            "Please provide either a 'ticker' (to see top institutional/whale blockholders for a stock) "
            "or a 'fund_name' (e.g. 'BERKSHIRE_HATHAWAY', 'COATUE', 'APPALOOSA') to inspect a fund's 13F portfolio."
        )

    sections = []

    # 1. If ticker is requested, retrieve Schedule 13D/13G whale blockholders
    if ticker:
        filings = await fetch_beneficial_ownership_from_fmp(ticker.strip().upper())
        sec_md = format_beneficial_ownership_markdown(filings, ticker.strip().upper(), limit=limit)
        sections.append(sec_md)

    # 2. If fund_name is requested, retrieve 13F holdings
    if fund_name:
        clean_fund = fund_name.strip().upper().replace(" ", "_")
        cik = DEFAULT_THEMATIC_FUNDS.get(clean_fund)
        if not cik:
            # Check partial match in DEFAULT_THEMATIC_FUNDS
            for k, v in DEFAULT_THEMATIC_FUNDS.items():
                if clean_fund in k or k in clean_fund:
                    cik = v
                    clean_fund = k
                    break

        if cik:
            holdings_info = await get_fund_holdings(cik)
            fund_md = format_fund_holdings_markdown(clean_fund, holdings_info, limit=limit)
            sections.append(fund_md)
        else:
            known_funds = ", ".join(DEFAULT_THEMATIC_FUNDS.keys())
            sections.append(
                f"Whale fund '{fund_name}' not recognized in curated funds list. Available curated funds: {known_funds}."
            )

    return "\n\n".join(sections)


async def execute_get_whale_holdings_tool(
    ticker: str | None = None,
    fund_name: str | None = None,
    limit: int = 15,
) -> str:
    """Executes the get_whale_holdings tool."""
    return await handle_get_whale_holdings(
        ticker=ticker,
        fund_name=fund_name,
        limit=limit,
    )
