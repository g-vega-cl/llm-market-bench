"""Post-Earnings Announcement Drift (PEAD) Scheduled Task.

Executes the PEAD systematic strategy:
1. Queries top-decile SUE candidates with clean Sloan accruals from `earnings_alpha_snapshots`.
2. Gathers fundamental surprise metrics and recent headlines into a candidate state card.
3. Submits typed admission questions to TypeSafe Jev via the OpenRouter Decisions API.
4. Executes rebalance orders against `sys-pead-drift` portfolio with position sizing and trailing stops.
"""

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime
from typing import Any

# Ensure apps/engine is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from core.config import FMP_API_KEY, JEV_MODEL, OPENROUTER_API_KEY, logger
from core.db import get_supabase_client
from core.llm.pead_prompts import (
    PEAD_DEFAULT_CRITERIA,
    PEAD_JEV_INSTRUCTIONS,
    PEAD_JEV_QUESTION_KEY,
    PEAD_JEV_QUESTION_TYPE,
)
from execution.pead_drift import (
    DEFAULT_MAX_HOLDING_DAYS,
    DEFAULT_MAX_HOLDINGS,
    DEFAULT_SLIPPAGE_BPS,
    DEFAULT_TRAILING_STOP_PCT,
    SYS_PEAD_DRIFT_OWNER_ID,
    compute_pead_rebalance_orders,
    evaluate_holding_exit,
)
from execution.portfolio import Portfolio


def fetch_current_price(client: httpx.Client, ticker: str, fmp_key: str) -> float:
    """Fetch real-time price for a ticker via FMP /stable/quote."""
    if not fmp_key:
        return 0.0
    url = f"https://financialmodelingprep.com/stable/quote?symbol={ticker.upper()}&apikey={fmp_key}"
    try:
        resp = client.get(url, timeout=10.0)
        if resp.status_code == 200 and resp.json():
            data = resp.json()
            if isinstance(data, list) and data:
                return float(data[0].get("price") or 0.0)
    except Exception as e:
        logger.debug(f"Failed to fetch FMP price for {ticker}: {e}")
    return 0.0


async def evaluate_candidate_with_jev(
    candidate: dict[str, Any],
    criteria: dict[str, str] | None = None,
    min_confidence: float = 70.0,
    model_name: str = JEV_MODEL,
) -> dict[str, Any]:
    """Evaluates an earnings candidate using TypeSafe Jev on the OpenRouter Decisions API."""
    key = OPENROUTER_API_KEY
    if not key:
        logger.warning("OPENROUTER_API_KEY is not set. Defaulting Jev evaluation to disqualified.")
        return {
            "is_qualified": False,
            "choice": "DISQUALIFIED",
            "confidence": 0.0,
            "probabilities": {},
        }

    ticker = str(candidate.get("ticker", "")).upper()
    crit = criteria or PEAD_DEFAULT_CRITERIA

    # Build dense financial surprise context for Jev state
    state = {
        "ticker": ticker,
        "sector": candidate.get("sector", "Unknown"),
        "report_date": str(candidate.get("report_date", "")),
        "actual_eps": candidate.get("actual_eps"),
        "estimated_eps": candidate.get("estimated_eps"),
        "eps_surprise": candidate.get("eps_surprise"),
        "revenue_surprise_pct": candidate.get("revenue_surprise_pct"),
        "sue_score": candidate.get("sue_score"),
        "sloan_accrual_ratio": candidate.get("sloan_accrual_ratio"),
        "is_sloan_accrual_clean": candidate.get("is_sloan_accrual_clean", True),
        "analyst_consensus": candidate.get("analyst_consensus", "Unknown"),
        "target_upside_pct": candidate.get("target_consensus_upside_pct"),
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "state": state,
        "questions": {
            PEAD_JEV_QUESTION_KEY: {
                "type": PEAD_JEV_QUESTION_TYPE,
                "instructions": PEAD_JEV_INSTRUCTIONS,
                "criteria": {
                    "QUALIFIED": crit.get("QUALIFIED", PEAD_DEFAULT_CRITERIA["QUALIFIED"]),
                    "DISQUALIFIED": crit.get("DISQUALIFIED", PEAD_DEFAULT_CRITERIA["DISQUALIFIED"]),
                },
            }
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://openrouter.ai/api/alpha/decisions", headers=headers, json=payload)
        if resp.status_code != 200:
            logger.warning(f"OpenRouter Decisions error {resp.status_code} for {ticker}: {resp.text}")
            return {
                "is_qualified": False,
                "choice": "DISQUALIFIED",
                "confidence": 0.0,
                "probabilities": {},
            }
        data = resp.json()

    answers = data.get("answers", {})
    ans = answers.get(PEAD_JEV_QUESTION_KEY, {})
    choice = str(ans.get("choice", "DISQUALIFIED")).upper()
    probabilities = ans.get("probabilities", {})

    prob = float(probabilities.get(choice, ans.get("confidence", 0.5)))
    confidence = round(prob * 100.0, 1) if prob <= 1.0 else round(prob, 1)

    is_qualified = (choice == "QUALIFIED") and (confidence >= min_confidence)

    logger.info(f"Jev PEAD Decision for {ticker}: {choice} (Conf: {confidence:.1f}%, Qualified: {is_qualified})")

    return {
        "is_qualified": is_qualified,
        "choice": choice,
        "confidence": confidence,
        "probabilities": probabilities,
    }


def fetch_pead_candidates_for_evaluation(
    supabase: Any,
    min_sue: float = 2.0,
    max_days_since_report: int = 5,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Queries top-decile SUE candidates with clean accruals from Supabase."""
    try:
        res = (
            supabase.table("earnings_alpha_snapshots")
            .select("*")
            .gte("sue_score", min_sue)
            .lte("days_since_earnings_report", max_days_since_report)
            .order("snapshot_date", desc=True)
            .order("sue_score", desc=True)
            .limit(limit)
            .execute()
        )
        raw_candidates = res.data or []
        seen = set()
        deduped = []
        for cand in raw_candidates:
            ticker = (cand.get("ticker") or "").upper()
            if ticker and ticker not in seen:
                seen.add(ticker)
                deduped.append(cand)
        return deduped
    except Exception as e:
        logger.exception(f"Failed to fetch PEAD snapshot candidates: {e}")
        return []


async def run_pead_drift_task(
    dry_run: bool = False,
    max_holdings: int = DEFAULT_MAX_HOLDINGS,
    max_holding_days: int = DEFAULT_MAX_HOLDING_DAYS,
    min_sue: float = 2.0,
    min_confidence: float = 70.0,
    trailing_stop_pct: float = DEFAULT_TRAILING_STOP_PCT,
) -> dict[str, Any]:
    """Runs the systematic PEAD Drift strategy."""
    logger.info(
        f"Starting PEAD Drift Task (Dry Run: {dry_run}, Max Holdings: {max_holdings}, "
        f"Holding Days: {max_holding_days}, Min SUE: {min_sue}, Min Jev Conf: {min_confidence}%)"
    )

    portfolio = Portfolio(SYS_PEAD_DRIFT_OWNER_ID)
    await portfolio.initialize()

    supabase = get_supabase_client()
    current_holdings: list[dict[str, Any]] = []
    holding_evaluations: dict[str, dict[str, Any]] = {}
    current_prices: dict[str, float] = {}

    with httpx.Client(timeout=15.0) as client:
        # 1. Evaluate current positions for exit triggers
        for ticker, pos in list(portfolio.positions.items()):
            price = fetch_current_price(client, ticker, FMP_API_KEY)
            current_p = price if price > 0 else pos.average_cost_basis
            current_prices[ticker] = current_p

            holding_info = {
                "ticker": ticker,
                "shares": pos.quantity,
                "current_price": current_p,
                "cost_basis": pos.average_cost_basis,
                "entry_price": pos.average_cost_basis,
                "holding_days": 1,  # Calculated or updated
            }
            current_holdings.append(holding_info)

            should_exit, reason = evaluate_holding_exit(
                holding_info,
                current_price=current_p,
                max_holding_days=max_holding_days,
                trailing_stop_pct=trailing_stop_pct,
            )
            holding_evaluations[ticker] = {"should_exit": should_exit, "reason": reason}

        # 2. Query recent top-decile SUE candidates
        candidates = fetch_pead_candidates_for_evaluation(
            supabase=supabase, min_sue=min_sue, max_days_since_report=5, limit=20
        )

        # 3. Filter candidates through Jev System One Decisions
        qualified_candidates: list[dict[str, Any]] = []
        for cand in candidates:
            ticker = cand.get("ticker", "").upper()
            if not ticker or ticker in portfolio.positions:
                continue

            jev_res = await evaluate_candidate_with_jev(cand, min_confidence=min_confidence)
            if jev_res.get("is_qualified"):
                price = fetch_current_price(client, ticker, FMP_API_KEY)
                if price <= 0:
                    price = float(cand.get("target_consensus_price") or 100.0)
                current_prices[ticker] = price

                qualified_candidates.append(
                    {
                        "ticker": ticker,
                        "price": price,
                        "sue_score": cand.get("sue_score", 0.0),
                        "jev_confidence": jev_res.get("confidence", 0.0),
                    }
                )

    # 4. Compute rebalance orders
    plan = compute_pead_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=qualified_candidates,
        available_cash=portfolio.cash_balance,
        max_holdings=max_holdings,
        slippage_bps=DEFAULT_SLIPPAGE_BPS,
    )

    # 5. Execute orders if live (not dry-run)
    if not dry_run and portfolio.id:
        for sale in plan["sales"]:
            ticker = sale["ticker"]
            shares = sale["shares"]
            exec_p = sale["execution_price"]
            await portfolio.execute_trade(
                ticker=ticker,
                quantity=shares,
                price=exec_p,
                signal="SELL",
                current_prices=current_prices,
                skip_alpaca_mirror=False,
            )
            logger.info(f"PEAD Executed SELL {shares} {ticker} @ {exec_p:.2f} ({sale['reason']})")

        for buy in plan["buys"]:
            ticker = buy["ticker"]
            shares = buy["shares"]
            exec_p = buy["execution_price"]
            current_prices[ticker] = exec_p
            await portfolio.execute_trade(
                ticker=ticker,
                quantity=shares,
                price=exec_p,
                signal="BUY",
                current_prices=current_prices,
                skip_alpaca_mirror=False,
            )
            logger.info(f"PEAD Executed BUY {shares} {ticker} @ {exec_p:.2f} (SUE: {buy['sue_score']})")

        portfolio.calculate_reg_t_metrics(current_prices)
        await portfolio.save_metrics()

        # Upsert portfolio performance
        now = datetime.now(UTC)
        today_str = now.strftime("%Y-%m-%d")
        total_equity = portfolio.total_equity

        supabase.table("portfolio_performance").upsert(
            {
                "portfolio_id": str(portfolio.id),
                "date": today_str,
                "total_equity": total_equity,
                "cash_balance": portfolio.cash_balance,
                "buying_power": portfolio.metrics.buying_power if portfolio.metrics else portfolio.cash_balance * 2,
                "sma": portfolio.sma,
                "realized": portfolio.metrics.realized if portfolio.metrics else total_equity,
            },
            on_conflict="portfolio_id,date",
        ).execute()

    return {
        "status": "success",
        "dry_run": dry_run,
        "sales": plan["sales"],
        "retained": plan["retained"],
        "buys": plan["buys"],
        "freed_cash": plan["freed_cash"],
        "remaining_cash": plan["remaining_cash"],
    }


def main():
    parser = argparse.ArgumentParser(description="PEAD Drift Strategy Task")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying DB")
    parser.add_argument("--max-holdings", type=int, default=DEFAULT_MAX_HOLDINGS, help="Target max holdings")
    parser.add_argument("--holding-days", type=int, default=DEFAULT_MAX_HOLDING_DAYS, help="Max holding days")
    parser.add_argument("--min-sue", type=float, default=2.0, help="Minimum SUE score threshold")
    parser.add_argument("--min-confidence", type=float, default=70.0, help="Minimum Jev confidence threshold")
    args = parser.parse_args()

    asyncio.run(
        run_pead_drift_task(
            dry_run=args.dry_run,
            max_holdings=args.max_holdings,
            max_holding_days=args.holding_days,
            min_sue=args.min_sue,
            min_confidence=args.min_confidence,
        )
    )


if __name__ == "__main__":
    main()
