"""Live intraday execution lifecycle for daily SPY systematic portfolios.

Handles:
1. Pre-market MOO entry (~9:20 AM ET): Alpaca OPG orders and provisional entry tracking.
2. Morning open reconciliation (~9:35 AM ET): Reconciles entry price and cost basis
   to the official 9:30 AM session open price (beginning of day).
3. Target limit orders (~9:35 AM ET): Places limit sell orders at target price.
4. Close exit (~3:30 PM ET): Liquidates positions and records realized PnL computed
   from the session open price.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from core.config import (
    SYS_DAILY_SPY_CLOSE_OWNER_PREFIX,
    SYS_DAILY_SPY_OWNER_PREFIX,
    is_allowed_daily_spy_model,
    is_allowed_daily_spy_owner,
    logger,
    resolve_daily_spy_owners,
)
from execution.daily_reconciliation import (
    get_daily_session_open_price,
    reconcile_daily_open_trades,
)
from trading.market_calendar import is_us_trading_day


async def _execute_single_moo_portfolio_entry(
    client: Any,
    broker: Any,
    owner_id: str,
    ticker: str,
    direction: str,
    spy_price: float,
    target_date_str: str,
    dry_run: bool,
) -> dict[str, Any] | None:
    """Execute one idempotent MOO entry for a single allowed Daily SPY portfolio."""
    if dry_run:
        port_res = client.table("portfolios").select("id, cash_balance").eq("owner_id", owner_id).limit(1).execute()
        if not port_res.data:
            return None
        portfolio_id = port_res.data[0]["id"]
        current_cash = float(port_res.data[0].get("cash_balance") or 0.0)
    else:
        import execution.daily_trading as dt

        portfolio = await dt.get_or_create_system_portfolio(owner_id)
        portfolio_id = portfolio.id
        current_cash = portfolio.cash_balance

    # Idempotency check: verify if entry trade already exists for today
    existing_res = (
        client.table("trades")
        .select("id")
        .eq("portfolio_id", str(portfolio_id))
        .gte("executed_at", f"{target_date_str}T00:00:00Z")
        .lte("executed_at", f"{target_date_str}T23:59:59Z")
        .execute()
    )
    if existing_res.data:
        logger.info(f"Entry trade already exists for {owner_id} on {target_date_str}. Skipping re-entry.")
        return None

    shares = int(current_cash // spy_price) if spy_price > 0 else 0
    if shares <= 0:
        logger.info(f"Insufficient cash (${current_cash:.2f}) for {owner_id} to buy SPY @ ${spy_price:.2f}.")
        return None

    trade_id = str(uuid4())
    signal = "BUY" if direction == "UP" else "SHORT"
    entry_trade: dict[str, Any] = {
        "id": trade_id,
        "portfolio_id": str(portfolio_id),
        "ticker": ticker,
        "signal": signal,
        "quantity": shares,
        "price": spy_price,
        "total_cost": shares * spy_price,
        "executed_at": f"{target_date_str}T13:30:00Z",
    }
    if direction != "UP":
        # Virtual SHORT legs are never sent to Alpaca; mark explicitly so sync/repair skips them.
        entry_trade["alpaca_status"] = "NO_MIRROR"

    if not dry_run:
        client.table("trades").insert(entry_trade).execute()
        if direction == "UP":
            client.table("portfolio_positions").upsert(
                {
                    "portfolio_id": str(portfolio_id),
                    "ticker": ticker,
                    "quantity": shares,
                    "average_cost_basis": spy_price,
                    "last_updated_at": datetime.now(UTC).isoformat(),
                },
                on_conflict="portfolio_id,ticker",
            ).execute()
            remaining_cash = max(0.0, current_cash - (shares * spy_price))
            client.table("portfolios").update(
                {
                    "cash_balance": remaining_cash,
                    "total_equity": current_cash,
                    "last_updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", str(portfolio_id)).execute()

            try:
                from alpaca.trading.enums import TimeInForce

                await broker.submit_market_order(
                    trade_id=UUID(trade_id),
                    ticker=ticker,
                    quantity=shares,
                    signal="BUY",
                    agent_id=owner_id,
                    time_in_force=TimeInForce.OPG,
                )
            except Exception as e:
                logger.warning(f"Alpaca MOO order failed for {owner_id}: {e}")

    return {"owner_id": owner_id, "signal": signal, "shares": shares, "price": spy_price}


async def execute_daily_moo_entries(target_date: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Execute pre-market Market-On-Open (OPG) daily trades for SPY before 9:28 AM ET.

    - Reads predictions for target_date from daily_predictions table.
    - Sizing uses session open price if available, otherwise latest quote.
    - For UP predictions:
      - Allocates cash, inserts BUY trade, upserts portfolio_positions, submits Alpaca OPG order.
    - For DOWN predictions:
      - Logs virtual SHORT trade in trades table.
    """
    import execution.daily_trading as dt

    target_date_str = target_date or date.today().isoformat()
    if not is_us_trading_day(date.fromisoformat(target_date_str[:10])):
        return {"status": "skipped", "reason": f"Not a US trading day: {target_date_str}"}

    client = dt.get_supabase_client()

    res = client.table("daily_predictions").select("*").eq("target_date", target_date_str).eq("ticker", "SPY").execute()
    predictions = res.data or []
    if not predictions:
        logger.info(f"No daily SPY predictions found for {target_date_str}. Skipping MOO entry.")
        return {"status": "skipped", "reason": "No predictions found", "entries": []}

    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()
    spy_quote = await mdm.get_quote("SPY", force_refresh=True)
    quote_price = float(spy_quote.price) if spy_quote and hasattr(spy_quote, "price") else 0.0

    session_open = await get_daily_session_open_price("SPY", target_date_str, client=client)
    spy_price = session_open if session_open and session_open > 0 else quote_price
    if not spy_price or spy_price <= 0:
        logger.warning(f"Could not retrieve SPY price for MOO entry on {target_date_str}.")
        return {"status": "skipped", "reason": "No SPY price", "entries": []}

    from execution.alpaca_broker import AlpacaBroker

    broker = AlpacaBroker()
    entries = []

    for pred in predictions:
        ticker = str(pred.get("ticker", "SPY")).strip().upper()
        if ticker != "SPY":
            continue
        model_name = str(pred.get("model_name", "unknown")).strip()
        if not is_allowed_daily_spy_model(model_name):
            logger.warning(
                f"Skipping MOO entry for {model_name} on {target_date_str}: model is not in ALLOWED_DAILY_SPY_MODELS."
            )
            continue
        direction = str(pred.get("predicted_direction", "UP")).strip().upper()
        if direction == "HOLD":
            logger.info(f"Skipping MOO entry for {model_name} on {target_date_str}: Prediction is HOLD.")
            continue
        expected_ret_raw = pred.get("expected_return_pct")
        target_portfolios = resolve_daily_spy_owners(model_name, expected_ret_raw)

        for owner_id in target_portfolios:
            entry = await _execute_single_moo_portfolio_entry(
                client=client,
                broker=broker,
                owner_id=owner_id,
                ticker=ticker,
                direction=direction,
                spy_price=spy_price,
                target_date_str=target_date_str,
                dry_run=dry_run,
            )
            if entry is not None:
                entries.append(entry)

    return {"status": "success", "entries": entries}


async def place_daily_target_limit_orders(target_date: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Place Alpaca limit sell order at profit target price for target-exit portfolios post-open (~9:35 AM)."""
    import execution.daily_trading as dt

    client = dt.get_supabase_client()
    target_date_str = target_date or date.today().isoformat()

    # Reconcile entry prices to beginning-of-day session open first
    await reconcile_daily_open_trades(target_date=target_date_str, dry_run=dry_run)

    # Query target portfolios: sys-daily-spy-{model} (not -close-)
    portfolios_res = (
        client.table("portfolios").select("id, owner_id").like("owner_id", f"{SYS_DAILY_SPY_OWNER_PREFIX}%").execute()
    )
    portfolios = [
        p
        for p in (portfolios_res.data or [])
        if not p.get("owner_id", "").startswith(SYS_DAILY_SPY_CLOSE_OWNER_PREFIX)
        and is_allowed_daily_spy_owner(p.get("owner_id"))
    ]

    from execution.alpaca_broker import AlpacaBroker

    broker = AlpacaBroker()
    placed_orders = []

    for p in portfolios:
        owner_id = p["owner_id"]
        model_name = owner_id.removeprefix(SYS_DAILY_SPY_OWNER_PREFIX)

        pos_res = (
            client.table("portfolio_positions")
            .select("quantity, average_cost_basis")
            .eq("portfolio_id", p["id"])
            .eq("ticker", "SPY")
            .execute()
        )
        positions = pos_res.data or []
        if not positions or positions[0]["quantity"] <= 0:
            continue

        pos = positions[0]
        qty = int(pos["quantity"])
        cost_basis = float(pos["average_cost_basis"])

        pred_res = (
            client.table("daily_predictions")
            .select("expected_return_pct")
            .eq("target_date", target_date_str)
            .eq("ticker", "SPY")
            .eq("model_name", model_name)
            .execute()
        )
        if not pred_res.data:
            continue
        exp_ret = pred_res.data[0].get("expected_return_pct")
        if not exp_ret or float(exp_ret) <= 0:
            continue

        target_pct = float(exp_ret)
        target_price = cost_basis * (1.0 + (target_pct / 100.0))

        if not dry_run:
            try:
                trade_id = uuid4()
                await broker.submit_limit_order(
                    trade_id=trade_id,
                    ticker="SPY",
                    quantity=qty,
                    signal="SELL",
                    limit_price=round(target_price, 2),
                    agent_id=owner_id,
                )
            except Exception as e:
                logger.warning(f"Failed to submit target limit order for {owner_id}: {e}")

        placed_orders.append(
            {
                "owner_id": owner_id,
                "quantity": qty,
                "target_price": round(target_price, 2),
            }
        )

    return {"status": "success", "orders": placed_orders}


async def execute_daily_close_exits(target_date: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Execute afternoon liquidation (~3:30 PM) for daily systematic portfolios.

    Guarantees realized PnL is computed against the beginning-of-day session open price.
    """
    import execution.daily_trading as dt

    target_date_str = target_date or date.today().isoformat()
    if not is_us_trading_day(date.fromisoformat(target_date_str[:10])):
        return {"status": "skipped", "reason": f"Not a US trading day: {target_date_str}"}

    client = dt.get_supabase_client()

    # Reconcile entry trades to official open price before closing
    session_open = await get_daily_session_open_price("SPY", target_date_str, client=client)

    portfolios_res = (
        client.table("portfolios")
        .select("id, owner_id, cash_balance")
        .like("owner_id", f"{SYS_DAILY_SPY_OWNER_PREFIX}%")
        .execute()
    )
    portfolios = [p for p in (portfolios_res.data or []) if is_allowed_daily_spy_owner(p.get("owner_id"))]

    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()
    spy_quote = await mdm.get_quote("SPY", force_refresh=True)
    current_price = float(spy_quote.price) if spy_quote and hasattr(spy_quote, "price") else 0.0
    if not current_price or current_price <= 0:
        logger.warning(f"Could not retrieve SPY price for close exit on {target_date_str}.")
        return {"status": "skipped", "reason": "No SPY price", "exits": []}

    from execution.alpaca_broker import AlpacaBroker

    broker = AlpacaBroker()
    exited = []

    for p in portfolios:
        portfolio_id = p["id"]
        owner_id = p["owner_id"]
        current_cash = float(p.get("cash_balance") or 0.0)

        # 1. Cancel open limit orders on Alpaca
        if not dry_run:
            try:
                await broker.cancel_open_orders_for_agent(agent_id=owner_id, ticker="SPY")
            except Exception as e:
                logger.warning(f"Failed to cancel open orders for {owner_id}: {e}")

        # 2. Check for LONG position in portfolio_positions
        pos_res = (
            client.table("portfolio_positions")
            .select("id, ticker, quantity, average_cost_basis")
            .eq("portfolio_id", portfolio_id)
            .eq("ticker", "SPY")
            .execute()
        )
        positions = pos_res.data or []
        if positions and positions[0]["quantity"] > 0:
            pos = positions[0]
            qty = int(pos["quantity"])
            initial_cost_basis = float(pos["average_cost_basis"])
            # Anchor to beginning-of-day session open price
            cost_basis = session_open if session_open and session_open > 0 else initial_cost_basis

            realized_pnl = (current_price - cost_basis) * qty
            realized_pnl_pct = (((current_price / cost_basis) - 1.0) * 100.0) if cost_basis > 0 else 0.0

            trade_id = str(uuid4())
            exit_trade = {
                "id": trade_id,
                "portfolio_id": str(portfolio_id),
                "ticker": "SPY",
                "signal": "SELL",
                "quantity": qty,
                "price": current_price,
                "total_cost": qty * current_price,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
                "executed_at": f"{target_date_str}T19:30:00Z",
            }

            if not dry_run:
                # Reconcile entry trade in trades table if it recorded estimated pre-market price
                if session_open and abs(initial_cost_basis - session_open) > 0.01:
                    client.table("trades").update({"price": session_open, "total_cost": qty * session_open}).eq(
                        "portfolio_id", portfolio_id
                    ).eq("signal", "BUY").gte("executed_at", f"{target_date_str}T00:00:00Z").lte(
                        "executed_at", f"{target_date_str}T23:59:59Z"
                    ).execute()

                client.table("trades").insert(exit_trade).execute()
                client.table("portfolio_positions").delete().eq("portfolio_id", portfolio_id).eq(
                    "ticker", "SPY"
                ).execute()

                new_cash = max(0.0, current_cash + (qty * current_price))
                client.table("portfolios").update(
                    {
                        "cash_balance": new_cash,
                        "total_equity": new_cash,
                        "realized": new_cash,
                        "buying_power": new_cash,
                        "excess_liquidity": new_cash,
                        "last_updated_at": datetime.now(UTC).isoformat(),
                    }
                ).eq("id", portfolio_id).execute()

                client.table("portfolio_performance").upsert(
                    {
                        "portfolio_id": portfolio_id,
                        "date": target_date_str,
                        "total_equity": new_cash,
                        "cash_balance": new_cash,
                        "buying_power": new_cash,
                        "sma": 0.0,
                        "realized": new_cash,
                    },
                    on_conflict="portfolio_id,date",
                ).execute()

                try:
                    await broker.submit_market_order(
                        trade_id=UUID(trade_id),
                        ticker="SPY",
                        quantity=qty,
                        signal="SELL",
                        agent_id=owner_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to submit Alpaca sell order for {owner_id}: {e}")

            exited.append({"owner_id": owner_id, "signal": "SELL", "shares": qty, "pnl": realized_pnl})
            continue

        # 3. Check for open virtual SHORT trade without COVER
        trades_res = (
            client.table("trades")
            .select("id, signal, price, quantity")
            .eq("portfolio_id", portfolio_id)
            .gte("executed_at", f"{target_date_str}T00:00:00Z")
            .lte("executed_at", f"{target_date_str}T23:59:59Z")
            .execute()
        )
        day_trades = trades_res.data or []
        short_trades = [t for t in day_trades if t.get("signal") == "SHORT"]
        cover_trades = [t for t in day_trades if t.get("signal") == "COVER"]

        if short_trades and not cover_trades:
            st = short_trades[0]
            recorded_entry_p = float(st["price"])
            entry_p = session_open if session_open and session_open > 0 else recorded_entry_p
            qty = int(st["quantity"])
            realized_pnl = (entry_p - current_price) * qty
            realized_pnl_pct = (((entry_p - current_price) / entry_p) * 100.0) if entry_p > 0 else 0.0

            trade_id = str(uuid4())
            exit_trade = {
                "id": trade_id,
                "portfolio_id": str(portfolio_id),
                "ticker": "SPY",
                "signal": "COVER",
                "quantity": qty,
                "price": current_price,
                "total_cost": qty * current_price,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
                "alpaca_status": "NO_MIRROR",
                "executed_at": f"{target_date_str}T19:30:00Z",
            }

            if not dry_run:
                # Reconcile short entry trade price if it recorded premarket estimated price
                if session_open and abs(recorded_entry_p - session_open) > 0.01:
                    client.table("trades").update({"price": session_open, "total_cost": qty * session_open}).eq(
                        "id", st["id"]
                    ).execute()

                client.table("trades").insert(exit_trade).execute()
                # Mark original entry SHORT trade as closed with realized PnL
                client.table("trades").update({"realized_pnl": realized_pnl, "realized_pnl_pct": realized_pnl_pct}).eq(
                    "id", st["id"]
                ).execute()
                new_cash = max(0.0, current_cash + realized_pnl)
                client.table("portfolios").update(
                    {
                        "cash_balance": new_cash,
                        "total_equity": new_cash,
                        "realized": new_cash,
                        "buying_power": new_cash,
                        "excess_liquidity": new_cash,
                        "last_updated_at": datetime.now(UTC).isoformat(),
                    }
                ).eq("id", portfolio_id).execute()

                client.table("portfolio_performance").upsert(
                    {
                        "portfolio_id": portfolio_id,
                        "date": target_date_str,
                        "total_equity": new_cash,
                        "cash_balance": new_cash,
                        "buying_power": new_cash,
                        "sma": 0.0,
                        "realized": new_cash,
                    },
                    on_conflict="portfolio_id,date",
                ).execute()

            exited.append({"owner_id": owner_id, "signal": "COVER", "shares": qty, "pnl": realized_pnl})

    return {"status": "success", "exits": exited}


__all__ = [
    "get_daily_session_open_price",
    "reconcile_daily_open_trades",
    "execute_daily_moo_entries",
    "place_daily_target_limit_orders",
    "execute_daily_close_exits",
]
