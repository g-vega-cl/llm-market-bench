"""System portfolios analytics and inspection report generator."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.db import get_supabase_client

logger = logging.getLogger("engine")

STRATEGY_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "sys-sector-mean-reversion": {
        "name": "7-Day Sector Mean Reversion",
        "category": "mean_reversion",
        "signal": "Oversold Sector Reversal: Allocates to the 2 worst-performing sector ETFs over trailing 7 days anticipating a weekly mean-reverting bounce.",
    },
    "sys-sector-naive-momentum": {
        "name": "20-Day Unconstrained Momentum",
        "category": "momentum",
        "signal": "Trend Continuation: Allocates to the 2 highest-returning sector ETFs over trailing 20 days without correlation constraints.",
    },
    "sys-sector-uncorr-7d": {
        "name": "7-Day Uncorrelated Momentum",
        "category": "momentum",
        "signal": "Uncorrelated Trend: Top sector ETF pair with |Pearson corr| < 0.30 and positive 7-day momentum.",
    },
    "sys-sector-uncorr-20d": {
        "name": "20-Day Uncorrelated Momentum",
        "category": "momentum",
        "signal": "Uncorrelated Trend: Top sector ETF pair with |Pearson corr| < 0.30 and positive 20-day momentum.",
    },
    "sys-sector-ls-consensus": {
        "name": "Weekly Sector Long/Short Consensus",
        "category": "sector_ls",
        "signal": "Multi-Model Sector Spread: 50% Long clean consensus top sectors, 50% Short clean consensus worst sectors with conflict netting.",
    },
    "sys-sector-ls-30d": {
        "name": "30-Day Sector Long/Short Consensus",
        "category": "sector_ls",
        "signal": "Medium-Term Sector Spread: 30-day holding cycle capturing macro regime shifts.",
    },
    "sys-sector-ls-90d": {
        "name": "90-Day Sector Long/Short Consensus",
        "category": "sector_ls",
        "signal": "Quarterly Sector Spread: 90-day holding cycle capturing monetary policy and earnings cycle dispersion.",
    },
    "sys-future-forces": {
        "name": "Multi-Horizon Thematic Forces",
        "category": "thematic",
        "signal": "Secular Catalysts: Liquid US equities expressing unpriced 2-24m macro forces with active falsification sentinel.",
    },
    "sys-frontier-tech": {
        "name": "Frontier Technology Supercycles",
        "category": "thematic",
        "signal": "Small-Cap Supercycles: Pure-play pre-explosion equities scored against a 5-point supercycle rubric.",
    },
}


def _matches_category(owner_id: str, category: str) -> bool:
    """Check if owner_id belongs to the requested category."""
    cat = category.lower().strip()
    if cat in ("all", "*"):
        return True

    info = STRATEGY_DESCRIPTIONS.get(owner_id)
    if info and info["category"] == cat:
        return True

    if cat == "daily_spy" and owner_id.startswith("sys-daily-spy"):
        return True
    if cat == "sector_ls" and owner_id.startswith("sys-sector-ls"):
        return True
    if cat == "momentum" and ("mom" in owner_id or "uncorr" in owner_id):
        return True
    if cat == "mean_reversion" and "mean-rev" in owner_id:
        return True
    return cat == "thematic" and owner_id in ("sys-future-forces", "sys-frontier-tech")


async def execute_get_system_portfolios_tool(
    category: str = "all",
    include_positions: bool = True,
    lookback_days: int = 7,
) -> str:
    """Inspect mechanical system portfolios (mean reversion, momentum, sector L/S, daily SPY).

    Args:
        category: 'all', 'mean_reversion', 'momentum', 'sector_ls', 'daily_spy', or 'thematic'.
        include_positions: Whether to list active stock/ETF holdings, prices, and unrealized PnL.
        lookback_days: Trailing window in days to compute portfolio return and equity drift.

    Returns:
        Formatted markdown summary of system portfolios, current positions, and quantitative signals.
    """
    try:
        client = get_supabase_client()

        # 1. Fetch system portfolios
        p_res = (
            client.table("portfolios")
            .select("id, owner_id, cash_balance, total_equity, buying_power")
            .like("owner_id", "sys-%")
            .execute()
        )
        all_portfolios: list[dict[str, Any]] = p_res.data or []

        matched_portfolios = [p for p in all_portfolios if _matches_category(p.get("owner_id", ""), category)]
        if not matched_portfolios:
            return f"No system portfolios found matching category '{category}'."

        matched_pids = {p["id"] for p in matched_portfolios}

        # 2. Fetch active positions if requested
        positions_by_pid: dict[str, list[dict[str, Any]]] = {}
        if include_positions:
            pos_res = (
                client.table("position_pnl")
                .select(
                    "portfolio_id, owner_id, ticker, quantity, average_cost_basis, current_price, unrealized_pnl_usd, unrealized_pnl_pct"
                )
                .execute()
            )
            for pos in pos_res.data or []:
                pid = pos.get("portfolio_id")
                qty = float(pos.get("quantity", 0))
                if pid in matched_pids and abs(qty) > 0:
                    pos_dict = dict(pos)
                    pos_dict["side"] = "LONG"
                    positions_by_pid.setdefault(pid, []).append(pos_dict)

            try:
                short_res = (
                    client.table("trades")
                    .select("portfolio_id, ticker, quantity, price, executed_at")
                    .eq("signal", "SHORT")
                    .is_("realized_pnl", "null")
                    .execute()
                )
                open_shorts = short_res.data or []
                if open_shorts:
                    short_tickers = list({s["ticker"] for s in open_shorts if s.get("ticker")})
                    cache_res = (
                        client.table("market_data_cache").select("ticker, price").in_("ticker", short_tickers).execute()
                    )
                    price_cache = {
                        item["ticker"]: float(item["price"])
                        for item in (cache_res.data or [])
                        if item.get("ticker") and item.get("price") is not None
                    }
                    for s in open_shorts:
                        pid = s.get("portfolio_id")
                        if pid in matched_pids:
                            qty = float(s.get("quantity", 0))
                            avg_cost = float(s.get("price", 0.0) or 0.0)
                            curr_p = price_cache.get(s.get("ticker", ""), avg_cost)
                            pnl_usd = (avg_cost - curr_p) * qty
                            pnl_pct = ((avg_cost - curr_p) / avg_cost * 100.0) if avg_cost > 0 else 0.0
                            positions_by_pid.setdefault(pid, []).append(
                                {
                                    "portfolio_id": pid,
                                    "ticker": s.get("ticker"),
                                    "quantity": qty,
                                    "average_cost_basis": avg_cost,
                                    "current_price": curr_p,
                                    "unrealized_pnl_usd": pnl_usd,
                                    "unrealized_pnl_pct": pnl_pct,
                                    "side": "SHORT",
                                }
                            )
            except Exception as e:
                logger.debug("Failed to query open shorts in execute_get_system_portfolios_tool: %s", e)

        # 3. Fetch performance trajectory over lookback
        perf_by_pid: dict[str, list[dict[str, Any]]] = {}
        cutoff_date = (datetime.now(UTC) - timedelta(days=lookback_days)).date().isoformat()
        try:
            perf_res = (
                client.table("portfolio_performance")
                .select("portfolio_id, date, total_equity")
                .gte("date", cutoff_date)
                .order("date", desc=False)
                .execute()
            )
            for snap in perf_res.data or []:
                pid = snap.get("portfolio_id")
                if pid in matched_pids:
                    perf_by_pid.setdefault(pid, []).append(snap)
        except Exception as e:
            logger.debug("Failed to query portfolio_performance in execute_get_system_portfolios_tool: %s", e)

        # 4. Format report
        lines = [
            f"=== SYSTEM PORTFOLIOS & MECHANICAL BENCHMARKS (Category: {category.upper()}, Lookback: {lookback_days}d) ===",
            "Mechanical control strategies provide objective baselines for mean reversion, momentum, and sector rotation.",
            "",
        ]

        for p in sorted(matched_portfolios, key=lambda x: str(x.get("owner_id", ""))):
            pid = str(p.get("id", ""))
            owner_id = str(p.get("owner_id", ""))
            equity = float(p.get("total_equity", 0.0) or 0.0)
            cash = float(p.get("cash_balance", 0.0) or 0.0)
            strat_meta = STRATEGY_DESCRIPTIONS.get(owner_id, {})
            strat_name = strat_meta.get("name", owner_id)
            strat_signal = strat_meta.get("signal", "Systematic execution strategy.")

            # Calculate trailing return
            return_str = "N/A"
            snaps = perf_by_pid.get(pid, [])
            if len(snaps) >= 2:
                start_eq = float(snaps[0].get("total_equity", 0.0) or 0.0)
                end_eq = float(snaps[-1].get("total_equity", 0.0) or 0.0)
                if start_eq > 0:
                    ret_pct = ((end_eq - start_eq) / start_eq) * 100.0
                    return_str = f"{ret_pct:+.2f}% (${start_eq:,.2f} -> ${end_eq:,.2f})"

            lines.append(f"### {strat_name} (`{owner_id}`)")
            lines.append(f"- Strategy: {strat_signal}")
            lines.append(f"- Total Equity: ${equity:,.2f} | Cash: ${cash:,.2f} | {lookback_days}d Return: {return_str}")

            if include_positions:
                pos_list = positions_by_pid.get(pid, [])
                if pos_list:
                    lines.append("- Active Holdings:")
                    for pos in pos_list:
                        ticker = pos.get("ticker", "UNKNOWN")
                        qty = pos.get("quantity", 0)
                        avg_cost = float(pos.get("average_cost_basis", 0.0) or 0.0)
                        curr_p = float(pos.get("current_price", 0.0) or 0.0)
                        pnl_usd = float(pos.get("unrealized_pnl_usd", 0.0) or 0.0)
                        pnl_pct = float(pos.get("unrealized_pnl_pct", 0.0) or 0.0)
                        side_tag = " [SHORT]" if pos.get("side") == "SHORT" else ""
                        cost_label = "Short Entry" if pos.get("side") == "SHORT" else "Avg Cost"
                        lines.append(
                            f"  * {ticker}{side_tag}: {qty:g} shares | {cost_label}: ${avg_cost:.2f} | "
                            f"Current Price: ${curr_p:.2f} | Unrealized PnL: ${pnl_usd:+,.2f} ({pnl_pct:+.2f}%)"
                        )
                else:
                    lines.append("- Active Holdings: None (100% Cash)")
            else:
                lines.append("- Holdings: omitted")

            lines.append("")

        return "\n".join(lines).strip()

    except Exception as e:
        logger.exception("Error executing get_system_portfolios tool: %s", e)
        return f"Error retrieving system portfolios: {str(e)}"
