"""Small/Mid-Cap Quality Compounder Scheduled Task.

Executes the Zero-Ceiling compounder strategy:
- Quarterly rebalance (Feb, May, Aug, Nov) to screen new high-ROIC, positive-FCF compounders.
- Monthly health check to immediately liquidate deteriorating zombie holdings.
- Invariant: Winning compounders that grow into large-caps are RETAINED without selling.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from analytics.smid_quality import (
    calculate_momentum_12m,
    evaluate_exit_condition,
    evaluate_quality_metrics,
    rank_and_select_candidates,
)
from core.config import FMP_API_KEY, MASSIVE_API_KEY, MASSIVE_BASE_URL, logger
from core.db import get_supabase_client
from execution.portfolio import Portfolio
from execution.smid_compounder import (
    DEFAULT_SLIPPAGE_BPS,
    DEFAULT_TARGET_HOLDINGS,
    SYS_SMID_COMPOUNDER_OWNER_ID,
    compute_smid_rebalance_orders,
)


def fetch_current_price_and_market_cap(
    client: httpx.Client,
    ticker: str,
    fmp_api_key: str,
) -> tuple[float, float]:
    """Fetches real-time price and market cap for a ticker via FMP /stable/quote."""
    if not fmp_api_key:
        return 0.0, 0.0
    url = f"https://financialmodelingprep.com/stable/quote?symbol={ticker.upper()}&apikey={fmp_api_key}"
    try:
        resp = client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list):
                price = float(data[0].get("price") or 0.0)
                mkt_cap = float(data[0].get("marketCap") or 0.0)
                return price, mkt_cap
    except Exception as e:
        logger.warning(f"Failed to fetch quote for {ticker}: {e}")
    return 0.0, 0.0


def fetch_holding_statements(
    client: httpx.Client,
    ticker: str,
    fmp_api_key: str,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Fetches quarterly income statement, cash flow, and balance sheet for a ticker."""
    if not fmp_api_key:
        return [], [], []

    base_fmp = "https://financialmodelingprep.com/stable"
    inc_url = f"{base_fmp}/income-statement?symbol={ticker.upper()}&period=quarter&limit=5&apikey={fmp_api_key}"
    cf_url = f"{base_fmp}/cash-flow-statement?symbol={ticker.upper()}&period=quarter&limit=5&apikey={fmp_api_key}"
    bs_url = f"{base_fmp}/balance-sheet-statement?symbol={ticker.upper()}&period=quarter&limit=2&apikey={fmp_api_key}"

    try:
        r_inc = client.get(inc_url)
        r_cf = client.get(cf_url)
        r_bs = client.get(bs_url)

        inc = r_inc.json() if r_inc.status_code == 200 else []
        cf = r_cf.json() if r_cf.status_code == 200 else []
        bs = r_bs.json() if r_bs.status_code == 200 else []

        return inc, cf, bs
    except Exception as e:
        logger.warning(f"Error fetching statements for {ticker}: {e}")
        return [], [], []


def fetch_screened_candidates(
    client: httpx.Client,
    fmp_api_key: str,
    massive_api_key: str,
    massive_base_url: str,
    limit: int = 60,
) -> list[dict]:
    """Screens candidate small/mid caps ($1B to $10B) and evaluates quality and momentum."""
    if not fmp_api_key or not massive_api_key:
        logger.error("Missing FMP_API_KEY or MASSIVE_API_KEY for SMID compounder screening.")
        return []

    screener_url = (
        f"https://financialmodelingprep.com/stable/company-screener"
        f"?marketCapMoreThan=1000000000&marketCapLowerThan=10000000000"
        f"&country=US&isActivelyTrading=true&isEtf=false&isFund=false"
        f"&limit={limit}&apikey={fmp_api_key}"
    )

    try:
        resp = client.get(screener_url)
        if resp.status_code != 200:
            logger.error(f"FMP screener query failed: HTTP {resp.status_code}")
            return []
        raw_screen = resp.json()
    except Exception as e:
        logger.error(f"Exception querying FMP screener: {e}")
        return []

    candidates: list[dict] = []
    end_date = datetime.now(UTC).strftime("%Y-%m-%d")
    start_date = (datetime.now(UTC) - timedelta(days=380)).strftime("%Y-%m-%d")

    for item in raw_screen:
        symbol = item.get("symbol")
        if not symbol:
            continue

        price = float(item.get("price") or 0.0)
        mkt_cap = float(item.get("marketCap") or 0.0)

        # 1. Fetch statements & evaluate quality
        inc, cf, bs = fetch_holding_statements(client, symbol, fmp_api_key)
        quality_res = evaluate_quality_metrics(inc, cf, bs)
        if not quality_res["is_quality_pass"]:
            continue

        # 2. Fetch momentum (FMP stock-price-change with Polygon fallback)
        mom_12m = None
        try:
            chg_resp = client.get(
                f"https://financialmodelingprep.com/stable/stock-price-change?symbol={symbol}&apikey={fmp_api_key}"
            )
            if chg_resp.status_code == 200:
                chg_data = chg_resp.json()
                if chg_data and isinstance(chg_data, list):
                    val = chg_data[0].get("1Y")
                    if val is not None:
                        mom_12m = float(val)
        except Exception as e:
            logger.warning(f"Failed to fetch FMP price change for {symbol}: {e}")

        if mom_12m is None and massive_api_key:
            poly_url = f"{massive_base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}?adjusted=true&apiKey={massive_api_key}"
            try:
                p_resp = client.get(poly_url)
                if p_resp.status_code == 200:
                    bars = p_resp.json().get("results", [])
                    mom_12m = calculate_momentum_12m(bars)
            except Exception as e:
                logger.warning(f"Failed to fetch Polygon bars for {symbol}: {e}")

        candidates.append(
            {
                "symbol": symbol,
                "price": price,
                "market_cap": mkt_cap,
                "quality": quality_res,
                "momentum_12m": mom_12m,
            }
        )

    return candidates


async def run_smid_compounder_task(
    mode: str = "auto",
    target_holdings: int = DEFAULT_TARGET_HOLDINGS,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Runs the scheduled SMID Quality Compounder task."""
    logger.info(f"Starting SMID Compounder Task (Mode: {mode}, Target Holdings: {target_holdings}, Dry Run: {dry_run})")

    portfolio = Portfolio(SYS_SMID_COMPOUNDER_OWNER_ID)
    await portfolio.initialize()

    # Determine execution mode if auto
    now = datetime.now(UTC)
    active_mode = mode.lower()
    if active_mode == "auto":
        # If portfolio is empty, do a full initial rebalance
        if not portfolio.positions or now.month in (2, 5, 8, 11) and now.day >= 18:
            active_mode = "rebalance"
        else:
            active_mode = "health_check"

    logger.info(f"SMID Compounder active mode determined: {active_mode}")

    current_holdings: list[dict] = []
    holding_evaluations: dict[str, dict] = {}
    current_prices: dict[str, float] = {}

    with httpx.Client(timeout=15.0) as client:
        # 1. Evaluate current positions
        for ticker, pos in list(portfolio.positions.items()):
            price, mkt_cap = fetch_current_price_and_market_cap(client, ticker, FMP_API_KEY)
            current_p = price if price > 0 else pos.average_cost_basis
            current_prices[ticker] = current_p

            inc, cf, bs = fetch_holding_statements(client, ticker, FMP_API_KEY)
            holding_info = {
                "ticker": ticker,
                "current_price": current_p,
                "market_cap": mkt_cap,
                "shares": pos.quantity,
                "cost_basis": pos.average_cost_basis,
            }
            current_holdings.append(holding_info)

            should_sell, reason = evaluate_exit_condition(holding_info, inc, cf, bs)
            holding_evaluations[ticker] = {"should_sell": should_sell, "reason": reason}

        # 2. If rebalance mode, screen new candidates
        candidate_pool: list[dict] = []
        if active_mode == "rebalance":
            raw_candidates = fetch_screened_candidates(
                client,
                FMP_API_KEY,
                MASSIVE_API_KEY,
                MASSIVE_BASE_URL,
                limit=80,
            )
            # Rank candidates
            candidate_pool = rank_and_select_candidates(raw_candidates, target_count=target_holdings)

    # 3. Compute orders
    # In health_check mode, candidate_pool is empty so no new buys are generated
    active_candidate_pool = candidate_pool if active_mode == "rebalance" else []
    plan = compute_smid_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        candidate_pool=active_candidate_pool,
        available_cash=portfolio.cash_balance,
        target_holdings_count=target_holdings,
        slippage_bps=DEFAULT_SLIPPAGE_BPS,
    )

    # 4. Execute orders in database if not dry_run
    if not dry_run and portfolio.id:
        # Execute Sales
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
                skip_alpaca_mirror=True,
            )
            logger.info(f"Executed SELL {shares} {ticker} @ {exec_p:.2f} (Reason: {sale['reason']})")

        # Execute Buys
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
                skip_alpaca_mirror=True,
            )
            logger.info(f"Executed BUY {shares} {ticker} @ {exec_p:.2f}")

        # Update performance record in DB
        supabase = get_supabase_client()
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

    return {
        "status": "success",
        "mode": active_mode,
        "dry_run": dry_run,
        "sales": plan["sales"],
        "retained": plan["retained"],
        "buys": plan["buys"],
        "freed_cash": plan["freed_cash"],
        "remaining_cash": plan["remaining_cash"],
    }


def main():
    parser = argparse.ArgumentParser(description="Small/Mid-Cap Quality Compounder Task")
    parser.add_argument(
        "--mode",
        choices=["auto", "rebalance", "health_check"],
        default="auto",
        help="Execution mode (default: auto)",
    )
    parser.add_argument(
        "--target-holdings",
        type=int,
        default=DEFAULT_TARGET_HOLDINGS,
        help="Target number of portfolio holdings (default: 25)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying the database",
    )
    args = parser.parse_args()

    asyncio.run(
        run_smid_compounder_task(
            mode=args.mode,
            target_holdings=args.target_holdings,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
