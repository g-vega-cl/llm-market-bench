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
from uuid import UUID

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
