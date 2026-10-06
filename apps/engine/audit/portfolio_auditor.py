"""System Portfolio Health Auditor and Reconciliation Island.

Audits systematic portfolios (Daily SPY and Sector Strategies) to detect:
1. Missing daily SPY trades when daily predictions exist.
2. Unliquidated weekly sector positions past Friday market close.
3. Desynced cash or equity metrics.

In '--fix' / 'auto_heal' mode, reconstructs missing trades using canonical
historical session prints and standard model slippage, marking trade records
with `alpaca_status = "BACKFILLED"`.
"""

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from core.config import logger
from core.db import get_supabase_client
from execution.daily_trading import (
    SYS_DAILY_SPY_CLOSE_OWNER_PREFIX,
    SYS_DAILY_SPY_OWNER_PREFIX,
    execute_system_daily_close_trade,
    execute_system_daily_trade,
)
from execution.portfolio import Portfolio

WEEKLY_SECTOR_PORTFOLIOS = [
    "sys-sector-ls-consensus",
    "sys-sector-mean-reversion",
    "sys-sector-naive-momentum",
    "sys-sector-uncorr-20d",
    "sys-sector-uncorr-7d",
]


def _get_trading_dates(target_date: str | None, lookback_days: int) -> list[str]:
    """Compute list of weekday ISO date strings for the audit window."""
    if target_date:
        return [target_date]

    dates: list[str] = []
    curr = date.today()
    checked = 0
    while len(dates) < lookback_days and checked < 30:
        if curr.weekday() < 5:  # Monday to Friday
            dates.append(curr.isoformat())
        curr -= timedelta(days=1)
        checked += 1
    return dates


async def audit_system_portfolios(
    target_date: str | None = None,
    lookback_days: int = 5,
    auto_heal: bool = False,
    supabase_client: Any = None,
) -> dict[str, Any]:
    """Audit systematic portfolios for missing executions, unclosed positions, and data anomalies.

    Args:
        target_date: Specific ISO date (YYYY-MM-DD) to audit. Defaults to lookback window.
        lookback_days: Number of trading sessions to look back (default 5).
        auto_heal: If True, reconstructs missing trades with alpaca_status="BACKFILLED".
        supabase_client: Optional injected database client (for hermetic unit tests).
    """
    client = supabase_client or get_supabase_client()
    dates_to_check = _get_trading_dates(target_date, lookback_days)
    dates_to_check.sort()

    anomalies: list[dict[str, Any]] = []
    healed: list[dict[str, Any]] = []
    flagged_for_review: list[dict[str, Any]] = []

    # 1. Fetch system portfolios
    portfolios_res = (
        client.table("portfolios")
        .select("id, owner_id, cash_balance, total_equity")
        .like("owner_id", "sys-%")
        .execute()
    )
    portfolios = portfolios_res.data or []
    port_by_owner = {p["owner_id"]: p for p in portfolios}

    async def _portfolio_getter(oid: str) -> Portfolio:
        port = Portfolio(oid)
        if oid in port_by_owner:
            raw_id = port_by_owner[oid]["id"]
            try:
                port.id = UUID(str(raw_id))
            except Exception:
                port.id = raw_id  # In test mocks or non-standard IDs
            port.cash_balance = float(port_by_owner[oid]["cash_balance"])
        return port

    for d in dates_to_check:
        # Check daily SPY predictions for date d
        preds_res = client.table("daily_predictions").select("*").eq("target_date", d).execute()
        predictions = preds_res.data or []

        for pred in predictions:
            model_name = str(pred.get("model_name", "unknown"))
            exp_ret_raw = pred.get("expected_return_pct")
            target_pct = abs(float(exp_ret_raw)) if exp_ret_raw is not None else 0.0

            target_owners = [f"{SYS_DAILY_SPY_CLOSE_OWNER_PREFIX}{model_name}"]
            if "jev" not in model_name.lower() and target_pct > 0.0:
                target_owners.append(f"{SYS_DAILY_SPY_OWNER_PREFIX}{model_name}")

            for owner_id in target_owners:
                p = port_by_owner.get(owner_id)
                if not p:
                    continue

                portfolio_id = p["id"]
                trades_res = (
                    client.table("trades")
                    .select("id, signal, price, quantity, executed_at, alpaca_status")
                    .eq("portfolio_id", portfolio_id)
                    .gte("executed_at", f"{d}T00:00:00Z")
                    .lte("executed_at", f"{d}T23:59:59Z")
                    .execute()
                )
                trades = trades_res.data or []

                entry_trade = next(
                    (t for t in trades if t.get("signal") in ("BUY", "SHORT")),
                    trades[0] if trades else None,
                )
                exit_trade = next(
                    (t for t in trades if t.get("signal") in ("SELL", "COVER")),
                    None,
                )
                open_p = float(pred.get("open_price") or 0.0)
                entry_price = float(entry_trade.get("price") or 0.0) if entry_trade else 0.0

                is_missing_trades = len(trades) < 2
                has_invalid_entry = False
                has_unclosed_short = False

                if not is_missing_trades and open_p > 0 and entry_price > 0:
                    drift_pct = abs(entry_price - open_p) / open_p
                    if drift_pct > 0.002:  # > 0.2% drift from beginning-of-day open
                        has_invalid_entry = True

                if (
                    not is_missing_trades
                    and entry_trade
                    and entry_trade.get("signal") == "SHORT"
                    and entry_trade.get("realized_pnl") is None
                    and exit_trade
                    and exit_trade.get("signal") == "COVER"
                    and exit_trade.get("realized_pnl") is not None
                ):
                    has_unclosed_short = True

                if has_unclosed_short and not (is_missing_trades or has_invalid_entry):
                    anomaly = {
                        "date": d,
                        "portfolio_id": portfolio_id,
                        "owner_id": owner_id,
                        "type": "UNCLOSED_SHORT_DAILY_SPY",
                        "model_name": model_name,
                        "details": f"Entry SHORT trade {entry_trade['id']} has NULL realized_pnl despite matching COVER trade on {d}",
                    }
                    anomalies.append(anomaly)
                    logger.warning(f"Portfolio health anomaly: {anomaly['details']} on {owner_id} ({d})")

                    if auto_heal:
                        cover_pnl = float(exit_trade["realized_pnl"])
                        cover_pnl_pct = float(exit_trade.get("realized_pnl_pct") or 0.0)
                        client.table("trades").update(
                            {"realized_pnl": cover_pnl, "realized_pnl_pct": cover_pnl_pct}
                        ).eq("id", entry_trade["id"]).execute()
                        healed.append(
                            {
                                "date": d,
                                "portfolio_id": portfolio_id,
                                "owner_id": owner_id,
                                "type": "UNCLOSED_SHORT_DAILY_SPY",
                                "action": "HEALED_UNCLOSED_SHORT",
                                "details": f"Healed entry SHORT trade {entry_trade['id']} with realized PnL ${cover_pnl:,.2f}",
                            }
                        )

                elif is_missing_trades or has_invalid_entry:
                    anomaly_type = "MISSING_DAILY_SPY_TRADE" if is_missing_trades else "INVALID_ENTRY_PRICE_DAILY_SPY"
                    details = (
                        f"Expected 2 trades (entry + exit) for {d}, found {len(trades)}"
                        if is_missing_trades
                        else f"Daily SPY entry price ${entry_price:.2f} desynced from session open ${open_p:.2f} (drift {drift_pct:.2%})"
                    )
                    anomaly = {
                        "date": d,
                        "portfolio_id": portfolio_id,
                        "owner_id": owner_id,
                        "type": anomaly_type,
                        "model_name": model_name,
                        "details": details,
                    }
                    anomalies.append(anomaly)
                    logger.warning(f"Portfolio health anomaly: {anomaly['details']} on {owner_id} ({d})")

                    if auto_heal and open_p > 0:
                        # Extract session OHLC prices from prediction or fetch fallback
                        high_p = float(pred.get("high_price") or open_p)
                        low_p = float(pred.get("low_price") or open_p)
                        close_p = float(pred.get("close_price") or open_p)

                        intraday_data = {
                            "open_price": open_p,
                            "high_price": high_p,
                            "low_price": low_p,
                            "close_price": close_p,
                            "intraday_hit": bool(pred.get("intraday_hit", False)),
                        }

                        # Prior trading session equity
                        prior_perf_res = (
                            client.table("portfolio_performance")
                            .select("total_equity")
                            .eq("portfolio_id", portfolio_id)
                            .lt("date", d)
                            .order("date", desc=True)
                            .limit(1)
                            .execute()
                        )
                        prior_perf_data = prior_perf_res.data if isinstance(prior_perf_res.data, list) else []
                        prior_equity = (
                            float(prior_perf_data[0]["total_equity"])
                            if (
                                prior_perf_data
                                and isinstance(prior_perf_data[0].get("total_equity"), (int, float, str))
                            )
                            else float(p.get("cash_balance") or 10000.0)
                        )

                        # Clean any existing trades for date d before executing
                        client.table("trades").delete().eq("portfolio_id", portfolio_id).gte(
                            "executed_at", f"{d}T00:00:00Z"
                        ).lte("executed_at", f"{d}T23:59:59Z").execute()
                        client.table("portfolio_positions").delete().eq("portfolio_id", portfolio_id).eq(
                            "ticker", "SPY"
                        ).execute()

                        # Reset portfolio cash to prior_equity
                        p["cash_balance"] = prior_equity
                        client.table("portfolios").update(
                            {"cash_balance": prior_equity, "total_equity": prior_equity}
                        ).eq("id", portfolio_id).execute()

                        if owner_id.startswith(SYS_DAILY_SPY_CLOSE_OWNER_PREFIX):
                            res = await execute_system_daily_close_trade(
                                prediction=pred,
                                intraday_data=intraday_data,
                                alpaca_status="BACKFILLED",
                                get_supabase_client_fn=lambda: client,
                                get_or_create_system_portfolio_fn=_portfolio_getter,
                            )
                        else:
                            res = await execute_system_daily_trade(
                                prediction=pred,
                                intraday_data=intraday_data,
                                alpaca_status="BACKFILLED",
                                get_supabase_client_fn=lambda: client,
                                get_or_create_system_portfolio_fn=_portfolio_getter,
                            )

                        if res.get("new_equity") is not None:
                            p["cash_balance"] = res["new_equity"]

                        healed.append(
                            {
                                "date": d,
                                "owner_id": owner_id,
                                "action": "AUTO_HEALED_DAILY_SPY",
                                "new_equity": res.get("new_equity"),
                                "alpaca_status": "BACKFILLED",
                            }
                        )
                        logger.info(f"Auto-healed {owner_id} for {d}: New equity ${(res.get('new_equity') or 0):,.2f}")

    # 2. Check Weekly Sector Portfolios
    # Weekly Sector Portfolios hold positions from Monday 9:35 AM ET through Friday 15:30 ET.
    # They should be flat (0 positions) from Friday 16:00 ET through Monday 9:30 AM ET.
    # Mid-week (Monday post-open through Friday pre-close), they must hold active positions.
    from zoneinfo import ZoneInfo

    now_ny = datetime.now(ZoneInfo("America/New_York"))
    is_friday_after_close = now_ny.weekday() == 4 and now_ny.hour >= 16
    is_weekend = now_ny.weekday() in (5, 6)
    is_monday_before_open = now_ny.weekday() == 0 and (now_ny.hour < 9 or (now_ny.hour == 9 and now_ny.minute < 30))
    should_be_flat = is_friday_after_close or is_weekend or is_monday_before_open

    # When target_date is passed, determine if target_date was a weekend/Friday post-close
    if target_date:
        t_d = date.fromisoformat(target_date)
        if t_d.weekday() in (5, 6):
            should_be_flat = True
        elif t_d.weekday() < 4:
            should_be_flat = False

    for owner_id in WEEKLY_SECTOR_PORTFOLIOS:
        p = port_by_owner.get(owner_id)
        if not p:
            continue
        pid = p["id"]
        pos_res = (
            client.table("portfolio_positions")
            .select("ticker, quantity, average_cost_basis")
            .eq("portfolio_id", pid)
            .execute()
        )
        positions = pos_res.data or []

        if should_be_flat and positions:
            anomaly = {
                "date": target_date or dates_to_check[0] if dates_to_check else date.today().isoformat(),
                "portfolio_id": pid,
                "owner_id": owner_id,
                "type": "UNLIQUIDATED_WEEKLY_SECTOR_POSITION",
                "details": f"Weekly portfolio holds {len(positions)} unliquidated positions out of market hours: {[x['ticker'] for x in positions]}",
            }
            anomalies.append(anomaly)
            flagged_for_review.append(anomaly)
        elif not should_be_flat and not positions:
            # Mid-week but portfolio has 0 positions!
            anomaly = {
                "date": target_date or dates_to_check[0] if dates_to_check else date.today().isoformat(),
                "portfolio_id": pid,
                "owner_id": owner_id,
                "type": "MISSING_WEEKLY_SECTOR_ENTRY",
                "details": "Weekly portfolio has 0 active positions mid-week (missing Monday rebalance entry).",
            }
            anomalies.append(anomaly)
            flagged_for_review.append(anomaly)

    status = "clean"
    if anomalies and auto_heal and len(healed) == len(anomalies):
        status = "healed"
    elif anomalies:
        status = "anomalies_detected"

    report = {
        "status": status,
        "dates_checked": dates_to_check,
        "anomalies": anomalies,
        "healed": healed,
        "flagged_for_review": flagged_for_review,
        "summary_table_markdown": generate_markdown_summary(dates_to_check, anomalies, healed, flagged_for_review),
    }

    return report


def generate_markdown_summary(
    dates: list[str],
    anomalies: list[dict[str, Any]],
    healed: list[dict[str, Any]],
    flagged: list[dict[str, Any]],
) -> str:
    """Generate Markdown summary table for terminal logging and GitHub Actions Step Summary."""
    lines = [
        "### 🛡️ System Portfolio Health & Reconciliation Audit",
        f"**Audit Window**: {dates[-1] if dates else 'N/A'} to {dates[0] if dates else 'N/A'} ({len(dates)} sessions)",
        "",
    ]

    if not anomalies and not healed:
        lines.append("✅ **All system portfolios healthy**: Zero missing trades or stale positions detected.")
        return "\n".join(lines)

    lines.append("| Date | Portfolio | Anomaly Detected | Resolution / Status |")
    lines.append("| :--- | :--- | :--- | :--- |")

    healed_lookup = {(h["date"], h["owner_id"]): h for h in healed}

    for a in anomalies:
        d = a["date"]
        owner = a["owner_id"]
        atype = a["type"]
        h = healed_lookup.get((d, owner))

        if h:
            if "alpaca_status" in h:
                resolution = f"✅ Auto-Healed (`alpaca_status='{h['alpaca_status']}'`, Equity: ${(h.get('new_equity') or 0):,.2f})"
            else:
                resolution = f"✅ Auto-Healed ({h.get('details')})"
        else:
            resolution = "⚠️ Pending Review (Run `main.py audit-portfolios --fix`)"

        lines.append(f"| {d} | `{owner}` | {atype} | {resolution} |")

    return "\n".join(lines)


async def run_portfolio_auditor_cli(
    target_date: str | None = None,
    lookback_days: int = 5,
    fix: bool = False,
) -> None:
    """CLI Entrypoint for main.py audit-portfolios."""
    import os

    print(f"\n🔍 Running System Portfolio Health Audit (lookback={lookback_days} days, fix={fix})...")
    report = await audit_system_portfolios(
        target_date=target_date,
        lookback_days=lookback_days,
        auto_heal=fix,
    )
    markdown_table = report["summary_table_markdown"]
    print("\n" + markdown_table + "\n")

    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        try:
            with open(summary_file, "a", encoding="utf-8") as f:
                f.write("\n" + markdown_table + "\n")
        except Exception as e:
            logger.warning(f"Could not append to GITHUB_STEP_SUMMARY: {e}")
