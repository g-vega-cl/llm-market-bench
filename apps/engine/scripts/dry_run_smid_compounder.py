"""Dry run script for the Small/Mid-Cap Quality Compounder strategy.

Runs an end-to-end live market screen using real FMP and Polygon API endpoints:
1. Queries FMP /stable/company-screener for US small/mid caps ($1B to $10B).
2. Evaluates trailing 4 quarters of fundamentals (GAAP net income, FCF, ROIC, leverage).
3. Queries Polygon for 1-year daily bars and computes 12M relative momentum.
4. Ranks the universe by composite quality/momentum score.
5. Computes order allocations for a $10,000 model portfolio with zero-ceiling hold rules.
"""

from datetime import UTC, datetime, timedelta

import httpx

from analytics.smid_quality import (
    calculate_momentum_12m,
    evaluate_quality_metrics,
    rank_and_select_candidates,
)
from core.config import FMP_API_KEY, MASSIVE_API_KEY, MASSIVE_BASE_URL
from execution.smid_compounder import compute_smid_rebalance_orders


def run_smid_dry_run(candidate_limit: int = 25, portfolio_cash: float = 10000.0) -> None:
    """Executes live end-to-end screen and simulated rebalance."""
    if not FMP_API_KEY:
        print("ERROR: FMP_API_KEY is not set.")
        return
    if not MASSIVE_API_KEY:
        print("ERROR: MASSIVE_API_KEY is not set.")
        return

    print("================================================================================")
    print("           SMALL/MID-CAP QUALITY COMPOUNDER: LIVE DRY RUN                        ")
    print("================================================================================")
    print(f"Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("Screen: US Actively Trading Equities | Market Cap: $1.0B to $10.0B")
    print(f"Sample Limit: {candidate_limit} companies\n")

    # 1. Fetch screened universe from FMP
    screener_url = (
        f"https://financialmodelingprep.com/stable/company-screener"
        f"?marketCapMoreThan=1000000000&marketCapLowerThan=10000000000"
        f"&country=US&isActivelyTrading=true&isEtf=false&isFund=false"
        f"&limit={candidate_limit}&apikey={FMP_API_KEY}"
    )

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(screener_url)
        if resp.status_code != 200:
            print(f"Failed to query screener: HTTP {resp.status_code} - {resp.text[:200]}")
            return
        raw_screen = resp.json()

    print(f"1. FMP Screener returned {len(raw_screen)} initial candidates.")
    print("2. Fetching quarterly statements and evaluating quality factors...")

    processed_candidates = []
    rejection_counts: dict[str, int] = {}

    end_date = datetime.now(UTC).strftime("%Y-%m-%d")
    start_date = (datetime.now(UTC) - timedelta(days=380)).strftime("%Y-%m-%d")

    with httpx.Client(timeout=10.0) as client:
        for item in raw_screen:
            symbol = item.get("symbol")
            price = float(item.get("price") or 0.0)
            mkt_cap = float(item.get("marketCap") or 0.0)
            company_name = item.get("companyName", symbol)
            sector = item.get("sector", "N/A")

            # Fetch fundamentals
            inc_resp = client.get(f"https://financialmodelingprep.com/stable/income-statement?symbol={symbol}&period=quarter&apikey={FMP_API_KEY}")
            cf_resp = client.get(f"https://financialmodelingprep.com/stable/cash-flow-statement?symbol={symbol}&period=quarter&apikey={FMP_API_KEY}")
            bs_resp = client.get(f"https://financialmodelingprep.com/stable/balance-sheet-statement?symbol={symbol}&period=quarter&apikey={FMP_API_KEY}")

            inc_data = inc_resp.json() if inc_resp.status_code == 200 else []
            cf_data = cf_resp.json() if cf_resp.status_code == 200 else []
            bs_data = bs_resp.json() if bs_resp.status_code == 200 else []

            quality_eval = evaluate_quality_metrics(inc_data, cf_data, bs_data)

            if not quality_eval["is_quality_pass"]:
                for r in quality_eval["rejection_reasons"]:
                    rejection_counts[r] = rejection_counts.get(r, 0) + 1
                continue

            # Fetch momentum from Polygon
            poly_url = f"{MASSIVE_BASE_URL}/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}?adjusted=true&apiKey={MASSIVE_API_KEY}"
            poly_resp = client.get(poly_url)
            bars = []
            if poly_resp.status_code == 200:
                bars = poly_resp.json().get("results", [])

            mom_12m = calculate_momentum_12m(bars)

            processed_candidates.append(
                {
                    "symbol": symbol,
                    "companyName": company_name,
                    "sector": sector,
                    "price": price,
                    "market_cap": mkt_cap,
                    "quality": quality_eval,
                    "momentum_12m": mom_12m,
                }
            )

    print("\nQuality Filter Results:")
    print(f"  - Total Evaluated: {len(raw_screen)}")
    print(f"  - Passed Quality:  {len(processed_candidates)}")
    for reason, count in rejection_counts.items():
        print(f"  - Rejected ({reason}): {count}")

    # 3. Rank and select top candidates
    selected_candidates = rank_and_select_candidates(processed_candidates, target_count=5)

    print("\n3. Top Ranked Quality & Momentum Compounders:")
    print("--------------------------------------------------------------------------------")
    print(f"{'Ticker':<7} {'Sector':<20} {'Market Cap':<10} {'TTM Net Inc':<12} {'TTM FCF':<12} {'ROIC':<7} {'12M Mom':<9} {'Score':<6}")
    print("--------------------------------------------------------------------------------")
    for c in selected_candidates:
        cap_str = f"${c['market_cap'] / 1e9:.2f}B"
        ni_str = f"${c['quality']['ttm_net_income'] / 1e6:.1f}M"
        fcf_str = f"${c['quality']['ttm_fcf'] / 1e6:.1f}M"
        roic_str = f"{c['quality']['roic'] * 100:.1f}%"
        mom_str = f"{c['momentum_12m']:+.1f}%" if c['momentum_12m'] is not None else "N/A"
        score_str = f"{c['composite_score']:.1f}"
        sec_short = c['sector'][:18]
        print(f"{c['symbol']:<7} {sec_short:<20} {cap_str:<10} {ni_str:<12} {fcf_str:<12} {roic_str:<7} {mom_str:<9} {score_str:<6}")
    print("--------------------------------------------------------------------------------")

    # 4. Simulate portfolio allocation with Zero-Ceiling Invariant
    # Let's say the portfolio already has 1 large-cap compounder winner from earlier (DECK)
    sample_current_holdings = [
        {
            "ticker": "DECK",
            "shares": 30,
            "current_price": 160.0,
            "market_cap": 22000000000.0,  # Grown into a $22B large-cap!
        }
    ]
    sample_evaluations = {
        "DECK": {"should_sell": False, "reason": "hold_quality_winner"}
    }

    rebalance_plan = compute_smid_rebalance_orders(
        current_holdings=sample_current_holdings,
        holding_evaluations=sample_evaluations,
        candidate_pool=selected_candidates,
        available_cash=portfolio_cash,
        target_holdings_count=6,
        slippage_bps=5.0,
    )

    print("\n4. Simulated Rebalance Plan Execution ($10,000 New Cash):")
    print(f"  - Retained Winners (Zero-Ceiling Rule): {len(rebalance_plan['retained'])}")
    for ret in rebalance_plan["retained"]:
        val = ret["shares"] * ret["current_price"]
        print(f"      ● {ret['ticker']} (Market Cap ${ret['market_cap']/1e9:.1f}B): Holding {ret['shares']} shares (${val:,.2f}) -> {ret['reason']}")

    print(f"  - Liquidations (Zombie/Distress): {len(rebalance_plan['sales'])}")

    print("  - New Buys Deployed:")
    for buy in rebalance_plan["buys"]:
        print(f"      ● BUY {buy['ticker']}: {buy['shares']} shares @ ${buy['execution_price']:.2f} (Total: ${buy['total_cost']:,.2f})")

    print(f"  - Cash Remaining: ${rebalance_plan['remaining_cash']:,.2f}")
    print("================================================================================")


if __name__ == "__main__":
    run_smid_dry_run()
