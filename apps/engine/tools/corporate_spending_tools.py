"""Corporate capital allocation, CapEx, R&D, buybacks, M&A, and government contract receipts tool."""

import asyncio
from typing import Any

import httpx

from core.config import FMP_API_KEY, logger
from ingest.government_fetchers import _safe_float
from tools.government_tools import TICKER_CONTRACTOR_MAP, _fmt_usd, _get_contract_deals

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
FMP_TIMEOUT = 15.0
DEFAULT_HYPERSCALER_BASKET = ["MSFT", "AMZN", "GOOGL", "META", "NVDA"]


async def _fetch_ticker_spending_statements(
    ticker: str,
    period: str = "quarter",
    limit: int = 5,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch cash-flow statement, income statement, and annual key-metrics from FMP."""
    if not FMP_API_KEY:
        return [], [], []

    sym = ticker.strip().upper()
    eff_period = "annual" if period == "annual" else "quarter"
    fetch_limit = max(limit, 5 if eff_period == "quarter" else 3)

    async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
        cf_task = client.get(
            f"{FMP_BASE_URL}/cash-flow-statement",
            params={"symbol": sym, "period": eff_period, "limit": fetch_limit, "apikey": FMP_API_KEY},
        )
        inc_task = client.get(
            f"{FMP_BASE_URL}/income-statement",
            params={"symbol": sym, "period": eff_period, "limit": fetch_limit, "apikey": FMP_API_KEY},
        )
        km_task = client.get(
            f"{FMP_BASE_URL}/key-metrics",
            params={"symbol": sym, "period": "annual", "limit": 2, "apikey": FMP_API_KEY},
        )
        resps = await asyncio.gather(cf_task, inc_task, km_task, return_exceptions=True)

    out: list[list[dict[str, Any]]] = [[], [], []]
    for idx, r in enumerate(resps):
        if isinstance(r, httpx.Response) and r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                out[idx] = data
    return out[0], out[1], out[2]


async def _fetch_recent_ma_deals(ticker: str | None = None, limit: int = 15) -> list[dict[str, Any]]:
    """Fetch latest M&A announcements from FMP /stable/mergers-acquisitions-latest."""
    if not FMP_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
            resp = await client.get(
                f"{FMP_BASE_URL}/mergers-acquisitions-latest",
                params={"page": 0, "limit": 30, "apikey": FMP_API_KEY},
            )
            if resp.status_code == 200:
                rows = resp.json()
                if not isinstance(rows, list):
                    return []
                if ticker:
                    sym = ticker.strip().upper()
                    matched = [
                        r
                        for r in rows
                        if (r.get("symbol") or "").upper() == sym or (r.get("targetedSymbol") or "").upper() == sym
                    ]
                    if matched:
                        return matched[:limit]
                return rows[: min(limit, 5)]
    except Exception as e:
        logger.debug("FMP M&A latest fetch skipped: %s", e)
    return []


async def _fetch_company_gov_contracts(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch government contract awards for a ticker."""
    sym = ticker.strip().upper()
    query = TICKER_CONTRACTOR_MAP.get(sym, sym)
    return await _get_contract_deals(country="ALL", query=query, limit=limit)


def _compute_period_row(cf: dict[str, Any], inc: dict[str, Any]) -> dict[str, Any]:
    date_str = cf.get("date") or inc.get("date") or "N/A"
    period_label = (
        f"{cf.get('period') or inc.get('period') or ''} {cf.get('fiscalYear') or inc.get('fiscalYear') or ''}".strip()
    )
    capex = abs(_safe_float(cf.get("capitalExpenditure")))
    ocf = _safe_float(cf.get("operatingCashFlow"))
    fcf = _safe_float(cf.get("freeCashFlow"))
    buybacks = abs(_safe_float(cf.get("commonStockRepurchased")))
    divs = abs(_safe_float(cf.get("commonDividendsPaid") or cf.get("netDividendsPaid")))
    acq = abs(_safe_float(cf.get("acquisitionsNet")))
    rev = _safe_float(inc.get("revenue"))
    rnd = _safe_float(inc.get("researchAndDevelopmentExpenses"))
    sga = _safe_float(inc.get("sellingGeneralAndAdministrativeExpenses"))

    return {
        "date": date_str,
        "label": period_label or date_str,
        "capex": capex,
        "ocf": ocf,
        "fcf": fcf,
        "buybacks": buybacks,
        "dividends": divs,
        "acquisitions": acq,
        "revenue": rev,
        "rnd": rnd,
        "sga": sga,
        "capex_to_rev_pct": (capex / rev * 100.0) if rev > 0 else 0.0,
        "capex_to_ocf_pct": (capex / ocf * 100.0) if ocf > 0 else 0.0,
        "rnd_to_rev_pct": (rnd / rev * 100.0) if rev > 0 else 0.0,
    }


def _find_yoy_comparator(rows: list[dict[str, Any]], period: str) -> dict[str, Any] | None:
    if len(rows) < 2:
        return None
    if period == "quarter" and len(rows) >= 5:
        return rows[4]
    return rows[-1]


async def _format_single_ticker_spending(ticker: str, period: str, limit: int) -> str:
    sym = ticker.strip().upper()
    cf_list, inc_list, km_list = await _fetch_ticker_spending_statements(sym, period=period, limit=max(limit, 5))
    ma_deals, gov_contracts = await asyncio.gather(
        _fetch_recent_ma_deals(sym, limit=5),
        _fetch_company_gov_contracts(sym, limit=5),
    )

    if not cf_list and not inc_list:
        return f"No corporate spending or financial statement data available for {sym}."

    inc_by_date = {r.get("date"): r for r in inc_list if r.get("date")}
    parsed_rows = []
    for idx, cf in enumerate(cf_list):
        inc = inc_by_date.get(cf.get("date")) or (inc_list[idx] if idx < len(inc_list) else {})
        parsed_rows.append(_compute_period_row(cf, inc))

    latest = parsed_rows[0]
    comp = _find_yoy_comparator(parsed_rows, period)
    capex_yoy = ((latest["capex"] - comp["capex"]) / comp["capex"] * 100.0) if (comp and comp["capex"] > 0) else None
    rnd_yoy = ((latest["rnd"] - comp["rnd"]) / comp["rnd"] * 100.0) if (comp and comp["rnd"] > 0) else None

    roic_val = km_list[0].get("returnOnInvestedCapital") if km_list else None
    roic_str = f"{float(roic_val) * 100:.2f}%" if roic_val is not None else "N/A"
    capex_yoy_str = f" ({capex_yoy:+.1f}% vs prior comparator)" if capex_yoy is not None else ""
    rnd_yoy_str = f" ({rnd_yoy:+.1f}% vs prior comparator)" if rnd_yoy is not None else ""

    lines = [
        f"### 🏗️ Corporate Spending, CapEx & Capital Allocation Profile: {sym}",
        f"- **Latest Period ({latest['label']} / {latest['date']})**: Revenue {_fmt_usd(latest['revenue'])} | "
        f"Operating Cash Flow {_fmt_usd(latest['ocf'])} | Free Cash Flow {_fmt_usd(latest['fcf'])}",
        f"- **Capital Expenditure (CapEx)**: {_fmt_usd(latest['capex'])}{capex_yoy_str} "
        f"({latest['capex_to_rev_pct']:.1f}% of Revenue | {latest['capex_to_ocf_pct']:.1f}% of OCF)",
        f"- **R&D Investment**: {_fmt_usd(latest['rnd'])}{rnd_yoy_str} ({latest['rnd_to_rev_pct']:.1f}% of Revenue) | "
        f"**SG&A**: {_fmt_usd(latest['sga'])}",
        f"- **Shareholder Returns & M&A**: Buybacks {_fmt_usd(latest['buybacks'])} | "
        f"Dividends {_fmt_usd(latest['dividends'])} | Cash Acquisitions {_fmt_usd(latest['acquisitions'])} | "
        f"Annual ROIC: {roic_str}",
        "",
        "#### Multi-Period Corporate Spending History",
        "| Period (Date) | CapEx | CapEx/Rev | CapEx/OCF | R&D | R&D/Rev | Buybacks | M&A Cash | Free Cash Flow |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for row in parsed_rows[:limit]:
        lines.append(
            f"| {row['label']} ({row['date']}) | {_fmt_usd(row['capex'])} | {row['capex_to_rev_pct']:.1f}% | "
            f"{row['capex_to_ocf_pct']:.1f}% | {_fmt_usd(row['rnd'])} | {row['rnd_to_rev_pct']:.1f}% | "
            f"{_fmt_usd(row['buybacks'])} | {_fmt_usd(row['acquisitions'])} | {_fmt_usd(row['fcf'])} |"
        )

    if ma_deals:
        lines.extend(["", "#### Recent M&A Filings (FMP)"])
        for d in ma_deals[:4]:
            lines.append(
                f"- **{d.get('transactionDate', 'N/A')}**: {d.get('companyName')} ({d.get('symbol')}) -> "
                f"Target: **{d.get('targetedCompanyName')}**"
            )

    if gov_contracts:
        lines.extend(["", f"#### Matched Federal Government Contract Awards for {sym}"])
        for c in gov_contracts[:5]:
            prefix = "C$" if c.get("currency") == "CAD" else "$"
            lines.append(
                f"- **{c.get('award_date')}** ({c.get('country', 'US')}): **{_fmt_usd(_safe_float(c.get('award_amount')), prefix)}** "
                f"from {c.get('agency_name')} to `{c.get('recipient_name')}` ({(c.get('description') or '')[:60]})"
            )

    return "\n".join(lines)


async def _format_basket_spending(tickers: list[str], period: str) -> str:
    clean_tickers = [t.strip().upper() for t in tickers if t and t.strip()][:8]
    tasks = [_fetch_ticker_spending_statements(t, period=period, limit=5) for t in clean_tickers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary_rows = []
    for sym, res in zip(clean_tickers, results, strict=False):
        if not isinstance(res, tuple) or not res[0]:
            continue
        cf_list, inc_list, km_list = res
        inc_by_date = {r.get("date"): r for r in inc_list if r.get("date")}
        parsed = [
            _compute_period_row(cf, inc_by_date.get(cf.get("date")) or (inc_list[i] if i < len(inc_list) else {}))
            for i, cf in enumerate(cf_list)
        ]
        latest = parsed[0]
        comp = _find_yoy_comparator(parsed, period)
        capex_yoy = ((latest["capex"] - comp["capex"]) / comp["capex"] * 100.0) if (comp and comp["capex"] > 0) else 0.0
        roic = (
            float(km_list[0]["returnOnInvestedCapital"]) * 100.0
            if (km_list and km_list[0].get("returnOnInvestedCapital") is not None)
            else None
        )
        summary_rows.append(
            {
                "symbol": sym,
                "date": latest["date"],
                "capex": latest["capex"],
                "capex_yoy": capex_yoy,
                "capex_rev": latest["capex_to_rev_pct"],
                "capex_ocf": latest["capex_to_ocf_pct"],
                "rnd": latest["rnd"],
                "rnd_rev": latest["rnd_to_rev_pct"],
                "buybacks": latest["buybacks"],
                "fcf": latest["fcf"],
                "roic": roic,
            }
        )

    if not summary_rows:
        return "No corporate spending data available for the requested basket."

    summary_rows.sort(key=lambda x: x["capex"], reverse=True)
    tot_capex = sum(r["capex"] for r in summary_rows)
    tot_rnd = sum(r["rnd"] for r in summary_rows)

    lines = [
        f"### 🏗️ Corporate CapEx, R&D & Capital Allocation Basket ({', '.join(r['symbol'] for r in summary_rows)})",
        f"- **Aggregate Basket Period CapEx**: {_fmt_usd(tot_capex)} | **Aggregate Period R&D**: {_fmt_usd(tot_rnd)}",
        "",
        "| Ticker | Latest Date | CapEx | CapEx YoY | CapEx/Rev | CapEx/OCF | R&D | R&D/Rev | Buybacks | FCF | ROIC |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for r in summary_rows:
        roic_str = f"{r['roic']:.1f}%" if r["roic"] is not None else "N/A"
        lines.append(
            f"| **{r['symbol']}** | {r['date']} | {_fmt_usd(r['capex'])} | {r['capex_yoy']:+.1f}% | "
            f"{r['capex_rev']:.1f}% | {r['capex_ocf']:.1f}% | {_fmt_usd(r['rnd'])} | {r['rnd_rev']:.1f}% | "
            f"{_fmt_usd(r['buybacks'])} | {_fmt_usd(r['fcf'])} | {roic_str} |"
        )
    return "\n".join(lines)


async def execute_get_corporate_spending_tool(
    ticker: str | None = None,
    tickers: list[str] | None = None,
    period: str = "quarter",
    limit: int = 4,
) -> str:
    """Retrieve corporate CapEx, R&D, SG&A, buybacks, M&A activity, and federal contract awards."""
    try:
        if ticker and ticker.strip():
            return await _format_single_ticker_spending(ticker=ticker, period=period, limit=limit)
        basket = tickers if (tickers and len(tickers) > 0) else DEFAULT_HYPERSCALER_BASKET
        return await _format_basket_spending(tickers=basket, period=period)
    except Exception as e:
        logger.exception("Error in execute_get_corporate_spending_tool: %s", e)
        return f"Error retrieving corporate spending data: {e}"
