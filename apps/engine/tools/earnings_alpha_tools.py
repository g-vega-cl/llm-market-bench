"""Tool handlers for Earnings Alpha, PEAD Candidates, Revisions, and Bellwethers."""

import json
from datetime import UTC, datetime

import httpx

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client


async def fetch_pead_candidates_from_db(
    sector: str | None = None,
    min_sue: float = 2.0,
    limit: int = 20,
) -> list[dict]:
    """Query Supabase for active PEAD candidates with top-decile SUE scores."""
    try:
        supabase = get_supabase_client()
        query = (
            supabase.table("earnings_alpha_snapshots")
            .select("*")
            .gte("sue_score", min_sue)
            .order("snapshot_date", desc=True)
            .order("sue_score", desc=True)
        )
        if sector:
            query = query.eq("sector", sector.upper())
        query = query.limit(limit)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.warning(f"Failed to fetch PEAD candidates from DB: {e}")
        return []


async def fetch_fmp_grades_and_targets(ticker: str) -> tuple[dict, dict, float]:
    """Fetch analyst grades consensus, price target consensus, and current price from FMP."""
    if not FMP_API_KEY:
        return {}, {}, 0.0

    base_url = "https://financialmodelingprep.com/stable"
    grades: dict = {}
    targets: dict = {}
    current_price: float = 0.0

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            grades_resp = await client.get(
                f"{base_url}/grades-consensus", params={"symbol": ticker.upper(), "apikey": FMP_API_KEY}
            )
            if grades_resp.status_code == 200 and grades_resp.json():
                grades = grades_resp.json()[0]

            targets_resp = await client.get(
                f"{base_url}/price-target-consensus", params={"symbol": ticker.upper(), "apikey": FMP_API_KEY}
            )
            if targets_resp.status_code == 200 and targets_resp.json():
                targets = targets_resp.json()[0]

            quote_resp = await client.get(f"{base_url}/quote", params={"symbol": ticker.upper(), "apikey": FMP_API_KEY})
            if quote_resp.status_code == 200 and quote_resp.json():
                current_price = float(quote_resp.json()[0].get("price", 0.0))
    except Exception as e:
        logger.warning(f"Failed to fetch FMP grades/targets for {ticker}: {e}")

    return grades, targets, current_price


async def fetch_sector_bellwethers_from_db(sector: str) -> dict:
    """Fetch reported bellwether signals and upcoming unannounced peers for a sector from Supabase."""
    try:
        supabase = get_supabase_client()

        # 1. Fetch active reported bellwethers
        active_resp = (
            supabase.table("sector_bellwether_signals")
            .select("*")
            .eq("sector", sector.upper())
            .eq("is_active_bellwether_signal", True)
            .order("report_date", desc=True)
            .execute()
        )

        # 2. Fetch unannounced peers
        peers_resp = (
            supabase.table("sector_bellwether_signals")
            .select("*")
            .eq("sector", sector.upper())
            .eq("is_reported", False)
            .order("report_date", desc=False)
            .execute()
        )

        active_bellwethers = []
        for row in active_resp.data or []:
            active_bellwethers.append(
                {
                    "ticker": row.get("ticker"),
                    "report_date": str(row.get("report_date")),
                    "sue_score": float(row.get("sue_score", 0.0)) if row.get("sue_score") is not None else None,
                    "revenue_surprise_pct": float(row.get("revenue_surprise_pct", 0.0))
                    if row.get("revenue_surprise_pct") is not None
                    else None,
                    "days_since_report": (
                        datetime.now(UTC).date() - datetime.strptime(str(row.get("report_date")), "%Y-%m-%d").date()
                    ).days
                    if row.get("report_date")
                    else None,
                    "is_active_bellwether_signal": True,
                }
            )

        unannounced_peers = []
        for row in peers_resp.data or []:
            days_until = None
            if row.get("report_date"):
                try:
                    rep_d = datetime.strptime(str(row.get("report_date")), "%Y-%m-%d").date()
                    days_until = (rep_d - datetime.now(UTC).date()).days
                except Exception:
                    pass

            unannounced_peers.append(
                {
                    "ticker": row.get("ticker"),
                    "upcoming_earnings_date": str(row.get("report_date")),
                    "days_until_report": days_until,
                }
            )

        return {
            "sector": sector.upper(),
            "active_reported_bellwethers": active_bellwethers,
            "unannounced_peers": unannounced_peers,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch sector bellwethers from DB for {sector}: {e}")
        return {
            "sector": sector.upper(),
            "active_reported_bellwethers": [],
            "unannounced_peers": [],
        }


async def handle_get_pead_candidates(args: dict) -> str:
    """Handler for get_pead_candidates tool."""
    sector = args.get("sector")
    min_sue = float(args.get("min_sue", 2.0))
    limit = int(args.get("limit", 15))

    records = await fetch_pead_candidates_from_db(sector=sector, min_sue=min_sue, limit=limit)

    candidates = []
    for r in records:
        sue = float(r.get("sue_score", 0.0)) if r.get("sue_score") is not None else 0.0
        if sue < min_sue:
            continue
        candidates.append(
            {
                "ticker": r.get("ticker"),
                "sector": r.get("sector"),
                "report_date": str(r.get("report_date")),
                "sue_score": round(sue, 2),
                "is_top_decile_sue": bool(r.get("is_top_decile_sue", False)),
                "revenue_surprise_pct": round(float(r.get("revenue_surprise_pct", 0.0)), 2)
                if r.get("revenue_surprise_pct") is not None
                else 0.0,
                "has_sufficient_earnings_history": bool(r.get("has_sufficient_earnings_history", False)),
                "is_sloan_accrual_clean": bool(r.get("is_sloan_accrual_clean", True)),
                "has_extreme_pre_earnings_runup": bool(r.get("has_extreme_pre_earnings_runup", False)),
                "days_since_earnings_report": int(r.get("days_since_earnings_report", 0))
                if r.get("days_since_earnings_report") is not None
                else 0,
                "post_earnings_drift_pct": round(float(r.get("post_earnings_drift_pct", 0.0)), 2)
                if r.get("post_earnings_drift_pct") is not None
                else 0.0,
                "post_earnings_alpha_vs_spy": round(float(r.get("post_earnings_alpha_vs_spy", 0.0)), 2)
                if r.get("post_earnings_alpha_vs_spy") is not None
                else 0.0,
            }
        )

    return json.dumps(
        {
            "sector_filter": sector,
            "min_sue_filter": min_sue,
            "count": len(candidates),
            "candidates": candidates,
        },
        indent=2,
    )


async def handle_get_earnings_revisions(args: dict) -> str:
    """Handler for get_earnings_revisions tool."""
    ticker = str(args.get("ticker", "")).upper()
    if not ticker:
        return json.dumps({"error": "Missing required ticker parameter"})

    grades, targets, current_price = await fetch_fmp_grades_and_targets(ticker)

    strong_buy = int(grades.get("strongBuy", 0))
    buy = int(grades.get("buy", 0))
    hold = int(grades.get("hold", 0))
    sell = int(grades.get("sell", 0))
    strong_sell = int(grades.get("strongSell", 0))
    total = strong_buy + buy + hold + sell + strong_sell

    buy_ratio_pct = ((strong_buy + buy) / total * 100.0) if total > 0 else 0.0

    target_price = float(targets.get("targetConsensus", 0.0)) if targets.get("targetConsensus") else 0.0
    upside_pct = 0.0
    if current_price > 0 and target_price > 0:
        upside_pct = ((target_price - current_price) / current_price) * 100.0

    return json.dumps(
        {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "analyst_consensus": grades.get("consensus", "Unknown"),
            "analyst_coverage_count": total,
            "analyst_buy_ratio_pct": round(buy_ratio_pct, 1),
            "strong_buy_count": strong_buy,
            "buy_count": buy,
            "hold_count": hold,
            "sell_count": sell,
            "strong_sell_count": strong_sell,
            "target_consensus_price": round(target_price, 2),
            "target_consensus_upside_pct": round(upside_pct, 2),
        },
        indent=2,
    )


async def handle_get_sector_bellwethers(args: dict) -> str:
    """Handler for get_sector_bellwethers tool."""
    sector = str(args.get("sector", "")).upper()
    if not sector:
        return json.dumps({"error": "Missing required sector parameter"})

    data = await fetch_sector_bellwethers_from_db(sector)
    return json.dumps(data, indent=2)
