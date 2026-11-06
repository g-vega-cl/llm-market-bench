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
from execution.daily_bond_trading import (
    SYS_DAILY_TLT_CLOSE_OWNER_PREFIX,
    execute_system_daily_bond_close_trade,
)
from execution.daily_trading import (
    INITIAL_PORTFOLIO_CASH,
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


async def _heal_missing_or_invalid_trade(
    client: Any,
    owner_id: str,
    portfolio_id: str,
    d: str,
    pred: dict[str, Any],
    p: dict[str, Any],
    ticker: str,
    open_p: float,
    portfolio_getter: Any,
) -> dict[str, Any]:
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
        if (prior_perf_data and isinstance(prior_perf_data[0].get("total_equity"), (int, float, str)))
        else INITIAL_PORTFOLIO_CASH
    )

    client.table("trades").delete().eq("portfolio_id", portfolio_id).gte("executed_at", f"{d}T00:00:00Z").lte(
        "executed_at", f"{d}T23:59:59Z"
    ).execute()
    client.table("portfolio_positions").delete().eq("portfolio_id", portfolio_id).eq("ticker", ticker).execute()

    p["cash_balance"] = prior_equity
    client.table("portfolios").update({"cash_balance": prior_equity, "total_equity": prior_equity}).eq(
        "id", portfolio_id
    ).execute()

    if owner_id.startswith(SYS_DAILY_TLT_CLOSE_OWNER_PREFIX):
        res = await execute_system_daily_bond_close_trade(
            prediction=pred,
            intraday_data=intraday_data,
        )
    elif owner_id.startswith(SYS_DAILY_SPY_CLOSE_OWNER_PREFIX):
        res = await execute_system_daily_close_trade(
            prediction=pred,
            intraday_data=intraday_data,
            alpaca_status="BACKFILLED",
            get_supabase_client_fn=lambda: client,
            get_or_create_system_portfolio_fn=portfolio_getter,
        )
    else:
        res = await execute_system_daily_trade(
            prediction=pred,
            intraday_data=intraday_data,
            alpaca_status="BACKFILLED",
            get_supabase_client_fn=lambda: client,
            get_or_create_system_portfolio_fn=portfolio_getter,
        )

    if res.get("new_equity") is not None:
        p["cash_balance"] = res["new_equity"]

    logger.info(f"Auto-healed {owner_id} for {d}: New equity ${(res.get('new_equity') or 0):,.2f}")
    return {
        "date": d,
        "owner_id": owner_id,
        "action": "AUTO_HEALED_DAILY_SPY",
        "new_equity": res.get("new_equity"),
        "alpaca_status": "BACKFILLED",
    }


def _check_desynced_performance(
    client: Any,
    portfolio_id: str,
    owner_id: str,
    d: str,
    model_name: str,
    trades: list[dict[str, Any]],
    p: dict[str, Any],
    is_last_date: bool,
    auto_heal: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
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
        if (prior_perf_data and isinstance(prior_perf_data[0].get("total_equity"), (int, float, str)))
        else INITIAL_PORTFOLIO_CASH
    )
    closing_trades = [t for t in trades if t.get("signal") in ("SELL", "COVER")]
    if not closing_trades:
        return None, None

    session_pnl = sum(float(t["realized_pnl"]) for t in closing_trades if t.get("realized_pnl") is not None)
    expected_equity = round(prior_equity + session_pnl, 2)
    curr_perf_res = (
        client.table("portfolio_performance")
        .select("total_equity")
        .eq("portfolio_id", portfolio_id)
        .eq("date", d)
        .execute()
    )
    curr_perf_data = curr_perf_res.data if isinstance(curr_perf_res.data, list) else []
    if not curr_perf_data:
        return None, None

    rec_equity = float(curr_perf_data[0]["total_equity"])
    if abs(rec_equity - expected_equity) <= 2.00:
        return None, None

    anomaly = {
        "date": d,
        "portfolio_id": portfolio_id,
        "owner_id": owner_id,
        "type": "DESYNCED_EQUITY_DAILY_SPY",
        "model_name": model_name,
        "details": (
            f"Performance equity ${rec_equity:,.2f} on {d} desynced from cumulative equity "
            f"${expected_equity:,.2f} (drift ${rec_equity - expected_equity:+,.2f})"
        ),
    }
    logger.warning(f"Portfolio health anomaly: {anomaly['details']} on {owner_id} ({d})")
    healed_item = None
    if auto_heal:
        client.table("portfolio_performance").update(
            {
                "total_equity": expected_equity,
                "cash_balance": expected_equity,
                "buying_power": expected_equity,
                "realized": expected_equity,
            }
        ).eq("portfolio_id", portfolio_id).eq("date", d).execute()
        p["cash_balance"] = expected_equity
        p["total_equity"] = expected_equity
        if is_last_date:
            client.table("portfolios").update(
                {
                    "cash_balance": expected_equity,
                    "total_equity": expected_equity,
                    "buying_power": expected_equity,
                    "realized": expected_equity,
                }
            ).eq("id", portfolio_id).execute()
        healed_item = {
            "date": d,
            "portfolio_id": portfolio_id,
            "owner_id": owner_id,
            "type": "DESYNCED_EQUITY_DAILY_SPY",
            "action": "HEALED_DESYNCED_EQUITY",
            "new_equity": expected_equity,
            "details": f"Corrected performance equity to ${expected_equity:,.2f}",
        }
    return anomaly, healed_item


async def _audit_single_prediction_owner(
    client: Any,
    owner_id: str,
    p: dict[str, Any],
    d: str,
    pred: dict[str, Any],
    ticker: str,
    model_name: str,
    is_last_date: bool,
    auto_heal: bool,
    portfolio_getter: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    anomalies: list[dict[str, Any]] = []
    healed: list[dict[str, Any]] = []
    portfolio_id = p["id"]

    trades_res = (
        client.table("trades")
        .select("id, signal, price, quantity, executed_at, alpaca_status, realized_pnl")
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
    exit_trade = next((t for t in trades if t.get("signal") in ("SELL", "COVER")), None)
    open_p = float(pred.get("open_price") or 0.0)
    entry_price = float(entry_trade.get("price") or 0.0) if entry_trade else 0.0

    is_missing_trades = len(trades) < 2
    has_invalid_entry = False
    if not is_missing_trades and open_p > 0 and entry_price > 0 and abs(entry_price - open_p) / open_p > 0.002:
        has_invalid_entry = True

    has_unclosed_short = bool(
        not is_missing_trades
        and entry_trade
        and entry_trade.get("signal") == "SHORT"
        and entry_trade.get("realized_pnl") is None
        and exit_trade
        and exit_trade.get("signal") == "COVER"
        and exit_trade.get("realized_pnl") is not None
    )

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
            client.table("trades").update({"realized_pnl": cover_pnl, "realized_pnl_pct": cover_pnl_pct}).eq(
                "id", entry_trade["id"]
            ).execute()
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
            else f"Daily SPY entry price ${entry_price:.2f} desynced from session open ${open_p:.2f}"
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
            healed_entry = await _heal_missing_or_invalid_trade(
                client, owner_id, portfolio_id, d, pred, p, ticker, open_p, portfolio_getter
            )
            healed.append(healed_entry)
    elif not is_missing_trades and not has_invalid_entry:
        anom, hld = _check_desynced_performance(
            client, portfolio_id, owner_id, d, model_name, trades, p, is_last_date, auto_heal
        )
        if anom:
            anomalies.append(anom)
        if hld:
            healed.append(hld)

    return anomalies, healed


def _audit_weekly_sector_portfolios(
    client: Any,
    port_by_owner: dict[str, Any],
    target_date: str | None,
    dates_to_check: list[str],
    now_ny: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    anomalies: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []

    is_friday_after_close = now_ny.weekday() == 4 and now_ny.hour >= 16
    is_weekend = now_ny.weekday() in (5, 6)
    is_monday_before_open = now_ny.weekday() == 0 and (now_ny.hour < 9 or (now_ny.hour == 9 and now_ny.minute < 30))
    should_be_flat = is_friday_after_close or is_weekend or is_monday_before_open

    if target_date:
        t_d = date.fromisoformat(target_date)
        if t_d.weekday() in (5, 6):
            should_be_flat = True
        elif t_d.weekday() < 4:
            should_be_flat = False

    audit_dt = target_date or (dates_to_check[0] if dates_to_check else date.today().isoformat())
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
                "date": audit_dt,
                "portfolio_id": pid,
                "owner_id": owner_id,
                "type": "UNLIQUIDATED_WEEKLY_SECTOR_POSITION",
                "details": f"Weekly portfolio holds {len(positions)} unliquidated positions out of market hours: {[x['ticker'] for x in positions]}",
            }
            anomalies.append(anomaly)
            flagged.append(anomaly)
        elif not should_be_flat and not positions:
            anomaly = {
                "date": audit_dt,
                "portfolio_id": pid,
                "owner_id": owner_id,
                "type": "MISSING_WEEKLY_SECTOR_ENTRY",
                "details": "Weekly portfolio has 0 active positions mid-week (missing Monday rebalance entry).",
            }
            anomalies.append(anomaly)
            flagged.append(anomaly)

    return anomalies, flagged


async def _audit_max_pain_portfolio(
    client: Any,
    port_by_owner: dict[str, Any],
    target_date: str | None,
    dates_to_check: list[str],
    now_ny: datetime,
    auto_heal: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    from execution.max_pain import SYS_MAX_PAIN_OWNER_ID, reconcile_unliquidated_max_pain_positions

    anomalies: list[dict[str, Any]] = []
    healed: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []

    mp_port = port_by_owner.get(SYS_MAX_PAIN_OWNER_ID)
    if not mp_port:
        return anomalies, healed, flagged

    mp_pid = mp_port["id"]
    mp_pos_res = (
        client.table("portfolio_positions")
        .select("ticker, quantity, average_cost_basis, last_updated_at")
        .eq("portfolio_id", mp_pid)
        .execute()
    )
    mp_positions = [pos for pos in (mp_pos_res.data or []) if int(pos.get("quantity") or 0) > 0]
    if not mp_positions:
        return anomalies, healed, flagged

    today_ny_str = now_ny.date().isoformat()
    is_after_daily_close = (
        now_ny.hour >= 16
        or now_ny.weekday() in (5, 6)
        or now_ny.hour < 9
        or (now_ny.hour == 9 and now_ny.minute < 30)
        or bool(target_date and target_date < today_ny_str)
        or any(str(pos.get("last_updated_at") or "")[:10] < today_ny_str for pos in mp_positions)
    )
    if is_after_daily_close:
        mp_audit_date = target_date or (dates_to_check[-1] if dates_to_check else today_ny_str)
        anomaly = {
            "date": mp_audit_date,
            "portfolio_id": mp_pid,
            "owner_id": SYS_MAX_PAIN_OWNER_ID,
            "type": "UNLIQUIDATED_MAX_PAIN_POSITION",
            "details": f"Max Pain portfolio holds {len(mp_positions)} unliquidated 0DTE position(s) after session close: {[x['ticker'] for x in mp_positions]}",
        }
        anomalies.append(anomaly)
        if auto_heal:
            rec = await reconcile_unliquidated_max_pain_positions(
                portfolio_row=mp_port,
                positions=mp_positions,
                audit_date=mp_audit_date,
                client=client,
            )
            healed.append(
                {
                    "date": mp_audit_date,
                    "portfolio_id": mp_pid,
                    "owner_id": SYS_MAX_PAIN_OWNER_ID,
                    "type": "UNLIQUIDATED_MAX_PAIN_POSITION",
                    "action": "AUTO_HEALED_MAX_PAIN_EXIT",
                    "new_equity": rec.get("new_equity"),
                    "alpaca_status": "BACKFILLED",
                }
            )
        else:
            flagged.append(anomaly)

    return anomalies, healed, flagged


async def audit_system_portfolios(
    target_date: str | None = None,
    lookback_days: int = 5,
    auto_heal: bool = False,
    supabase_client: Any = None,
) -> dict[str, Any]:
    """Audit systematic portfolios for missing executions, unclosed positions, and data anomalies."""
    from zoneinfo import ZoneInfo

    client = supabase_client or get_supabase_client()
    dates_to_check = _get_trading_dates(target_date, lookback_days)
    dates_to_check.sort()

    anomalies: list[dict[str, Any]] = []
    healed: list[dict[str, Any]] = []
    flagged_for_review: list[dict[str, Any]] = []

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
                port.id = raw_id
            port.cash_balance = float(port_by_owner[oid]["cash_balance"])
        return port

    for d in dates_to_check:
        preds_res = client.table("daily_predictions").select("*").eq("target_date", d).execute()
        for pred in preds_res.data or []:
            model_name = str(pred.get("model_name", "unknown"))
            exp_ret_raw = pred.get("expected_return_pct")
            target_pct = abs(float(exp_ret_raw)) if exp_ret_raw is not None else 0.0
            ticker = str(pred.get("ticker", "SPY")).upper()

            if ticker == "TLT":
                target_owners = [f"{SYS_DAILY_TLT_CLOSE_OWNER_PREFIX}{model_name}"]
            else:
                target_owners = [f"{SYS_DAILY_SPY_CLOSE_OWNER_PREFIX}{model_name}"]
                if "jev" not in model_name.lower() and target_pct > 0.0:
                    target_owners.append(f"{SYS_DAILY_SPY_OWNER_PREFIX}{model_name}")

            for owner_id in target_owners:
                p = port_by_owner.get(owner_id)
                if not p:
                    continue
                a_list, h_list = await _audit_single_prediction_owner(
                    client,
                    owner_id,
                    p,
                    d,
                    pred,
                    ticker,
                    model_name,
                    d == dates_to_check[-1],
                    auto_heal,
                    _portfolio_getter,
                )
                anomalies.extend(a_list)
                healed.extend(h_list)

    now_ny = datetime.now(ZoneInfo("America/New_York"))
    w_anom, w_flag = _audit_weekly_sector_portfolios(client, port_by_owner, target_date, dates_to_check, now_ny)
    anomalies.extend(w_anom)
    flagged_for_review.extend(w_flag)

    mp_anom, mp_heal, mp_flag = await _audit_max_pain_portfolio(
        client, port_by_owner, target_date, dates_to_check, now_ny, auto_heal
    )
    anomalies.extend(mp_anom)
    healed.extend(mp_heal)
    flagged_for_review.extend(mp_flag)

    status = "clean"
    if anomalies and auto_heal and len(healed) == len(anomalies):
        status = "healed"
    elif anomalies:
        status = "anomalies_detected"

    return {
        "status": status,
        "dates_checked": dates_to_check,
        "anomalies": anomalies,
        "healed": healed,
        "flagged_for_review": flagged_for_review,
        "summary_table_markdown": generate_markdown_summary(dates_to_check, anomalies, healed, flagged_for_review),
    }


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
