"""Live Weekly & Horizon Sector Portfolio Execution Engine."""

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from core.config import logger
from core.db import get_supabase_client
from execution.sector_horizon_trading import execute_horizon_sector_entries, execute_horizon_sector_exits
from execution.system_portfolios import (
    ALL_SECTOR_LS_OWNER_IDS,
    DEFAULT_SLIPPAGE_BPS,
    MECHANICAL_SECTOR_OWNER_IDS,
    MECHANICAL_SECTOR_UNIVERSE,
    SYS_SECTOR_LS_OWNER_ID,
    SYS_SECTOR_START_DATE,
    get_or_create_system_portfolio,
    resolve_mechanical_sectors,
    resolve_sector_predictions,
)


async def execute_system_sector_entry(
    week_start_date: str,
    predictions: list[dict],
    price_map: dict[str, float],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    owner_id: str = SYS_SECTOR_LS_OWNER_ID,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute Monday market open entry for the consensus sector long/short portfolio."""
    if week_start_date < SYS_SECTOR_START_DATE:
        return {"status": "skipped", "reason": f"Before start date {SYS_SECTOR_START_DATE}"}

    long_sectors, short_sectors = resolve_sector_predictions(predictions)
    if not long_sectors and not short_sectors:
        logger.warning(f"No clean sectors available for {owner_id} entry.")
        return {"status": "skipped", "reason": "No valid sectors"}

    portfolio = await get_or_create_system_portfolio(owner_id)
    current_cash = portfolio.cash_balance
    slip_factor = slippage_bps / 10000.0
    client = get_supabase_client()

    start_ts = f"{week_start_date}T13:30:00Z"

    # Idempotency check: verify if entry trades already exist for this start date
    existing_res = (
        client.table("trades")
        .select("id, ticker, signal")
        .eq("portfolio_id", str(portfolio.id))
        .eq("executed_at", start_ts)
        .execute()
    )
    if existing_res.data:
        logger.info(f"Entry trades already exist for {owner_id} at {start_ts}. Skipping re-entry.")
        return {"status": "skipped", "reason": "Already entered for this cycle", "trades": existing_res.data}

    long_budget = (current_cash * 0.5) if (long_sectors and short_sectors) else (current_cash if long_sectors else 0.0)
    short_budget = (
        (current_cash * 0.5) if (long_sectors and short_sectors) else (current_cash if short_sectors else 0.0)
    )

    per_long_alloc = (long_budget / len(long_sectors)) if long_sectors else 0.0
    per_short_alloc = (short_budget / len(short_sectors)) if short_sectors else 0.0

    entered_trades = []

    # 1. Long Legs Entry
    for ticker in long_sectors:
        p = price_map.get(ticker)
        if not p or p <= 0:
            continue
        entry_p = p * (1.0 + slip_factor)
        shares = int(per_long_alloc // entry_p) if entry_p > 0 else 0
        if shares <= 0:
            continue

        trade_record = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "BUY",
            "quantity": shares,
            "price": entry_p,
            "total_cost": shares * entry_p,
            "executed_at": start_ts,
        }
        trade_id = None
        if not dry_run:
            ins_res = client.table("trades").insert(trade_record).execute()
            trade_id = ins_res.data[0]["id"] if ins_res.data and "id" in ins_res.data[0] else str(uuid4())

            # Upsert active holding into portfolio_positions
            client.table("portfolio_positions").upsert(
                {
                    "portfolio_id": str(portfolio.id),
                    "ticker": ticker,
                    "quantity": shares,
                    "average_cost_basis": entry_p,
                    "last_updated_at": datetime.now(UTC).isoformat(),
                },
                on_conflict="portfolio_id,ticker",
            ).execute()
        entered_trades.append(
            {"ticker": ticker, "side": "LONG", "shares": shares, "entry_price": entry_p, "trade_id": trade_id}
        )

    # 2. Short Legs Entry
    for ticker in short_sectors:
        p = price_map.get(ticker)
        if not p or p <= 0:
            continue
        entry_p = p * (1.0 - slip_factor)
        shares = int(per_short_alloc // entry_p) if entry_p > 0 else 0
        if shares <= 0:
            continue

        trade_record = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "SHORT",
            "quantity": shares,
            "price": entry_p,
            "total_cost": shares * entry_p,
            "executed_at": start_ts,
        }
        trade_id = None
        if not dry_run:
            ins_res = client.table("trades").insert(trade_record).execute()
            trade_id = ins_res.data[0]["id"] if ins_res.data and "id" in ins_res.data[0] else str(uuid4())
        # Note: DB constraint quantity_not_negative prevents negative positions in portfolio_positions.
        # Short legs are tracked directly via trades table.
        entered_trades.append(
            {"ticker": ticker, "side": "SHORT", "shares": shares, "entry_price": entry_p, "trade_id": trade_id}
        )

    # Deduct cash for long leg purchases
    total_long_spent = sum(t["shares"] * t["entry_price"] for t in entered_trades if t["side"] == "LONG")
    remaining_cash = max(0.0, current_cash - total_long_spent)
    if not dry_run:
        client.table("portfolios").update(
            {
                "cash_balance": remaining_cash,
                "total_equity": current_cash,
                "buying_power": current_cash * 4,
                "excess_liquidity": current_cash,
                "last_updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(portfolio.id)).execute()

        # Submit Alpaca orders for LONG legs only (Alpaca paper guardrail prevents shorting)
        try:
            from execution.alpaca_broker import AlpacaBroker

            broker = AlpacaBroker()
            for t in entered_trades:
                if t["side"] == "LONG":
                    await broker.submit_limit_order(
                        trade_id=t.get("trade_id") or uuid4(),
                        ticker=t["ticker"],
                        quantity=t["shares"],
                        signal="BUY",
                        limit_price=round(t["entry_price"], 2),
                        agent_id=owner_id,
                    )
        except Exception as exc:
            logger.warning(f"Alpaca mirror error during sector entry: {exc}")

    logger.info(
        f"System Sector L/S entry executed for {owner_id} on {week_start_date} (dry_run={dry_run}): {entered_trades}"
    )
    return {
        "status": "success",
        "dry_run": dry_run,
        "owner_id": owner_id,
        "long_sectors": long_sectors,
        "short_sectors": short_sectors,
        "trades": entered_trades,
    }


async def execute_mechanical_sector_entry(
    owner_id: str,
    sectors: list[str],
    week_start_date: str,
    price_map: dict[str, float],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute Monday market open entry for a mechanical long-only sector portfolio."""
    if week_start_date < SYS_SECTOR_START_DATE:
        return {"status": "skipped", "reason": f"Before start date {SYS_SECTOR_START_DATE}"}

    clean_sectors = [s.upper() for s in sectors if s]
    if not clean_sectors:
        return {"status": "skipped", "reason": "No valid sectors"}

    portfolio = await get_or_create_system_portfolio(owner_id)
    current_cash = portfolio.cash_balance
    slip_factor = slippage_bps / 10000.0
    client = get_supabase_client()

    start_ts = f"{week_start_date}T13:30:00Z"

    existing_res = (
        client.table("trades").select("id").eq("portfolio_id", str(portfolio.id)).eq("executed_at", start_ts).execute()
    )
    if existing_res.data:
        logger.info(f"Entry trades already exist for {owner_id} at {start_ts}. Skipping re-entry.")
        return {"status": "skipped", "reason": "Already entered for this cycle"}

    budget_per_sector = current_cash / len(clean_sectors)
    entered_trades = []

    for ticker in clean_sectors:
        p = price_map.get(ticker)
        if not p or p <= 0:
            continue
        entry_p = p * (1.0 + slip_factor)
        shares = int(budget_per_sector // entry_p) if entry_p > 0 else 0
        if shares <= 0:
            continue

        trade_record = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "BUY",
            "quantity": shares,
            "price": entry_p,
            "total_cost": shares * entry_p,
            "executed_at": start_ts,
        }
        trade_id = None
        if not dry_run:
            ins_res = client.table("trades").insert(trade_record).execute()
            trade_id = ins_res.data[0]["id"] if ins_res.data and "id" in ins_res.data[0] else str(uuid4())

            client.table("portfolio_positions").upsert(
                {
                    "portfolio_id": str(portfolio.id),
                    "ticker": ticker,
                    "quantity": shares,
                    "average_cost_basis": entry_p,
                    "last_updated_at": datetime.now(UTC).isoformat(),
                },
                on_conflict="portfolio_id,ticker",
            ).execute()
        entered_trades.append({"ticker": ticker, "shares": shares, "entry_price": entry_p, "trade_id": trade_id})

    total_spent = sum(t["shares"] * t["entry_price"] for t in entered_trades)
    remaining_cash = max(0.0, current_cash - total_spent)
    if not dry_run:
        client.table("portfolios").update(
            {
                "cash_balance": remaining_cash,
                "total_equity": current_cash,
                "buying_power": current_cash * 4,
                "excess_liquidity": current_cash,
                "last_updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(portfolio.id)).execute()

        try:
            from execution.alpaca_broker import AlpacaBroker

            broker = AlpacaBroker()
            for t in entered_trades:
                await broker.submit_limit_order(
                    trade_id=t.get("trade_id") or uuid4(),
                    ticker=t["ticker"],
                    quantity=t["shares"],
                    signal="BUY",
                    limit_price=round(t["entry_price"], 2),
                    agent_id=owner_id,
                )
        except Exception as exc:
            logger.warning(f"Alpaca mirror error during mechanical entry for {owner_id}: {exc}")

    logger.info(
        f"Mechanical sector entry complete for {owner_id} on {week_start_date} (dry_run={dry_run}): {entered_trades}"
    )
    return {
        "status": "success",
        "dry_run": dry_run,
        "owner_id": owner_id,
        "sectors": clean_sectors,
        "trades": entered_trades,
    }


async def execute_system_sector_exit(
    week_end_date: str,
    price_map: dict[str, float],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    owner_id: str = SYS_SECTOR_LS_OWNER_ID,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute market close exit for the consensus sector long/short portfolio."""
    portfolio = await get_or_create_system_portfolio(owner_id)
    current_cash = portfolio.cash_balance
    slip_factor = slippage_bps / 10000.0
    client = get_supabase_client()

    end_ts = f"{week_end_date}T20:00:00Z"

    # Find open trades without an exit in this cycle
    trades_res = (
        client.table("trades")
        .select("id, ticker, signal, quantity, price, executed_at, realized_pnl")
        .eq("portfolio_id", str(portfolio.id))
        .order("executed_at", desc=True)
        .execute()
    )
    all_trades = trades_res.data or []

    # Map existing exit trades to avoid double exit
    exited_tickers = {
        t["ticker"] for t in all_trades if t.get("realized_pnl") is not None and t.get("executed_at") == end_ts
    }

    open_entries = [
        t
        for t in all_trades
        if t.get("signal") in ("BUY", "SHORT")
        and t.get("realized_pnl") is None
        and t.get("ticker") not in exited_tickers
    ]

    if not open_entries:
        logger.info(f"No open entries to exit for {owner_id} on {week_end_date}.")
        return {"status": "skipped", "reason": "No open positions to exit"}

    total_realized_pnl = 0.0
    total_long_proceeds = 0.0
    total_short_pnl = 0.0
    exited_trades = []

    for entry in open_entries:
        ticker = entry["ticker"]
        side = entry["signal"]
        entry_p = float(entry["price"])
        shares = int(entry["quantity"])
        p = price_map.get(ticker)
        if not p or p <= 0:
            continue

        if side == "BUY":
            exit_p = p * (1.0 - slip_factor)
            exit_sig = "SELL"
            pnl = (exit_p - entry_p) * shares
            pnl_pct = ((exit_p / entry_p) - 1.0) * 100.0
            proceeds = shares * exit_p
            total_long_proceeds += proceeds
        else:  # SHORT
            exit_p = p * (1.0 + slip_factor)
            exit_sig = "COVER"
            pnl = (entry_p - exit_p) * shares
            pnl_pct = ((entry_p - exit_p) / entry_p) * 100.0
            total_short_pnl += pnl

        total_realized_pnl += pnl

        exit_record = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": exit_sig,
            "quantity": shares,
            "price": exit_p,
            "total_cost": shares * exit_p,
            "realized_pnl": pnl,
            "realized_pnl_pct": pnl_pct,
            "executed_at": end_ts,
        }
        exit_trade_id = None
        if not dry_run:
            ins_res = client.table("trades").insert(exit_record).execute()
            exit_trade_id = ins_res.data[0]["id"] if ins_res.data and "id" in ins_res.data[0] else str(uuid4())

            # Mark the original entry trade as closed with realized_pnl
            if entry.get("id"):
                try:
                    client.table("trades").update({"realized_pnl": pnl, "realized_pnl_pct": pnl_pct}).eq(
                        "id", entry["id"]
                    ).execute()
                except Exception as exc:
                    logger.warning(f"Could not mark entry trade {entry.get('id')} closed: {exc}")

            if side == "BUY":
                try:
                    from execution.alpaca_broker import AlpacaBroker

                    broker = AlpacaBroker()
                    await broker.submit_limit_order(
                        trade_id=exit_trade_id,
                        ticker=ticker,
                        quantity=shares,
                        signal="SELL",
                        limit_price=round(exit_p, 2),
                        agent_id=owner_id,
                    )
                except Exception as exc:
                    logger.warning(f"Alpaca mirror error during sector exit for {ticker}: {exc}")

                # Clean up position in portfolio_positions after Alpaca limit order submission
                client.table("portfolio_positions").delete().match(
                    {"portfolio_id": str(portfolio.id), "ticker": ticker}
                ).execute()

        exited_trades.append({"ticker": ticker, "side": exit_sig, "pnl": pnl, "pnl_pct": pnl_pct})

    new_cash = max(0.0, current_cash + total_long_proceeds + total_short_pnl)
    if not dry_run:
        client.table("portfolios").update(
            {
                "cash_balance": new_cash,
                "total_equity": new_cash,
                "realized": new_cash,
                "buying_power": new_cash * 4,
                "excess_liquidity": new_cash,
                "last_updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(portfolio.id)).execute()

        client.table("portfolio_performance").upsert(
            {
                "portfolio_id": str(portfolio.id),
                "date": week_end_date,
                "total_equity": new_cash,
                "cash_balance": new_cash,
                "buying_power": new_cash * 4,
                "sma": 0.0,
                "realized": new_cash,
            },
            on_conflict="portfolio_id,date",
        ).execute()

    logger.info(
        f"System Sector L/S Exit complete for {owner_id} ({week_end_date}) (dry_run={dry_run}): PnL: ${total_realized_pnl:,.2f}, New Equity: ${new_cash:,.2f}"
    )
    return {
        "status": "success",
        "dry_run": dry_run,
        "owner_id": owner_id,
        "total_realized_pnl": total_realized_pnl,
        "new_equity": new_cash,
        "trades": exited_trades,
    }


async def execute_mechanical_sector_exit(
    owner_id: str,
    week_end_date: str,
    price_map: dict[str, float],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute Friday market close exit for a mechanical sector portfolio."""
    portfolio = await get_or_create_system_portfolio(owner_id)
    current_cash = portfolio.cash_balance
    slip_factor = slippage_bps / 10000.0
    client = get_supabase_client()

    end_ts = f"{week_end_date}T20:00:00Z"

    trades_res = (
        client.table("trades")
        .select("id, ticker, signal, quantity, price, executed_at, realized_pnl")
        .eq("portfolio_id", str(portfolio.id))
        .order("executed_at", desc=True)
        .execute()
    )
    all_trades = trades_res.data or []
    exited_tickers = {
        t["ticker"] for t in all_trades if t.get("realized_pnl") is not None and t.get("executed_at") == end_ts
    }

    open_entries = [
        t
        for t in all_trades
        if t.get("signal") == "BUY" and t.get("realized_pnl") is None and t.get("ticker") not in exited_tickers
    ]

    if not open_entries:
        logger.info(f"No open entries to exit for {owner_id} on {week_end_date}.")
        return {"status": "skipped", "reason": "No open positions to exit"}

    total_realized_pnl = 0.0
    total_proceeds = 0.0
    exited_trades = []

    for entry in open_entries:
        ticker = entry["ticker"]
        entry_p = float(entry["price"])
        shares = int(entry["quantity"])
        p = price_map.get(ticker)
        if not p or p <= 0:
            continue

        exit_p = p * (1.0 - slip_factor)
        proceeds = shares * exit_p
        pnl = (exit_p - entry_p) * shares
        pnl_pct = ((exit_p / entry_p) - 1.0) * 100.0
        total_realized_pnl += pnl
        total_proceeds += proceeds

        if not dry_run:
            exit_record = {
                "portfolio_id": str(portfolio.id),
                "ticker": ticker,
                "signal": "SELL",
                "quantity": shares,
                "price": exit_p,
                "total_cost": proceeds,
                "realized_pnl": pnl,
                "realized_pnl_pct": pnl_pct,
                "executed_at": end_ts,
            }
            ins_res = client.table("trades").insert(exit_record).execute()
            exit_trade_id = ins_res.data[0]["id"] if ins_res.data and "id" in ins_res.data[0] else str(uuid4())
            if entry.get("id"):
                try:
                    client.table("trades").update({"realized_pnl": pnl, "realized_pnl_pct": pnl_pct}).eq(
                        "id", entry["id"]
                    ).execute()
                except Exception as exc:
                    logger.warning(f"Could not mark mechanical entry trade {entry.get('id')} closed: {exc}")

            try:
                from execution.alpaca_broker import AlpacaBroker

                broker = AlpacaBroker()
                await broker.submit_limit_order(
                    trade_id=exit_trade_id,
                    ticker=ticker,
                    quantity=shares,
                    signal="SELL",
                    limit_price=round(exit_p, 2),
                    agent_id=owner_id,
                )
            except Exception as exc:
                logger.warning(f"Alpaca mirror error during mechanical exit for {owner_id}: {exc}")

            # Clean up position in portfolio_positions after Alpaca limit order submission
            client.table("portfolio_positions").delete().match(
                {"portfolio_id": str(portfolio.id), "ticker": ticker}
            ).execute()

        exited_trades.append({"ticker": ticker, "pnl": pnl, "pnl_pct": pnl_pct})

    new_cash = max(0.0, current_cash + total_proceeds)
    if not dry_run:
        client.table("portfolios").update(
            {
                "cash_balance": new_cash,
                "total_equity": new_cash,
                "realized": new_cash,
                "buying_power": new_cash * 4,
                "excess_liquidity": new_cash,
                "last_updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(portfolio.id)).execute()

        client.table("portfolio_performance").upsert(
            {
                "portfolio_id": str(portfolio.id),
                "date": week_end_date,
                "total_equity": new_cash,
                "cash_balance": new_cash,
                "buying_power": new_cash * 4,
                "sma": 0.0,
                "realized": new_cash,
            },
            on_conflict="portfolio_id,date",
        ).execute()

    logger.info(
        f"Mechanical sector exit complete for {owner_id} ({week_end_date}) (dry_run={dry_run}): PnL: ${total_realized_pnl:,.2f}, New Equity: ${new_cash:,.2f}"
    )
    return {
        "status": "success",
        "dry_run": dry_run,
        "owner_id": owner_id,
        "total_realized_pnl": total_realized_pnl,
        "new_equity": new_cash,
        "trades": exited_trades,
    }


async def get_sector_portfolios_status() -> dict[str, Any]:
    """Retrieve current positions, cash, and performance for all sector portfolios."""
    owner_ids = ALL_SECTOR_LS_OWNER_IDS + MECHANICAL_SECTOR_OWNER_IDS
    client = get_supabase_client()
    status_summary = {}

    for owner_id in owner_ids:
        portfolio = await get_or_create_system_portfolio(owner_id)
        pos_res = (
            client.table("portfolio_positions")
            .select("ticker, quantity, average_cost_basis, last_updated_at")
            .eq("portfolio_id", str(portfolio.id))
            .execute()
        )
        positions = pos_res.data or []

        trades_res = (
            client.table("trades")
            .select("id, ticker, signal, quantity, price, executed_at, realized_pnl")
            .eq("portfolio_id", str(portfolio.id))
            .is_("realized_pnl", "null")
            .execute()
        )
        open_trades = trades_res.data or []

        status_summary[owner_id] = {
            "portfolio_id": str(portfolio.id),
            "cash_balance": portfolio.cash_balance,
            "total_equity": portfolio.total_equity,
            "positions": positions,
            "open_trades": open_trades,
        }
        pos_str = ", ".join(f"{p['ticker']}:{p['quantity']}sh" for p in positions) or "None"
        short_str = (
            ", ".join(f"SHORT {t['ticker']}:{t['quantity']}sh" for t in open_trades if t.get("signal") == "SHORT")
            or "None"
        )
        logger.info(
            f"Portfolio [{owner_id}]: Equity=${portfolio.total_equity:,.2f}, Cash=${portfolio.cash_balance:,.2f}, Long=[{pos_str}], Short=[{short_str}]"
        )

    return status_summary


async def run_sector_trade(
    action: str = "entry",
    target_date_str: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Orchestrate live sector portfolio entry, exit, or status across all 5 weekly portfolios."""
    today = date.today() if target_date_str is None else date.fromisoformat(target_date_str)
    today_str = today.isoformat()
    client = get_supabase_client()

    if action == "status":
        summary = await get_sector_portfolios_status()
        return {"status": "success", "action": "status", "portfolios": summary}

    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()

    if action in ("entry", "open"):
        # 1. Fetch latest active 7d predictions
        preds_res = (
            client.table("sector_predictions")
            .select("*")
            .eq("timeframe", "7d")
            .lte("prediction_date", today_str)
            .order("prediction_date", desc=True)
            .limit(10)
            .execute()
        )
        predictions = preds_res.data or []
        if not predictions:
            logger.warning("No sector predictions found to execute live entry.")
            return {"status": "skipped", "reason": "No predictions found"}

        # Scoping fix: filter strictly to the latest prediction_date to prevent mixing multi-week predictions
        pred_dates = [p["prediction_date"] for p in predictions if p.get("prediction_date")]
        if pred_dates:
            latest_pred_date = max(pred_dates)
            predictions = [p for p in predictions if p.get("prediction_date") == latest_pred_date]
            logger.info(
                f"Scoped sector predictions to latest cycle: {latest_pred_date} ({len(predictions)} model predictions)"
            )

        # 2. Fetch latest correlation run for mechanical portfolios
        corr_run_res = (
            client.table("correlation_runs")
            .select("id, tickers")
            .lte("run_date", today_str)
            .order("run_date", desc=True)
            .limit(1)
            .execute()
        )
        corr_data = []
        universe = MECHANICAL_SECTOR_UNIVERSE
        if corr_run_res.data and isinstance(corr_run_res.data[0], dict) and "id" in corr_run_res.data[0]:
            run_id = corr_run_res.data[0]["id"]
            ref_tickers = corr_run_res.data[0].get("tickers") or universe
            universe = [t for t in MECHANICAL_SECTOR_UNIVERSE if t in ref_tickers] or universe
            c_res = client.table("correlation_data").select("*").eq("run_id", run_id).execute()
            corr_data = c_res.data or []

        resolved_mechanical = resolve_mechanical_sectors(corr_data, universe) if corr_data else {}

        # 3. Collect unique tickers and fetch open prices
        long_s, short_s = resolve_sector_predictions(predictions)
        all_tickers = set(long_s + short_s)
        for sec_list in resolved_mechanical.values():
            all_tickers.update(sec_list)

        quotes = await mdm.get_quotes(list(all_tickers), force_refresh=True)
        # Use open price from quote if available, fallback to current price
        price_map = {}
        for t, q in quotes.items():
            price_map[t] = float(q.open if getattr(q, "open", None) and q.open > 0 else q.price)

        # 4. Execute consensus entry
        res_consensus = await execute_system_sector_entry(
            week_start_date=today_str,
            predictions=predictions,
            price_map=price_map,
            dry_run=dry_run,
        )

        # 5. Execute mechanical entries
        mech_results = {}
        for owner_id in MECHANICAL_SECTOR_OWNER_IDS:
            sectors = resolved_mechanical.get(owner_id, [])
            if sectors:
                res_mech = await execute_mechanical_sector_entry(
                    owner_id=owner_id,
                    sectors=sectors,
                    week_start_date=today_str,
                    price_map=price_map,
                    dry_run=dry_run,
                )
                mech_results[owner_id] = res_mech

        # 6. Execute horizon entries (30d and 90d)
        res_horizons = await execute_horizon_sector_entries(
            today_str=today_str,
            price_map=price_map,
            dry_run=dry_run,
        )

        return {
            "status": "success",
            "action": "entry",
            "dry_run": dry_run,
            "consensus": res_consensus,
            "mechanical": mech_results,
            "horizons": res_horizons,
        }

    elif action in ("exit", "close"):
        # Dynamically collect all tickers that need closing quotes across consensus and mechanical portfolios
        tickers_to_close = set(MECHANICAL_SECTOR_UNIVERSE)
        for owner_id in ALL_SECTOR_LS_OWNER_IDS + MECHANICAL_SECTOR_OWNER_IDS:
            try:
                p = await get_or_create_system_portfolio(owner_id)
                tickers_to_close.update(p.positions.keys())
                open_t_res = (
                    client.table("trades")
                    .select("ticker")
                    .eq("portfolio_id", str(p.id))
                    .is_("realized_pnl", "null")
                    .execute()
                )
                if open_t_res.data:
                    tickers_to_close.update(t["ticker"] for t in open_t_res.data if t.get("ticker"))
            except Exception as e:
                logger.warning(f"Could not load open tickers for {owner_id}: {e}")

        quotes = await mdm.get_quotes(list(tickers_to_close), force_refresh=True)
        price_map = {t: float(q.price) for t, q in quotes.items() if q.price > 0}
        res_consensus = await execute_system_sector_exit(
            week_end_date=today_str,
            price_map=price_map,
            dry_run=dry_run,
        )
        mech_results = {}
        for owner_id in MECHANICAL_SECTOR_OWNER_IDS:
            res_mech = await execute_mechanical_sector_exit(
                owner_id=owner_id,
                week_end_date=today_str,
                price_map=price_map,
                dry_run=dry_run,
            )
            mech_results[owner_id] = res_mech

        res_horizons = await execute_horizon_sector_exits(
            today_str=today_str,
            price_map=price_map,
            dry_run=dry_run,
        )

        return {
            "status": "success",
            "action": "exit",
            "dry_run": dry_run,
            "consensus": res_consensus,
            "mechanical": mech_results,
            "horizons": res_horizons,
        }

    else:
        return {"status": "error", "message": f"Unsupported action: {action}"}
