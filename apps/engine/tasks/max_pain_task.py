"""Daily Options Max Pain Systematic Task.

Executes the Daily Index Max Pain pinning strategy:
1. Queries 0DTE options chain metrics and Max Pain strikes for SPY and QQQ via MassiveOptionsClient.
2. Identifies mean-reversion discount opportunities where spot price trades below today's strike.
3. Submits typed admission questions to TypeSafe Jev via the OpenRouter Decisions API.
4. Executes rebalance orders against `sys-max-pain` portfolio with 0.01% (1 bps) slippage,
   profit target strike touches, and 3:50 PM market-on-close liquidations.
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
from core.llm.max_pain_prompts import (
    MAX_PAIN_DEFAULT_CRITERIA,
    MAX_PAIN_JEV_INSTRUCTIONS,
    MAX_PAIN_JEV_QUESTION_KEY,
    MAX_PAIN_JEV_QUESTION_TYPE,
)
from execution.max_pain import (
    DEFAULT_ADVERSE_STOP_PCT,
    DEFAULT_MAX_HOLDINGS,
    DEFAULT_MAX_PAIN_SLIPPAGE_BPS,
    DEFAULT_TARGET_PROXIMITY_PCT,
    SYS_MAX_PAIN_OWNER_ID,
    compute_max_pain_rebalance_orders,
    evaluate_max_pain_holding_exit,
)
from execution.portfolio import Portfolio
from execution.providers.massive import MassiveOptionsClient

DEFAULT_TARGET_TICKERS: tuple[str, ...] = ("SPY", "QQQ")


def fetch_current_price(client: httpx.Client, ticker: str, fmp_key: str) -> float:
    """Fetch real-time price for an index ticker via FMP /stable/quote."""
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


async def fetch_max_pain_snapshot(ticker: str, min_dte: int = 0) -> dict[str, Any] | None:
    """Retrieve 0DTE options snapshot and Max Pain metrics with error isolation."""
    try:
        client = MassiveOptionsClient()
        snapshot = await client.get_options_snapshot(ticker, min_dte=min_dte)
        if snapshot.get("status") == "OK" and snapshot.get("metrics"):
            return snapshot["metrics"]
    except Exception as e:
        logger.warning(f"Massive options fetch error for {ticker} (graceful fallback): {e}")

    # Fallback to Supabase options_data_cache
    try:
        sb = get_supabase_client()
        if sb:
            res = sb.table("options_data_cache").select("metrics").eq("ticker", ticker.upper()).execute()
            if res.data and res.data[0].get("metrics"):
                return res.data[0]["metrics"]
    except Exception as e:
        logger.debug(f"options_data_cache lookup failed for {ticker}: {e}")

    return None


async def evaluate_candidate_with_jev(
    candidate: dict[str, Any],
    criteria: dict[str, str] | None = None,
    min_confidence: float = 70.0,
    model_name: str = JEV_MODEL,
) -> dict[str, Any]:
    """Evaluates an index options candidate using TypeSafe Jev on the OpenRouter Decisions API."""
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
    crit = criteria or MAX_PAIN_DEFAULT_CRITERIA

    state = {
        "ticker": ticker,
        "underlying_price": candidate.get("price"),
        "max_pain_strike": candidate.get("max_pain_strike"),
        "discount_pct": candidate.get("discount_pct"),
        "put_call_oi_ratio": candidate.get("put_call_oi_ratio"),
        "atm_implied_volatility": candidate.get("atm_implied_volatility"),
        "total_contracts_analyzed": candidate.get("total_contracts_analyzed"),
        "staleness_note": candidate.get("staleness_note"),
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "state": state,
        "questions": {
            MAX_PAIN_JEV_QUESTION_KEY: {
                "type": MAX_PAIN_JEV_QUESTION_TYPE,
                "instructions": MAX_PAIN_JEV_INSTRUCTIONS,
                "criteria": {
                    "QUALIFIED": crit.get("QUALIFIED", MAX_PAIN_DEFAULT_CRITERIA["QUALIFIED"]),
                    "DISQUALIFIED": crit.get("DISQUALIFIED", MAX_PAIN_DEFAULT_CRITERIA["DISQUALIFIED"]),
                },
            }
        },
    }

    try:
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
    except Exception as e:
        logger.warning(f"Network error evaluating candidate {ticker} with Jev: {e}")
        return {
            "is_qualified": False,
            "choice": "DISQUALIFIED",
            "confidence": 0.0,
            "probabilities": {},
        }

    answers = data.get("answers", {})
    ans = answers.get(MAX_PAIN_JEV_QUESTION_KEY, {})
    choice = str(ans.get("choice", "DISQUALIFIED")).upper()
    probabilities = ans.get("probabilities", {})

    prob = float(probabilities.get(choice, ans.get("confidence", 0.5)))
    confidence = round(prob * 100.0, 1) if prob <= 1.0 else round(prob, 1)
    is_qualified = (choice == "QUALIFIED") and (confidence >= min_confidence)

    logger.info(f"Jev Max Pain Decision for {ticker}: {choice} (Conf: {confidence:.1f}%, Qualified: {is_qualified})")

    return {
        "is_qualified": is_qualified,
        "choice": choice,
        "confidence": confidence,
        "probabilities": probabilities,
    }


async def run_max_pain_task(
    dry_run: bool = False,
    action: str = "evaluate",
    tickers: tuple[str, ...] | list[str] = DEFAULT_TARGET_TICKERS,
    max_holdings: int = DEFAULT_MAX_HOLDINGS,
    min_discount_pct: float = 0.25,
    max_discount_pct: float = 2.50,
    min_confidence: float = 70.0,
    target_proximity_pct: float = DEFAULT_TARGET_PROXIMITY_PCT,
    stop_loss_pct: float = DEFAULT_ADVERSE_STOP_PCT,
    is_market_close_window: bool = False,
) -> dict[str, Any]:
    """Runs the systematic Daily Options Max Pain strategy with failure isolation."""
    logger.info(
        f"Starting Daily Max Pain Task (Action: {action}, Dry Run: {dry_run}, "
        f"Tickers: {tickers}, Max Holdings: {max_holdings}, Discount Range: {min_discount_pct}%-{max_discount_pct}%)"
    )

    try:
        portfolio = Portfolio(SYS_MAX_PAIN_OWNER_ID)
        await portfolio.initialize()
    except Exception as e:
        logger.exception(f"Failed to initialize portfolio for {SYS_MAX_PAIN_OWNER_ID}: {e}")
        return {"status": "error", "error": f"Portfolio initialization failed: {e}"}

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
                "target_strike": pos.average_cost_basis * 1.008,  # Default or stored target
            }
            current_holdings.append(holding_info)

            should_exit, reason = evaluate_max_pain_holding_exit(
                holding_info,
                current_price=current_p,
                is_market_close_window=is_market_close_window or (action == "exit"),
                target_proximity_pct=target_proximity_pct,
                stop_loss_pct=stop_loss_pct,
            )
            holding_evaluations[ticker] = {"should_exit": should_exit, "reason": reason}

        # 2. Screen incoming daily 0DTE candidates (only if evaluating or entry action)
        qualified_candidates: list[dict[str, Any]] = []
        if action in ("evaluate", "entry") and not is_market_close_window:
            for t in tickers:
                sym = t.upper().strip()
                if sym in portfolio.positions and not holding_evaluations.get(sym, {}).get("should_exit"):
                    continue

                spot_px = fetch_current_price(client, sym, FMP_API_KEY)
                metrics = await fetch_max_pain_snapshot(sym, min_dte=0)
                if not metrics:
                    logger.debug(f"Skipping {sym}: No options snapshot available.")
                    continue

                max_pain_strike = metrics.get("max_pain")
                if not max_pain_strike or float(max_pain_strike) <= 0:
                    continue

                if spot_px <= 0:
                    spot_px = float(metrics.get("underlying_price") or 0.0)
                if spot_px <= 0:
                    continue

                current_prices[sym] = spot_px
                # Calculate discount percentage: (max_pain - spot) / spot * 100
                discount_pct = ((float(max_pain_strike) - spot_px) / spot_px) * 100.0

                if min_discount_pct <= discount_pct <= max_discount_pct:
                    cand_data = {
                        "ticker": sym,
                        "price": spot_px,
                        "max_pain_strike": float(max_pain_strike),
                        "discount_pct": round(discount_pct, 2),
                        "put_call_oi_ratio": metrics.get("put_call_oi_ratio"),
                        "atm_implied_volatility": metrics.get("atm_implied_volatility"),
                        "total_contracts_analyzed": metrics.get("total_contracts_analyzed"),
                        "staleness_note": metrics.get("staleness_note"),
                    }
                    jev_res = await evaluate_candidate_with_jev(cand_data, min_confidence=min_confidence)
                    if jev_res.get("is_qualified"):
                        cand_data["jev_confidence"] = jev_res.get("confidence", 0.0)
                        qualified_candidates.append(cand_data)

    # 3. Compute rebalance orders
    plan = compute_max_pain_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=qualified_candidates,
        available_cash=portfolio.cash_balance,
        max_holdings=max_holdings,
        slippage_bps=DEFAULT_MAX_PAIN_SLIPPAGE_BPS,
    )

    # 4. Execute orders if live (not dry-run)
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
            logger.info(f"Max Pain Executed SELL {shares} {ticker} @ {exec_p:.2f} ({sale['reason']})")

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
            logger.info(
                f"Max Pain Executed BUY {shares} {ticker} @ {exec_p:.2f} (Target Strike: ${buy['target_strike']:.2f})"
            )

        # Upsert portfolio performance
        try:
            supabase = get_supabase_client()
            if supabase:
                now = datetime.now(UTC)
                today_str = now.strftime("%Y-%m-%d")
                total_equity = portfolio.cash_balance + sum(
                    pos.quantity * current_prices.get(t, pos.average_cost_basis)
                    for t, pos in portfolio.positions.items()
                )
                supabase.table("portfolio_performance").upsert(
                    {
                        "portfolio_id": str(portfolio.id),
                        "date": today_str,
                        "total_equity": total_equity,
                        "cash_balance": portfolio.cash_balance,
                        "buying_power": portfolio.cash_balance * 2,
                        "sma": 0.0,
                        "realized": total_equity,
                    },
                    on_conflict="portfolio_id,date",
                ).execute()
        except Exception as e:
            logger.warning(f"Failed to upsert portfolio_performance for {SYS_MAX_PAIN_OWNER_ID}: {e}")

    return {
        "status": "success",
        "dry_run": dry_run,
        "action": action,
        "sales": plan["sales"],
        "retained": plan["retained"],
        "buys": plan["buys"],
        "freed_cash": plan["freed_cash"],
        "remaining_cash": plan["remaining_cash"],
    }


def main():
    parser = argparse.ArgumentParser(description="Daily Options Max Pain Strategy Task")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying DB")
    parser.add_argument("--action", choices=["evaluate", "entry", "exit"], default="evaluate", help="Execution phase")
    parser.add_argument("--max-holdings", type=int, default=DEFAULT_MAX_HOLDINGS, help="Target max holdings")
    parser.add_argument("--min-discount", type=float, default=0.25, help="Minimum discount to strike pct")
    parser.add_argument("--max-discount", type=float, default=2.50, help="Maximum discount to strike pct")
    parser.add_argument("--min-confidence", type=float, default=70.0, help="Minimum Jev confidence threshold")
    parser.add_argument("--close-window", action="store_true", help="Flag 3:50 PM MOC liquidation window")
    args = parser.parse_args()

    asyncio.run(
        run_max_pain_task(
            dry_run=args.dry_run,
            action=args.action,
            max_holdings=args.max_holdings,
            min_discount_pct=args.min_discount,
            max_discount_pct=args.max_discount,
            min_confidence=args.min_confidence,
            is_market_close_window=args.close_window,
        )
    )


if __name__ == "__main__":
    main()
