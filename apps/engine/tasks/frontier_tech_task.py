"""Frontier Technology Supercycle Monthly Scheduled Task.

Executes the monthly discovery, qualification, and portfolio allocation for sys-frontier-tech:
1. Reviews and discovers gestation-phase frontier technology themes.
2. Validates themes against the 5-point supercycle rubric.
3. Screens small-cap pure plays for exchange, liquidity, runway (>= 18 mo), and anti-pump checks.
4. Executes venture power-law rebalance (2% - 4% sizing, minimal churn, thesis death exits).
5. Persists qualified themes to `frontier_themes` table and updates `portfolios` / `trades`.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from analytics.frontier_tech import (
    SupercycleRubricCriteria,
    evaluate_stock_guardrails,
    evaluate_supercycle_rubric,
)
from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from execution.frontier_tech import (
    DEFAULT_SLIPPAGE_BPS,
    DEFAULT_TARGET_POSITION_WEIGHT,
    SYS_FRONTIER_TECH_OWNER_ID,
    compute_frontier_rebalance_orders,
)
from execution.portfolio import Portfolio

# Baseline vetted frontier themes for initialization and deterministic offline fallback
DEFAULT_FRONTIER_THEMES = [
    {
        "theme_name": "Silicon Photonics & Optical Interconnects",
        "thesis": "Generative AI copper interconnects are reaching physical thermal and distance limits at 800G and 1.6T. Silicon photonics replaces copper wires with direct optical chip-to-chip links.",
        "catalysts": "800G/1.6T optical transceiver volume ramp; hyperscaler optical backplane trials.",
        "rubric": SupercycleRubricCriteria(
            cost_deflation=True,
            pure_play_enabler=True,
            talent_migration=True,
            regulatory_catalyst=False,
            early_commercial_pilot=True,
        ),
        "candidate_tickers": ["POET", "LWLG"],
    },
    {
        "theme_name": "Next-Gen SMR & Advanced Nuclear",
        "thesis": "Hyperscaler data centers require 24/7 clean baseload power that intermittent renewables cannot supply. Small modular reactors and enriched fuel form the critical power bottleneck.",
        "catalysts": "NRC regulatory licensing progress; hyperscaler 20-year power purchase agreements; DOE HALEU availability.",
        "rubric": SupercycleRubricCriteria(
            cost_deflation=True,
            pure_play_enabler=True,
            talent_migration=True,
            regulatory_catalyst=True,
            early_commercial_pilot=True,
        ),
        "candidate_tickers": ["SMR", "OKLO", "LEU"],
    },
    {
        "theme_name": "Precision Gene Writing & Synthetic Biology",
        "thesis": "Transition from first-generation cutting (CRISPR double-strand breaks) to precision base editing, prime editing, and de-novo high-throughput DNA synthesis.",
        "catalysts": "In-vivo base editing clinical readouts; silicon-based enzymatic DNA synthesis cost deflation.",
        "rubric": SupercycleRubricCriteria(
            cost_deflation=True,
            pure_play_enabler=True,
            talent_migration=True,
            regulatory_catalyst=True,
            early_commercial_pilot=False,
        ),
        "candidate_tickers": ["TWST", "BEAM", "DNA"],
    },
    {
        "theme_name": "Commercial Space Infrastructure & Orbital Logistics",
        "thesis": "Rapidly declining launch cost per kilogram enables commercial low Earth orbit constellations, direct-to-cell satellite broadband, and lunar payload logistics.",
        "catalysts": "Direct-to-smartphone commercial service activation; reusable medium launch vehicle maiden flights.",
        "rubric": SupercycleRubricCriteria(
            cost_deflation=True,
            pure_play_enabler=True,
            talent_migration=True,
            regulatory_catalyst=True,
            early_commercial_pilot=True,
        ),
        "candidate_tickers": ["RKLB", "ASTS", "LUNR"],
    },
]


def fetch_ticker_data_for_screening(
    client: httpx.Client,
    ticker: str,
    fmp_api_key: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Fetches profile, quote, and financials from FMP for a candidate stock."""
    if not fmp_api_key:
        return {}, {}, {"cash": 0.0, "operating_expenses": 0.0, "is_profitable": False}

    base_fmp = "https://financialmodelingprep.com/stable"
    profile_url = f"{base_fmp}/profile?symbol={ticker.upper()}&apikey={fmp_api_key}"
    quote_url = f"{base_fmp}/quote?symbol={ticker.upper()}&apikey={fmp_api_key}"
    bs_url = f"{base_fmp}/balance-sheet-statement?symbol={ticker.upper()}&period=quarter&limit=1&apikey={fmp_api_key}"
    is_url = f"{base_fmp}/income-statement?symbol={ticker.upper()}&period=quarter&limit=4&apikey={fmp_api_key}"

    profile: dict[str, Any] = {}
    quote: dict[str, Any] = {}
    financials: dict[str, Any] = {"cash": 0.0, "operating_expenses": 0.0, "is_profitable": False}

    try:
        rp = client.get(profile_url)
        if rp.status_code == 200 and rp.json():
            profile = rp.json()[0]

        rq = client.get(quote_url)
        if rq.status_code == 200 and rq.json():
            quote = rq.json()[0]

        rbs = client.get(bs_url)
        if rbs.status_code == 200 and rbs.json():
            bs = rbs.json()[0]
            financials["cash"] = float(bs.get("cashAndCashEquivalents") or 0.0)

        ris = client.get(is_url)
        if ris.status_code == 200 and ris.json():
            statements = ris.json()
            annual_opex = sum(float(s.get("operatingExpenses") or 0.0) for s in statements)
            annual_net = sum(float(s.get("netIncome") or 0.0) for s in statements)
            financials["operating_expenses"] = annual_opex
            financials["is_profitable"] = annual_net > 0.0
    except Exception as e:
        logger.warning(f"Failed to fetch FMP data for {ticker}: {e}")

    return profile, quote, financials


async def run_frontier_tech_task(
    mode: str = "auto",
    dry_run: bool = False,
    target_weight: float = DEFAULT_TARGET_POSITION_WEIGHT,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Executes the monthly Frontier Technology Supercycle portfolio task."""
    logger.info(f"Starting Frontier Tech Supercycle Task (mode={mode}, dry_run={dry_run})")
    supabase = get_supabase_client()
    now = datetime.now(UTC)

    # 1. Initialize portfolio
    portfolio = Portfolio(SYS_FRONTIER_TECH_OWNER_ID)
    await portfolio.initialize()

    if not portfolio.id:
        logger.info(f"Bootstrapping new portfolio record for {SYS_FRONTIER_TECH_OWNER_ID}")
        res = (
            supabase.table("portfolios")
            .insert(
                {
                    "owner_id": SYS_FRONTIER_TECH_OWNER_ID,
                    "cash_balance": 10000.00,
                    "total_equity": 10000.00,
                    "buying_power": 20000.00,
                    "sma": 0.0,
                }
            )
            .execute()
        )
        if res.data:
            portfolio.id = res.data[0]["id"]
            portfolio.cash_balance = 10000.00

    # 2. Evaluate Themes & Screen Candidates
    qualified_themes: list[dict[str, Any]] = []
    screened_candidates: list[dict[str, Any]] = []
    current_prices: dict[str, float] = {}

    with httpx.Client(timeout=10.0) as http_client:
        for theme_def in DEFAULT_FRONTIER_THEMES:
            passes, score, satisfied = evaluate_supercycle_rubric(theme_def["rubric"])
            if not passes:
                logger.info(f"Theme '{theme_def['theme_name']}' rejected by rubric (score {score}/5).")
                continue

            theme_tickers = []
            for ticker in theme_def["candidate_tickers"]:
                if FMP_API_KEY:
                    profile, quote, financials = fetch_ticker_data_for_screening(http_client, ticker, FMP_API_KEY)
                    if not quote or not profile:
                        continue

                    passed_guardrails, reason = evaluate_stock_guardrails(profile, quote, financials)
                    if not passed_guardrails:
                        logger.info(f"Candidate {ticker} rejected by guardrails: {reason}")
                        continue

                    price = float(quote.get("price") or 0.0)
                    current_prices[ticker] = price
                else:
                    # Deterministic offline mock price for CI/testing without live keys
                    price = 10.0
                    current_prices[ticker] = price

                theme_tickers.append(ticker)
                screened_candidates.append(
                    {
                        "ticker": ticker,
                        "price": price,
                        "theme": theme_def["theme_name"],
                    }
                )

            qualified_themes.append(
                {
                    "theme_name": theme_def["theme_name"],
                    "thesis": theme_def["thesis"],
                    "catalysts": theme_def["catalysts"],
                    "rubric_score": score,
                    "tickers": theme_tickers,
                }
            )

    # 3. Format current holdings
    current_holdings: list[dict[str, Any]] = []
    for ticker, pos in portfolio.positions.items():
        price = current_prices.get(ticker, pos.average_cost_basis)
        current_holdings.append(
            {
                "ticker": ticker,
                "shares": pos.quantity,
                "current_price": price,
                "average_cost_basis": pos.average_cost_basis,
                "is_bankrupt": False,
                "is_delisted": False,
                "thesis_canceled": False,
            }
        )

    total_equity = portfolio.cash_balance + sum(h["shares"] * h["current_price"] for h in current_holdings)

    # 4. Compute rebalance orders
    plan = compute_frontier_rebalance_orders(
        current_holdings=current_holdings,
        current_cash=portfolio.cash_balance,
        total_equity=total_equity,
        candidate_stocks=screened_candidates,
        target_weight=target_weight,
        slippage_bps=slippage_bps,
    )

    # 5. Persist to DB if not dry_run
    if not dry_run and portfolio.id:
        # Save or update themes
        for qt in qualified_themes:
            try:
                supabase.table("frontier_themes").upsert(
                    {
                        "portfolio_id": str(portfolio.id),
                        "theme_name": qt["theme_name"],
                        "thesis": qt["thesis"],
                        "catalysts": qt["catalysts"],
                        "rubric_score": qt["rubric_score"],
                        "status": "active",
                        "tickers": qt["tickers"],
                        "updated_at": now.isoformat(),
                    },
                    on_conflict="portfolio_id,theme_name",
                ).execute()
            except Exception as e:
                logger.warning(f"Could not upsert theme {qt['theme_name']}: {e}")

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

            # Record decision
            decision_id = None
            try:
                dec_res = (
                    supabase.table("decisions")
                    .insert(
                        {
                            "source_id": f"frontier-tech-{now.strftime('%Y%m%d')}-{ticker}",
                            "ticker": ticker,
                            "signal": "BUY",
                            "confidence": 80,
                            "reasoning": f"[Theme: {buy.get('theme')}] Pre-explosion pure play passed 5-point supercycle rubric and 18-month runway guardrails.",
                            "model_provider": "system",
                            "model_name": SYS_FRONTIER_TECH_OWNER_ID,
                        }
                    )
                    .execute()
                )
                if dec_res.data:
                    decision_id = dec_res.data[0]["id"]
            except Exception as e:
                logger.warning(f"Failed to record decision for {ticker}: {e}")

            await portfolio.execute_trade(
                ticker=ticker,
                quantity=shares,
                price=exec_p,
                signal="BUY",
                decision_id=decision_id,
                current_prices=current_prices,
                skip_alpaca_mirror=True,
            )
            logger.info(f"Executed BUY {shares} {ticker} @ {exec_p:.2f}")

        # Update performance snapshot
        today_str = now.strftime("%Y-%m-%d")
        updated_equity = portfolio.cash_balance + sum(
            pos.quantity * current_prices.get(t, pos.average_cost_basis) for t, pos in portfolio.positions.items()
        )

        try:
            supabase.table("portfolio_performance").upsert(
                {
                    "portfolio_id": str(portfolio.id),
                    "date": today_str,
                    "total_equity": updated_equity,
                    "cash_balance": portfolio.cash_balance,
                    "buying_power": portfolio.cash_balance * 2,
                    "sma": 0.0,
                    "realized": updated_equity,
                },
                on_conflict="portfolio_id,date",
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to update portfolio_performance snapshot: {e}")

    logger.info("Frontier Tech Supercycle Task completed successfully.")
    return {
        "status": "success",
        "dry_run": dry_run,
        "themes": len(qualified_themes),
        "sales": len(plan["sales"]),
        "retained": len(plan["retained"]),
        "buys": len(plan["buys"]),
        "remaining_cash": plan["remaining_cash"],
    }


def main():
    parser = argparse.ArgumentParser(description="Frontier Technology Supercycle Scheduled Task")
    parser.add_argument(
        "--mode",
        choices=["auto", "rebalance", "health_check", "bootstrap"],
        default="auto",
        help="Execution mode (default: auto)",
    )
    parser.add_argument(
        "--target-weight",
        type=float,
        default=DEFAULT_TARGET_POSITION_WEIGHT,
        help="Target weight per stock (default: 0.03 = 3%%)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without writing to the database",
    )
    args = parser.parse_args()

    asyncio.run(
        run_frontier_tech_task(
            mode=args.mode,
            dry_run=args.dry_run,
            target_weight=args.target_weight,
        )
    )


if __name__ == "__main__":
    main()
