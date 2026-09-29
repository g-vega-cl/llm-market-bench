"""Daily S&P Intraday Trading Module.

Executes systematic daily trades on SPY based on daily open-to-close predictions:
1. Original Strategy: Exits at intraday profit target if hit, otherwise exits at time exit (3:30 PM / Close).
   Owner ID prefix: `sys-daily-spy-`
2. Close-Exit Strategy (3:50 PM / MOC): Holds throughout the session and sells at session close,
   disregarding intraday target hits. Modeled with 0.02% (2 bps) slippage due to high SPY liquidity.
   Owner ID prefix: `sys-daily-spy-close-`
"""

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from core.config import logger
from core.db import get_supabase_client
from execution.portfolio import Portfolio

SYS_DAILY_SPY_OWNER_PREFIX = "sys-daily-spy-"
SYS_DAILY_SPY_CLOSE_OWNER_PREFIX = "sys-daily-spy-close-"
DEFAULT_DAILY_SLIPPAGE_BPS = 5.0  # 5 bps = 0.05%
DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS = 2.0  # 2 bps = 0.02% for highly liquid SPY
INITIAL_PORTFOLIO_CASH = 10000.00


async def get_or_create_system_portfolio(owner_id: str) -> Portfolio:
    """Load an existing system portfolio or initialize a new one in Supabase."""
    portfolio = Portfolio(owner_id)
    await portfolio.initialize()
    if not portfolio.id:
        client = get_supabase_client()
        res = (
            client.table("portfolios")
            .insert(
                {
                    "owner_id": owner_id,
                    "cash_balance": INITIAL_PORTFOLIO_CASH,
                    "sma": 0.0,
                    "total_equity": INITIAL_PORTFOLIO_CASH,
                    "realized": INITIAL_PORTFOLIO_CASH,
                    "buying_power": INITIAL_PORTFOLIO_CASH * 4,
                    "excess_liquidity": INITIAL_PORTFOLIO_CASH,
                }
            )
            .execute()
        )
        if res.data:
            portfolio.id = UUID(res.data[0]["id"])
            portfolio.cash_balance = INITIAL_PORTFOLIO_CASH
    return portfolio


def compute_daily_trade_execution(
    prediction: dict,
    intraday: dict,
    capital: float = INITIAL_PORTFOLIO_CASH,
    slippage_bps: float = DEFAULT_DAILY_SLIPPAGE_BPS,
    exit_on_target: bool = True,
) -> dict[str, Any]:
    """Compute the entry price, target price, exit price, and realized PnL for a daily SPY trade.

    Args:
        prediction: Prediction record containing predicted_direction and expected_return_pct.
        intraday: Intraday market data with open_price, high_price, low_price, close_price,
                  and optional intraday_exit_price / intraday_hit.
        capital: Available capital to allocate.
        slippage_bps: Friction in basis points (e.g. 5.0 = 0.05%, 2.0 = 0.02%).
        exit_on_target: If True, exits at profit target if touched intraday.
                        If False, holds until 3:50ish / Day Close, ignoring target hits.
    """
    direction = str(prediction.get("predicted_direction", "UP")).strip().upper()
    expected_ret_raw = prediction.get("expected_return_pct")
    expected_return_pct = abs(float(expected_ret_raw)) if expected_ret_raw is not None else 0.0

    open_p = float(intraday["open_price"])
    high_p = float(intraday["high_price"])
    low_p = float(intraday["low_price"])
    close_p = float(intraday["close_price"])
    time_exit_p = float(intraday.get("intraday_exit_price") or close_p)

    slip_factor = slippage_bps / 10000.0

    if direction == "UP":
        entry_price = open_p * (1.0 + slip_factor)
        target_price = open_p * (1.0 + (expected_return_pct / 100.0))
        max_return_pct = ((high_p - open_p) / open_p) * 100.0 if open_p > 0 else 0.0

        intraday_hit = bool(intraday.get("intraday_hit", False)) or (
            expected_return_pct > 0 and (high_p >= target_price or max_return_pct >= expected_return_pct)
        )

        if exit_on_target:
            target_hit = intraday_hit
            exit_price = target_price if target_hit else time_exit_p * (1.0 - slip_factor)
        else:
            target_hit = False
            exit_price = time_exit_p * (1.0 - slip_factor)

        shares = int(capital // entry_price) if entry_price > 0 else 0
        realized_pnl = (exit_price - entry_price) * shares
        realized_pnl_pct = (((exit_price / entry_price) - 1.0) * 100.0) if entry_price > 0 else 0.0

    else:  # DOWN
        entry_price = open_p * (1.0 - slip_factor)
        target_price = open_p * (1.0 - (expected_return_pct / 100.0))
        min_return_pct = ((low_p - open_p) / open_p) * 100.0 if open_p > 0 else 0.0

        intraday_hit = bool(intraday.get("intraday_hit", False)) or (
            expected_return_pct > 0 and (low_p <= target_price or min_return_pct <= -expected_return_pct)
        )

        if exit_on_target:
            target_hit = intraday_hit
            exit_price = target_price if target_hit else time_exit_p * (1.0 + slip_factor)
        else:
            target_hit = False
            exit_price = time_exit_p * (1.0 + slip_factor)

        shares = int(capital // entry_price) if entry_price > 0 else 0
        realized_pnl = (entry_price - exit_price) * shares
        realized_pnl_pct = (((entry_price - exit_price) / entry_price) * 100.0) if entry_price > 0 else 0.0

    return {
        "direction": direction,
        "entry_price": entry_price,
        "target_price": target_price,
        "exit_price": exit_price,
        "target_hit": target_hit,
        "shares": shares,
        "capital_allocated": shares * entry_price,
        "realized_pnl": realized_pnl,
        "realized_pnl_pct": realized_pnl_pct,
    }


async def execute_daily_spy_trade(
    prediction: dict,
    intraday_data: dict,
    owner_prefix: str,
    exit_on_target: bool,
    slippage_bps: float,
    get_supabase_client_fn: Callable | None = None,
    get_or_create_system_portfolio_fn: Callable | None = None,
) -> dict[str, Any]:
    """Execute a systematic daily SPY trade with specified owner prefix and exit mechanics."""
    client_getter = get_supabase_client_fn or get_supabase_client
    portfolio_getter = get_or_create_system_portfolio_fn or get_or_create_system_portfolio

    model_name = prediction.get("model_name", "unknown")
    owner_id = f"{owner_prefix}{model_name}"
    target_date_str = prediction.get("target_date") or date.today().isoformat()
    ticker = prediction.get("ticker", "SPY").upper()

    portfolio = await portfolio_getter(owner_id)
    current_cash = portfolio.cash_balance

    client = client_getter()

    # Idempotency guard: clean up any existing trades for this portfolio and session
    existing_trades_res = (
        client.table("trades")
        .select("id, realized_pnl")
        .eq("portfolio_id", str(portfolio.id))
        .gte("executed_at", f"{target_date_str}T00:00:00Z")
        .lte("executed_at", f"{target_date_str}T23:59:59Z")
        .execute()
    )
    existing_trades = existing_trades_res.data or []
    if existing_trades:
        prev_pnl = sum(float(t["realized_pnl"]) for t in existing_trades if t.get("realized_pnl") is not None)
        current_cash = max(0.0, current_cash - prev_pnl)
        for t in existing_trades:
            client.table("trades").delete().eq("id", t["id"]).execute()
        logger.info(
            f"Idempotency cleanup: Removed {len(existing_trades)} existing trades for {owner_id} on {target_date_str}, reverted PnL: ${prev_pnl:,.2f}"
        )

    execution = compute_daily_trade_execution(
        prediction=prediction,
        intraday=intraday_data,
        capital=current_cash,
        slippage_bps=slippage_bps,
        exit_on_target=exit_on_target,
    )

    shares = execution["shares"]
    if shares <= 0:
        return {"status": "skipped", "reason": "Insufficient capital"}
    direction = execution["direction"]
    entry_signal = "BUY" if direction == "UP" else "SHORT"
    exit_signal = "SELL" if direction == "UP" else "COVER"

    # Log entry trade at 9:30 AM ET (13:30 UTC)
    client.table("trades").insert(
        {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": entry_signal,
            "quantity": shares,
            "price": execution["entry_price"],
            "total_cost": shares * execution["entry_price"],
            "executed_at": f"{target_date_str}T13:30:00Z",
        }
    ).execute()

    # Log exit trade at 4:00 PM ET (20:00 UTC) with realized PnL
    client.table("trades").insert(
        {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": exit_signal,
            "quantity": shares,
            "price": execution["exit_price"],
            "total_cost": shares * execution["exit_price"],
            "realized_pnl": execution["realized_pnl"],
            "realized_pnl_pct": execution["realized_pnl_pct"],
            "executed_at": f"{target_date_str}T20:00:00Z",
        }
    ).execute()

    new_cash = max(0.0, current_cash + execution["realized_pnl"])
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
            "date": target_date_str,
            "total_equity": new_cash,
            "cash_balance": new_cash,
            "buying_power": new_cash * 4,
            "sma": 0.0,
            "realized": new_cash,
        },
        on_conflict="portfolio_id,date",
    ).execute()

    logger.info(
        f"Daily SPY trade complete for {owner_id} on {target_date_str}: "
        f"Dir: {direction}, TargetHit: {execution['target_hit']}, PnL: ${execution['realized_pnl']:,.2f}, New Equity: ${new_cash:,.2f}"
    )

    return {
        "status": "success",
        "owner_id": owner_id,
        "execution": execution,
        "new_equity": new_cash,
    }


async def execute_system_daily_trade(
    prediction: dict,
    intraday_data: dict,
    slippage_bps: float = DEFAULT_DAILY_SLIPPAGE_BPS,
    get_supabase_client_fn: Callable | None = None,
    get_or_create_system_portfolio_fn: Callable | None = None,
) -> dict[str, Any]:
    """Execute original target-exit daily trade on SPY (sys-daily-spy-{model})."""
    model_name = str(prediction.get("model_name", "unknown"))
    expected_ret_raw = prediction.get("expected_return_pct")
    expected_return_pct = abs(float(expected_ret_raw)) if expected_ret_raw is not None else 0.0

    if "jev" in model_name.lower() or expected_return_pct <= 0.0:
        logger.info(
            f"Skipping target-exit daily trade for {model_name}: "
            f"Direction-only classifier models with 0% target do not participate in target-exit portfolios."
        )
        return {
            "status": "skipped",
            "reason": "Target-exit strategy requires a positive profit target percentage",
        }

    return await execute_daily_spy_trade(
        prediction=prediction,
        intraday_data=intraday_data,
        owner_prefix=SYS_DAILY_SPY_OWNER_PREFIX,
        exit_on_target=True,
        slippage_bps=slippage_bps,
        get_supabase_client_fn=get_supabase_client_fn,
        get_or_create_system_portfolio_fn=get_or_create_system_portfolio_fn,
    )


async def execute_system_daily_close_trade(
    prediction: dict,
    intraday_data: dict,
    slippage_bps: float = DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS,
    get_supabase_client_fn: Callable | None = None,
    get_or_create_system_portfolio_fn: Callable | None = None,
) -> dict[str, Any]:
    """Execute 3:50ish close-exit daily trade on SPY (sys-daily-spy-close-{model})."""
    return await execute_daily_spy_trade(
        prediction=prediction,
        intraday_data=intraday_data,
        owner_prefix=SYS_DAILY_SPY_CLOSE_OWNER_PREFIX,
        exit_on_target=False,
        slippage_bps=slippage_bps,
        get_supabase_client_fn=get_supabase_client_fn,
        get_or_create_system_portfolio_fn=get_or_create_system_portfolio_fn,
    )


async def execute_daily_moo_entries(target_date: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Execute pre-market Market-On-Open (OPG) daily trades for SPY before 9:28 AM ET.

    - Reads predictions for target_date from daily_predictions table.
    - For UP predictions:
      - Allocates available cash from portfolio.
      - Inserts BUY trade in trades table.
      - Upserts active SPY holding in portfolio_positions.
      - Deducts cash balance from portfolio.
      - Submits MarketOrderRequest(time_in_force=TimeInForce.OPG) to Alpaca.
    - For DOWN predictions:
      - Enters virtual SHORT trade in trades table.
      - Skips portfolio_positions and Alpaca order (guardrails against shorting).
    """
    client = get_supabase_client()
    target_date_str = target_date or date.today().isoformat()

    res = client.table("daily_predictions").select("*").eq("target_date", target_date_str).execute()
    predictions = res.data or []
    if not predictions:
        logger.info(f"No daily predictions found for {target_date_str}. Skipping MOO entry.")
        return {"status": "skipped", "reason": "No predictions found", "entries": []}

    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()
    spy_quote = await mdm.get_quote("SPY", force_refresh=True)
    spy_price = float(spy_quote.price) if spy_quote and hasattr(spy_quote, "price") else 0.0
    if not spy_price or spy_price <= 0:
        logger.warning(f"Could not retrieve SPY price for MOO entry on {target_date_str}.")
        return {"status": "skipped", "reason": "No SPY price", "entries": []}

    from execution.alpaca_broker import AlpacaBroker

    broker = AlpacaBroker()
    entries = []

    for pred in predictions:
        model_name = str(pred.get("model_name", "unknown"))
        direction = str(pred.get("predicted_direction", "UP")).strip().upper()
        ticker = str(pred.get("ticker", "SPY")).strip().upper()
        expected_ret_raw = pred.get("expected_return_pct")
        expected_return_pct = abs(float(expected_ret_raw)) if expected_ret_raw is not None else 0.0

        # Portfolios to enter:
        # 1. sys-daily-spy-close-{model} (always enters if direction is UP or DOWN)
        # 2. sys-daily-spy-{model} (target-exit: enters if expected_return_pct > 0 and 'jev' not in model_name.lower())
        target_portfolios = [f"{SYS_DAILY_SPY_CLOSE_OWNER_PREFIX}{model_name}"]
        if "jev" not in model_name.lower() and expected_return_pct > 0.0:
            target_portfolios.append(f"{SYS_DAILY_SPY_OWNER_PREFIX}{model_name}")

        for owner_id in target_portfolios:
            portfolio = await get_or_create_system_portfolio(owner_id)
            current_cash = portfolio.cash_balance

            # Idempotency check: verify if entry trade already exists for today
            existing_res = (
                client.table("trades")
                .select("id")
                .eq("portfolio_id", str(portfolio.id))
                .gte("executed_at", f"{target_date_str}T00:00:00Z")
                .lte("executed_at", f"{target_date_str}T23:59:59Z")
                .execute()
            )
            if existing_res.data:
                logger.info(f"Entry trade already exists for {owner_id} on {target_date_str}. Skipping re-entry.")
                continue

            shares = int(current_cash // spy_price) if spy_price > 0 else 0
            if shares <= 0:
                logger.info(f"Insufficient cash (${current_cash:.2f}) for {owner_id} to buy SPY @ ${spy_price:.2f}.")
                continue

            if direction == "UP":
                trade_id = str(uuid4())
                entry_trade = {
                    "id": trade_id,
                    "portfolio_id": str(portfolio.id),
                    "ticker": ticker,
                    "signal": "BUY",
                    "quantity": shares,
                    "price": spy_price,
                    "total_cost": shares * spy_price,
                    "executed_at": f"{target_date_str}T13:30:00Z",
                }
                if not dry_run:
                    client.table("trades").insert(entry_trade).execute()
                    client.table("portfolio_positions").upsert(
                        {
                            "portfolio_id": str(portfolio.id),
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
                    ).eq("id", str(portfolio.id)).execute()

                    # Submit Alpaca OPG Market Order
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

                entries.append({"owner_id": owner_id, "signal": "BUY", "shares": shares, "price": spy_price})

            else:  # DOWN
                trade_id = str(uuid4())
                entry_trade = {
                    "id": trade_id,
                    "portfolio_id": str(portfolio.id),
                    "ticker": ticker,
                    "signal": "SHORT",
                    "quantity": shares,
                    "price": spy_price,
                    "total_cost": shares * spy_price,
                    "executed_at": f"{target_date_str}T13:30:00Z",
                }
                if not dry_run:
                    client.table("trades").insert(entry_trade).execute()
                    # Note: DB constraint quantity_not_negative prevents negative positions in portfolio_positions.
                    # Virtual short is tracked in trades table; Alpaca mirror skipped.

                entries.append({"owner_id": owner_id, "signal": "SHORT", "shares": shares, "price": spy_price})

    return {"status": "success", "entries": entries}


async def place_daily_target_limit_orders(target_date: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Place Alpaca limit sell order at profit target price for target-exit portfolios post-open (~9:35 AM)."""
    client = get_supabase_client()
    target_date_str = target_date or date.today().isoformat()

    # Query target portfolios: sys-daily-spy-{model} (not -close-)
    portfolios_res = (
        client.table("portfolios").select("id, owner_id").like("owner_id", f"{SYS_DAILY_SPY_OWNER_PREFIX}%").execute()
    )
    portfolios = [
        p for p in (portfolios_res.data or []) if not p.get("owner_id", "").startswith(SYS_DAILY_SPY_CLOSE_OWNER_PREFIX)
    ]

    from execution.alpaca_broker import AlpacaBroker

    broker = AlpacaBroker()
    placed_orders = []

    for p in portfolios:
        owner_id = p["owner_id"]
        model_name = owner_id.replace(SYS_DAILY_SPY_OWNER_PREFIX, "")

        # Look up active SPY position
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

        # Fetch expected return from prediction
        pred_res = (
            client.table("daily_predictions")
            .select("expected_return_pct")
            .eq("target_date", target_date_str)
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

    - Cancels any unfilled target limit orders on Alpaca.
    - Sells held SPY shares at market price, deletes portfolio_positions, records SELL trade with realized PnL.
    - Closes virtual SHORT trades with COVER trade, records realized PnL.
    - Updates portfolios cash & equity, and upserts portfolio_performance.
    """
    client = get_supabase_client()
    target_date_str = target_date or date.today().isoformat()

    # Query all daily systematic portfolios
    portfolios_res = (
        client.table("portfolios")
        .select("id, owner_id, cash_balance")
        .like("owner_id", f"{SYS_DAILY_SPY_OWNER_PREFIX}%")
        .execute()
    )
    portfolios = portfolios_res.data or []

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
            cost_basis = float(pos["average_cost_basis"])
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
                        "buying_power": new_cash * 4,
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
                        "buying_power": new_cash * 4,
                        "sma": 0.0,
                        "realized": new_cash,
                    },
                    on_conflict="portfolio_id,date",
                ).execute()

                # Submit market sell order to Alpaca
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
            entry_p = float(st["price"])
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
                "executed_at": f"{target_date_str}T19:30:00Z",
            }

            if not dry_run:
                client.table("trades").insert(exit_trade).execute()
                new_cash = max(0.0, current_cash + realized_pnl)
                client.table("portfolios").update(
                    {
                        "cash_balance": new_cash,
                        "total_equity": new_cash,
                        "realized": new_cash,
                        "buying_power": new_cash * 4,
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
                        "buying_power": new_cash * 4,
                        "sma": 0.0,
                        "realized": new_cash,
                    },
                    on_conflict="portfolio_id,date",
                ).execute()

            exited.append({"owner_id": owner_id, "signal": "COVER", "shares": qty, "pnl": realized_pnl})

    return {"status": "success", "exits": exited}
