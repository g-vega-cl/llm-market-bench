"""Systematic 30-Day and 90-Day Sector Horizon Trading Engine.

Executes and manages multi-week horizon sector portfolios:
1. sys-sector-ls-30d: 30-Day Consensus Sector Long/Short Strategy.
2. sys-sector-ls-90d: 90-Day Consensus Sector Long/Short Strategy.
"""

from datetime import date, datetime, timedelta
from typing import Any

from core.config import logger
from core.db import get_supabase_client
from execution.system_portfolios import (
    SYS_SECTOR_LS_30D_OWNER_ID,
    SYS_SECTOR_LS_90D_OWNER_ID,
    SYS_SECTOR_START_DATE,
    get_or_create_system_portfolio,
)

HORIZON_PORTFOLIO_CONFIGS = [
    {
        "timeframe": "30d",
        "owner_id": SYS_SECTOR_LS_30D_OWNER_ID,
        "holding_days": 30,
        "name": "30-Day Consensus Sector L/S",
    },
    {
        "timeframe": "90d",
        "owner_id": SYS_SECTOR_LS_90D_OWNER_ID,
        "holding_days": 90,
        "name": "90-Day Consensus Sector L/S",
    },
]


async def execute_horizon_sector_entries(
    today_str: str,
    price_map: dict[str, float],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute new cycle entries for 30d and 90d portfolios if no open positions exist."""
    client = get_supabase_client()
    results = {}

    for cfg in HORIZON_PORTFOLIO_CONFIGS:
        owner_id = cfg["owner_id"]
        timeframe = cfg["timeframe"]

        try:
            portfolio = await get_or_create_system_portfolio(owner_id)

            # Check if this portfolio currently has active positions or open trades
            pos_res = (
                client.table("portfolio_positions").select("ticker").eq("portfolio_id", str(portfolio.id)).execute()
            )
            open_trades_res = (
                client.table("trades")
                .select("id, executed_at")
                .eq("portfolio_id", str(portfolio.id))
                .is_("realized_pnl", "null")
                .execute()
            )

            has_open_positions = bool(pos_res.data or open_trades_res.data)
            if has_open_positions:
                holding_days = cfg["holding_days"]
                today_date = date.fromisoformat(today_str)
                entry_dates = [
                    datetime.fromisoformat(t["executed_at"].replace("Z", "+00:00")).date()
                    for t in (open_trades_res.data or [])
                    if t.get("executed_at")
                ]
                matured = False
                if entry_dates:
                    earliest_entry = min(entry_dates)
                    maturity_date = earliest_entry + timedelta(days=holding_days)
                    if today_date >= maturity_date:
                        logger.info(
                            f"Portfolio {owner_id} entered on {earliest_entry} reached maturity ({maturity_date}). Liquidating matured cycle before re-entry."
                        )
                        from execution.sector_trading import execute_system_sector_exit

                        await execute_system_sector_exit(
                            week_end_date=today_str,
                            price_map=price_map,
                            owner_id=owner_id,
                            dry_run=dry_run,
                        )
                        portfolio = await get_or_create_system_portfolio(owner_id)
                        matured = True

                if not matured:
                    logger.info(f"Portfolio {owner_id} already has active open positions. Skipping new entry.")
                    results[owner_id] = {
                        "status": "skipped",
                        "reason": "Active positions exist",
                    }
                    continue

            # Query latest predictions for this specific timeframe
            preds_res = (
                client.table("sector_predictions")
                .select("*")
                .eq("timeframe", timeframe)
                .lte("prediction_date", today_str)
                .order("prediction_date", desc=True)
                .limit(10)
                .execute()
            )
            raw_preds = preds_res.data or []
            if not raw_preds:
                logger.info(f"No {timeframe} predictions found for {owner_id}.")
                results[owner_id] = {"status": "skipped", "reason": "No predictions"}
                continue

            # Scope strictly to latest prediction_date in this batch
            pred_dates = [p["prediction_date"] for p in raw_preds if p.get("prediction_date")]
            if not pred_dates:
                continue
            latest_pred_date = max(pred_dates)
            scoped_preds = [p for p in raw_preds if p.get("prediction_date") == latest_pred_date]

            from execution.sector_trading import execute_system_sector_entry

            res = await execute_system_sector_entry(
                week_start_date=today_str,
                predictions=scoped_preds,
                price_map=price_map,
                owner_id=owner_id,
                dry_run=dry_run,
            )
            results[owner_id] = res

        except Exception as e:
            logger.exception(f"Failed to execute horizon entry for {owner_id}: {e}")
            results[owner_id] = {"status": "error", "error": str(e)}

    return results


async def execute_horizon_sector_exits(
    today_str: str,
    price_map: dict[str, float],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute cycle exits for 30d and 90d portfolios if their target date has arrived."""
    client = get_supabase_client()
    today_date = date.fromisoformat(today_str)
    results = {}

    for cfg in HORIZON_PORTFOLIO_CONFIGS:
        owner_id = cfg["owner_id"]
        holding_days = cfg["holding_days"]

        try:
            portfolio = await get_or_create_system_portfolio(owner_id)

            # Query open entry trades
            trades_res = (
                client.table("trades")
                .select("id, executed_at, ticker, signal")
                .eq("portfolio_id", str(portfolio.id))
                .is_("realized_pnl", "null")
                .execute()
            )
            open_trades = trades_res.data or []
            if not open_trades:
                results[owner_id] = {"status": "skipped", "reason": "No open trades"}
                continue

            # Determine entry date from earliest open trade
            entry_dates = [
                datetime.fromisoformat(t["executed_at"].replace("Z", "+00:00")).date()
                for t in open_trades
                if t.get("executed_at")
            ]
            if not entry_dates:
                continue

            earliest_entry = min(entry_dates)
            maturity_date = earliest_entry + timedelta(days=holding_days)

            # Exit only if today is on or after maturity date
            if today_date < maturity_date:
                days_left = (maturity_date - today_date).days
                logger.info(
                    f"Portfolio {owner_id} entered on {earliest_entry} matures on {maturity_date} ({days_left}d remaining). Skipping exit."
                )
                results[owner_id] = {
                    "status": "holding",
                    "maturity_date": maturity_date.isoformat(),
                    "days_remaining": days_left,
                }
                continue

            active_price_map = dict(price_map) if price_map else {}
            needed = [t["ticker"] for t in open_trades if t.get("ticker") and t["ticker"] not in active_price_map]
            if needed:
                from execution.market_data import MarketDataManager

                mdm = MarketDataManager()
                quotes = await mdm.get_quotes(needed, force_refresh=True)
                for t, q in quotes.items():
                    if q.price > 0:
                        active_price_map[t] = float(q.price)

            from execution.sector_trading import execute_system_sector_exit

            res = await execute_system_sector_exit(
                week_end_date=today_str,
                price_map=active_price_map,
                owner_id=owner_id,
                dry_run=dry_run,
            )
            results[owner_id] = res

        except Exception as e:
            logger.exception(f"Failed to execute horizon exit for {owner_id}: {e}")
            results[owner_id] = {"status": "error", "error": str(e)}

    return results


async def backfill_sector_horizon_portfolios(
    start_date: str = SYS_SECTOR_START_DATE,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Replay historical discrete cycles for 30d and 90d sector portfolios from inception."""
    client = get_supabase_client()
    results = {}

    for cfg in HORIZON_PORTFOLIO_CONFIGS:
        owner_id = cfg["owner_id"]
        timeframe = cfg["timeframe"]

        try:
            # Query evaluated predictions for this timeframe >= start_date
            preds_res = (
                client.table("sector_predictions")
                .select("*")
                .eq("timeframe", timeframe)
                .gte("prediction_date", start_date)
                .order("prediction_date", desc=False)
                .execute()
            )
            preds = preds_res.data or []
            if not preds:
                results[owner_id] = {"status": "skipped", "reason": "No predictions found"}
                continue

            # Group by discrete cycles: (prediction_date, target_date)
            cycle_windows: dict[tuple[str, str], list[dict]] = {}
            for p in preds:
                w_key = (p["prediction_date"], p["target_date"])
                cycle_windows.setdefault(w_key, []).append(p)

            cycle_results = []
            last_end_date = None

            # Sort cycles chronologically
            for (w_start, w_end), cycle_preds in sorted(cycle_windows.items()):
                # Discrete cycle condition: only take non-overlapping cycles (w_start >= last_end_date)
                if last_end_date and w_start < last_end_date:
                    continue

                # Extract price_map from evaluation_audit_data if available
                price_map: dict[str, dict[str, float]] = {}
                for p in cycle_preds:
                    audit = p.get("evaluation_audit_data") or {}
                    for key in ("sector", "worst_sector"):
                        item = audit.get(key)
                        if isinstance(item, dict) and item.get("ticker"):
                            t = item["ticker"].upper()
                            if item.get("start_price") and item.get("end_price"):
                                price_map[t] = {
                                    "start_price": float(item["start_price"]),
                                    "end_price": float(item["end_price"]),
                                }

                all_evaluated = all(p.get("status") == "evaluated" for p in cycle_preds)
                if all_evaluated and price_map and not dry_run:
                    from execution.system_portfolios import execute_system_sector_rebalance

                    reb_res = await execute_system_sector_rebalance(
                        week_start_date=w_start,
                        week_end_date=w_end,
                        predictions=cycle_preds,
                        price_map=price_map,
                        owner_id=owner_id,
                    )
                    cycle_results.append(reb_res)
                else:
                    cycle_results.append(
                        {
                            "window": (w_start, w_end),
                            "status": "evaluated" if all_evaluated else "pending",
                            "has_prices": bool(price_map),
                        }
                    )
                last_end_date = w_end

            results[owner_id] = {"status": "success", "cycles": cycle_results}

        except Exception as e:
            logger.exception(f"Failed to backfill {owner_id}: {e}")
            results[owner_id] = {"status": "error", "error": str(e)}

    return results
