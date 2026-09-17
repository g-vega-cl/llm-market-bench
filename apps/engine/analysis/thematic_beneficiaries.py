"""Thematic Beneficiaries Analysis Island.

Identifies second-order winners and thematic beneficiaries by combining
industry screening, factor correlation and beta sensitivity, and options positioning.
"""

from datetime import datetime
from typing import Any

import httpx
import numpy as np

from analysis.sec_13f_client import DEFAULT_THEMATIC_FUNDS, get_fund_holdings, match_co_ownership
from core.config import FMP_API_KEY, logger
from execution.market_data import MarketDataManager
from execution.providers.massive import MassiveOptionsClient


def calculate_returns(prices: list[float]) -> np.ndarray:
    """Calculates daily returns from an ordered list of prices."""
    if len(prices) < 2:
        return np.array([])
    arr = np.array(prices, dtype=float)
    denom = arr[:-1]
    denom = np.where(denom == 0, np.nan, denom)
    returns = np.diff(arr) / denom
    return returns[~np.isnan(returns)]


def compute_pair_metrics(anchor_returns: np.ndarray, candidate_returns: np.ndarray) -> dict[str, Any]:
    """Calculates rolling correlation, empirical beta, and momentum between two return series."""
    min_len = min(len(anchor_returns), len(candidate_returns))
    if min_len < 5:
        return {
            "correlation": 0.0,
            "beta": 0.0,
            "momentum_20d": 0.0,
            "sample_count": min_len,
            "score": 0.0,
        }

    a_ret = anchor_returns[-min_len:]
    c_ret = candidate_returns[-min_len:]

    var_a = float(np.var(a_ret, ddof=1))
    var_c = float(np.var(c_ret, ddof=1))

    if var_a < 1e-9 or var_c < 1e-9:
        return {
            "correlation": 0.0,
            "beta": 0.0,
            "momentum_20d": 0.0,
            "sample_count": min_len,
            "score": 0.0,
        }

    cov = float(np.cov(a_ret, c_ret, ddof=1)[0, 1])
    corr = float(np.corrcoef(a_ret, c_ret)[0, 1])
    beta = cov / var_a

    # Momentum over the latest available window up to 20 days
    m_len = min(20, min_len)
    momentum = float(np.prod(1.0 + c_ret[-m_len:]) - 1.0)

    # Combined ranking score balancing co-movement, leverage, and momentum
    score = (0.5 * corr) + (0.3 * min(max(beta, -1.0), 2.0) / 2.0) + (0.2 * max(-0.5, min(0.5, momentum)))

    return {
        "correlation": round(corr, 3),
        "beta": round(beta, 3),
        "momentum_20d": round(momentum, 3),
        "sample_count": min_len,
        "score": round(score, 4),
    }


def calculate_fundamental_transmission(
    anchor_cf: list[dict[str, Any]],
    candidate_inc: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measures quarterly capex expansion from anchor and matching revenue absorption by candidate."""
    anchor_capex_growth = None
    if len(anchor_cf) >= 2:
        c0 = abs(float(anchor_cf[0].get("capitalExpenditure") or 0.0))
        c1 = abs(float(anchor_cf[1].get("capitalExpenditure") or 0.0))
        if c1 > 0:
            anchor_capex_growth = round((c0 - c1) / c1, 3)

    cand_rev_growth = None
    cand_op_growth = None
    if len(candidate_inc) >= 2:
        r0 = float(candidate_inc[0].get("revenue") or 0.0)
        r1 = float(candidate_inc[1].get("revenue") or 0.0)
        if r1 > 0:
            cand_rev_growth = round((r0 - r1) / r1, 3)

        op0 = float(candidate_inc[0].get("operatingIncome") or 0.0)
        op1 = float(candidate_inc[1].get("operatingIncome") or 0.0)
        if abs(op1) > 0:
            cand_op_growth = round((op0 - op1) / abs(op1), 3)

    transmission_score = 0.0
    if cand_rev_growth is not None:
        transmission_score += min(max(cand_rev_growth, -0.5), 0.5)
        if anchor_capex_growth is not None and anchor_capex_growth > 0:
            if cand_rev_growth > 0:
                transmission_score += 0.2
            if cand_op_growth is not None and cand_op_growth > 0:
                transmission_score += 0.1

    return {
        "anchor_capex_growth_qoq": anchor_capex_growth,
        "candidate_rev_growth_qoq": cand_rev_growth,
        "candidate_op_inc_growth_qoq": cand_op_growth,
        "transmission_score": round(transmission_score, 3),
    }


async def fetch_screener_candidates(
    industries: list[str] | None = None,
    sectors: list[str] | None = None,
    limit_per_group: int = 5,
    fmp_api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Screens candidate companies by industry or sector from FMP."""
    api_key = fmp_api_key or FMP_API_KEY
    if not api_key:
        logger.warning("FMP_API_KEY not configured, skipping screener candidate discovery.")
        return []

    client = http_client or httpx.AsyncClient(timeout=15.0)
    candidates: list[dict[str, Any]] = []
    seen_tickers: set[str] = set()

    try:
        targets = []
        if industries:
            for ind in industries:
                targets.append(("industry", ind))
        if sectors:
            for sec in sectors:
                targets.append(("sector", sec))

        if not targets:
            return []

        for param_key, param_val in targets:
            params = {
                param_key: param_val,
                "country": "US",
                "isActivelyTrading": "true",
                "isEtf": "false",
                "isFund": "false",
                "limit": limit_per_group,
                "apikey": api_key,
            }
            resp = await client.get("https://financialmodelingprep.com/stable/company-screener", params=params)
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    sym = item.get("symbol", "").upper()
                    if sym and sym not in seen_tickers:
                        seen_tickers.add(sym)
                        candidates.append(
                            {
                                "symbol": sym,
                                "company_name": item.get("companyName", ""),
                                "industry": item.get("industry", ""),
                                "sector": item.get("sector", ""),
                                "market_cap": float(item.get("marketCap") or 0.0),
                            }
                        )
    except Exception as e:
        logger.exception("Error querying FMP screener for thematic candidates: %s", e)
    finally:
        if http_client is None:
            await client.aclose()

    return candidates


async def _enrich_options_sentiment(
    beneficiaries: list[dict[str, Any]],
    top_n: int = 3,
    options_client: MassiveOptionsClient | None = None,
) -> None:
    """Enriches the top N candidates with options volume, open interest, and implied volatility."""
    client = options_client or MassiveOptionsClient()
    for item in beneficiaries[:top_n]:
        sym = item["symbol"]
        try:
            snapshot = await client.get_options_snapshot(sym)
            if snapshot.get("status") == "OK" and snapshot.get("contracts"):
                contracts = snapshot.get("contracts", [])
                total_calls = 0
                total_puts = 0
                total_iv = 0.0
                iv_count = 0

                for c in contracts:
                    details = c.get("details", {})
                    c_type = details.get("contract_type")
                    vol = c.get("day", {}).get("volume", 0) or 0
                    iv = c.get("implied_volatility")

                    if c_type == "call":
                        total_calls += vol
                    elif c_type == "put":
                        total_puts += vol

                    if iv and iv > 0:
                        total_iv += float(iv)
                        iv_count += 1

                pc_ratio = round(total_puts / total_calls, 3) if total_calls > 0 else None
                atm_iv = round((total_iv / iv_count) * 100.0, 1) if iv_count > 0 else None

                item["options_sentiment"] = {
                    "call_volume": total_calls,
                    "put_volume": total_puts,
                    "put_call_volume_ratio": pc_ratio,
                    "atm_iv_pct": atm_iv,
                }
        except Exception as e:
            logger.debug("Could not fetch options sentiment for candidate %s: %s", sym, e)


async def fetch_quarterly_financials(
    ticker: str,
    limit: int = 2,
    fmp_api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetches quarterly cash flow and income statements from FMP."""
    api_key = fmp_api_key or FMP_API_KEY
    if not api_key:
        return [], []

    client = http_client or httpx.AsyncClient(timeout=10.0)
    try:
        cf_url = f"https://financialmodelingprep.com/stable/cash-flow-statement?symbol={ticker}&period=quarter&limit={limit}&apikey={api_key}"
        inc_url = f"https://financialmodelingprep.com/stable/income-statement?symbol={ticker}&period=quarter&limit={limit}&apikey={api_key}"

        cf_resp = await client.get(cf_url)
        inc_resp = await client.get(inc_url)

        cf_data = cf_resp.json() if cf_resp.status_code == 200 else []
        inc_data = inc_resp.json() if inc_resp.status_code == 200 else []

        return cf_data, inc_data
    except Exception as e:
        logger.debug("Failed fetching quarterly financials for %s: %s", ticker, e)
        return [], []
    finally:
        if http_client is None:
            await client.aclose()


async def _enrich_financial_transmission(
    anchor_ticker: str,
    beneficiaries: list[dict[str, Any]],
    top_n: int = 5,
    fmp_api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> float | None:
    """Enriches candidate beneficiaries with capex and revenue transmission metrics."""
    anchor_cf, _ = await fetch_quarterly_financials(
        anchor_ticker, limit=2, fmp_api_key=fmp_api_key, http_client=http_client
    )

    anchor_capex_growth = None
    if len(anchor_cf) >= 2:
        c0 = abs(float(anchor_cf[0].get("capitalExpenditure") or 0.0))
        c1 = abs(float(anchor_cf[1].get("capitalExpenditure") or 0.0))
        if c1 > 0:
            anchor_capex_growth = round((c0 - c1) / c1, 3)

    for item in beneficiaries[:top_n]:
        sym = item["symbol"]
        _, cand_inc = await fetch_quarterly_financials(sym, limit=2, fmp_api_key=fmp_api_key, http_client=http_client)
        transmission = calculate_fundamental_transmission(anchor_cf, cand_inc)
        item["fundamentals"] = transmission
        item["score"] = round(item["score"] + (0.25 * transmission["transmission_score"]), 4)

    beneficiaries.sort(key=lambda x: x["score"], reverse=True)
    return anchor_capex_growth


KNOWN_ANCHOR_KEYWORDS = {
    "NVDA": ["NVIDIA"],
    "MSFT": ["MICROSOFT"],
    "AAPL": ["APPLE"],
    "AMZN": ["AMAZON"],
    "GOOGL": ["ALPHABET", "GOOGLE"],
    "GOOG": ["ALPHABET", "GOOGLE"],
    "META": ["META"],
    "TSLA": ["TESLA"],
    "LLY": ["LILLY", "ELI LILLY"],
    "NVO": ["NOVO NORDISK"],
}


async def _enrich_institutional_support(
    anchor_ticker: str,
    beneficiaries: list[dict[str, Any]],
    top_n: int = 5,
    fund_ciks: dict[str, str] | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, dict[str, Any]]:
    """Enriches candidate beneficiaries with Form 13F institutional co-ownership clusters."""
    funds = fund_ciks or DEFAULT_THEMATIC_FUNDS
    fund_holdings_map: dict[str, list[dict[str, Any]]] = {}

    client = http_client or httpx.AsyncClient(timeout=15.0)
    try:
        for fund_label, cik in funds.items():
            fund_data = await get_fund_holdings(cik, http_client=client)
            if fund_data and fund_data.get("holdings"):
                fund_holdings_map[fund_data.get("fund_name", fund_label)] = fund_data["holdings"]
    finally:
        if http_client is None:
            await client.aclose()

    if not fund_holdings_map:
        return {}

    anchor_sym = anchor_ticker.upper()
    anchor_keywords = [anchor_sym]
    if anchor_sym in KNOWN_ANCHOR_KEYWORDS:
        anchor_keywords.extend(KNOWN_ANCHOR_KEYWORDS[anchor_sym])

    candidates_to_match: dict[str, str] = {}
    for item in beneficiaries[:top_n]:
        sym = item["symbol"]
        comp = item.get("company_name", "")
        comp_clean = comp.replace(",", "").replace(".", "").strip()
        kw = comp_clean.split()[0].strip() if comp_clean else sym
        candidates_to_match[sym] = kw if len(kw) >= 3 else sym

    co_ownership = match_co_ownership(anchor_keywords, candidates_to_match, fund_holdings_map)

    for item in beneficiaries[:top_n]:
        sym = item["symbol"]
        if sym in co_ownership:
            cluster = co_ownership[sym]
            item["institutional_co_ownership"] = cluster
            item["score"] = round(item["score"] + (0.20 * cluster["co_owning_fund_count"]), 4)

    beneficiaries.sort(key=lambda x: x["score"], reverse=True)
    return co_ownership


async def fetch_ticker_profiles(
    tickers: list[str],
    fmp_api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, dict[str, Any]]:
    """Fetches company profile metadata for a list of tickers from FMP."""
    api_key = fmp_api_key or FMP_API_KEY
    if not api_key or not tickers:
        return {}

    client = http_client or httpx.AsyncClient(timeout=10.0)
    profiles: dict[str, dict[str, Any]] = {}
    try:
        for t in tickers:
            sym = t.strip().upper()
            url = f"https://financialmodelingprep.com/stable/profile?symbol={sym}&apikey={api_key}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list):
                    item = data[0]
                    profiles[sym] = {
                        "symbol": sym,
                        "company_name": item.get("companyName", sym),
                        "industry": item.get("industry", "Custom"),
                        "sector": item.get("sector", "Custom"),
                        "market_cap": float(item.get("marketCap") or item.get("mktCap") or 0.0),
                    }
    except Exception as e:
        logger.debug("Failed fetching ticker profiles: %s", e)
    finally:
        if http_client is None:
            await client.aclose()
    return profiles


async def compute_thematic_beneficiaries(
    anchor_ticker: str,
    theme: str | None = None,
    candidate_tickers: list[str] | None = None,
    candidate_industries: list[str] | None = None,
    candidate_sectors: list[str] | None = None,
    lookback_days: int = 60,
    options_top_n: int = 3,
    include_financials: bool = True,
    include_institutional: bool = False,
    fund_ciks: dict[str, str] | None = None,
    mdm: MarketDataManager | None = None,
    options_client: MassiveOptionsClient | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Computes second-order beneficiaries for an anchor ticker across candidate peers."""
    manager = mdm or MarketDataManager()
    anchor = anchor_ticker.strip().upper()

    # Step 1: Collect candidate ticker list
    candidates_meta: dict[str, dict[str, Any]] = {}
    if candidate_tickers:
        profiles = await fetch_ticker_profiles(candidate_tickers, http_client=http_client)
        for t in candidate_tickers:
            sym = t.strip().upper()
            if sym != anchor:
                if sym in profiles:
                    candidates_meta[sym] = profiles[sym]
                else:
                    candidates_meta[sym] = {"symbol": sym, "company_name": sym, "industry": "Custom", "market_cap": 0.0}

    if not candidates_meta and (candidate_industries or candidate_sectors):
        screener_results = await fetch_screener_candidates(
            industries=candidate_industries,
            sectors=candidate_sectors,
            limit_per_group=6,
            http_client=http_client,
        )
        for res in screener_results:
            sym = res["symbol"]
            if sym != anchor:
                candidates_meta[sym] = res

    if not candidates_meta:
        return {
            "anchor_ticker": anchor,
            "theme": theme or "Unspecified",
            "lookback_days": lookback_days,
            "beneficiaries": [],
            "summary": f"No candidate tickers discovered for theme {theme}.",
        }

    # Step 2: Fetch price history for anchor
    anchor_history = await manager.get_history(anchor, days=lookback_days + 15)
    # MarketDataManager returns desc sorted fetched_at, so reverse to chronological
    anchor_prices = [float(h["price"]) for h in reversed(anchor_history) if h.get("price")]
    anchor_returns = calculate_returns(anchor_prices)

    if len(anchor_returns) < 5:
        return {
            "anchor_ticker": anchor,
            "theme": theme or "Unspecified",
            "lookback_days": lookback_days,
            "beneficiaries": [],
            "summary": f"Insufficient historical price data for anchor {anchor}.",
        }

    # Step 3: Compute sensitivity metrics for each candidate
    beneficiaries: list[dict[str, Any]] = []
    for sym, meta in candidates_meta.items():
        try:
            cand_history = await manager.get_history(sym, days=lookback_days + 15)
            cand_prices = [float(h["price"]) for h in reversed(cand_history) if h.get("price")]
            cand_returns = calculate_returns(cand_prices)

            metrics = compute_pair_metrics(anchor_returns, cand_returns)
            if metrics["sample_count"] >= 5:
                beneficiaries.append(
                    {
                        "symbol": sym,
                        "company_name": meta.get("company_name", ""),
                        "industry": meta.get("industry", ""),
                        "sector": meta.get("sector", ""),
                        "market_cap": meta.get("market_cap", 0.0),
                        "correlation": metrics["correlation"],
                        "beta": metrics["beta"],
                        "momentum_20d": metrics["momentum_20d"],
                        "score": metrics["score"],
                    }
                )
        except Exception as e:
            logger.debug("Failed computing metrics for candidate %s: %s", sym, e)

    # Step 4: Sort candidates by score descending
    beneficiaries.sort(key=lambda x: x["score"], reverse=True)

    # Step 5: Fundamental transmission enrichment on top candidates
    anchor_capex_growth = None
    if include_financials and beneficiaries:
        anchor_capex_growth = await _enrich_financial_transmission(
            anchor, beneficiaries, top_n=5, http_client=http_client
        )

    # Step 6: Options radar enrichment on top candidates
    if options_top_n > 0 and beneficiaries:
        await _enrich_options_sentiment(beneficiaries, top_n=options_top_n, options_client=options_client)

    # Step 7: Form 13F institutional co-ownership enrichment
    if include_institutional and beneficiaries:
        await _enrich_institutional_support(
            anchor,
            beneficiaries,
            top_n=5,
            fund_ciks=fund_ciks,
            http_client=http_client,
        )

    return {
        "anchor_ticker": anchor,
        "theme": theme or "Unspecified",
        "lookback_days": lookback_days,
        "anchor_capex_growth_qoq": anchor_capex_growth,
        "as_of": datetime.now().isoformat(),
        "beneficiaries": beneficiaries,
        "summary": f"Analyzed {len(beneficiaries)} related beneficiaries for {anchor}.",
    }


def format_thematic_beneficiaries_markdown(data: dict[str, Any]) -> str:
    """Formats the beneficiaries result into a clean terminal-friendly markdown table."""
    anchor = data.get("anchor_ticker", "")
    theme = data.get("theme", "")
    beneficiaries = data.get("beneficiaries", [])

    lines = [
        f"### Thematic Beneficiaries Analysis: {anchor}",
        f"- **Theme**: {theme}",
        f"- **Lookback Window**: {data.get('lookback_days', 60)} days",
    ]
    if data.get("anchor_capex_growth_qoq") is not None:
        lines.append(f"- **Anchor CapEx QoQ**: {data.get('anchor_capex_growth_qoq') * 100.0:+.1f}%")

    has_inst = any("institutional_co_ownership" in b for b in beneficiaries)
    if has_inst:
        lines.extend(
            [
                "",
                "| Ticker | Industry | Market Cap | Corr | Beta | QoQ Rev | QoQ OpInc | P/C Ratio | ATM IV | Inst Co-Hold | Score |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "| Ticker | Industry | Market Cap | Corr | Beta | QoQ Rev | QoQ OpInc | P/C Ratio | ATM IV | Score |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )

    for b in beneficiaries:
        sym = b.get("symbol", "")
        ind = b.get("industry", "N/A") or "N/A"
        mkt_cap_num = b.get("market_cap", 0.0)
        mkt_cap_str = (
            f"${mkt_cap_num / 1e9:.1f}B"
            if mkt_cap_num >= 1e9
            else f"${mkt_cap_num / 1e6:.0f}M"
            if mkt_cap_num > 0
            else "N/A"
        )
        corr = f"{b.get('correlation', 0.0):.2f}"
        beta = f"{b.get('beta', 0.0):.2f}"
        score = f"{b.get('score', 0.0):.2f}"

        funds = b.get("fundamentals")
        if funds and funds.get("candidate_rev_growth_qoq") is not None:
            rev_str = f"{funds.get('candidate_rev_growth_qoq') * 100.0:+.1f}%"
        else:
            rev_str = "N/A"

        if funds and funds.get("candidate_op_inc_growth_qoq") is not None:
            op_str = f"{funds.get('candidate_op_inc_growth_qoq') * 100.0:+.1f}%"
        else:
            op_str = "N/A"

        opts = b.get("options_sentiment")
        if opts:
            pc_ratio = (
                f"{opts.get('put_call_volume_ratio', 'N/A')}"
                if opts.get("put_call_volume_ratio") is not None
                else "N/A"
            )
            iv = f"{opts.get('atm_iv_pct', 'N/A')}%" if opts.get("atm_iv_pct") is not None else "N/A"
        else:
            pc_ratio = "N/A"
            iv = "N/A"

        if has_inst:
            inst = b.get("institutional_co_ownership")
            inst_str = str(inst.get("co_owning_fund_count", 0)) if inst else "0"
            lines.append(
                f"| {sym} | {ind} | {mkt_cap_str} | {corr} | {beta} | {rev_str} | {op_str} | {pc_ratio} | {iv} | {inst_str} | {score} |"
            )
        else:
            lines.append(
                f"| {sym} | {ind} | {mkt_cap_str} | {corr} | {beta} | {rev_str} | {op_str} | {pc_ratio} | {iv} | {score} |"
            )

    if has_inst:
        lines.append("")
        lines.append("Co-Holding Institutional Funds:")
        for b in beneficiaries:
            inst = b.get("institutional_co_ownership")
            if inst and inst.get("funds"):
                funds_formatted = ", ".join(inst["funds"])
                lines.append(f"- {b['symbol']}: Co-held by {funds_formatted}")

    lines.append("")
    lines.append(f"Summary: {data.get('summary', '')}")
    return "\n".join(lines)
