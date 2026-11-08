"""Intraday portfolio management, position sizing, and trade execution island.

Manages the persistent paper portfolio for the live intraday homepage trader:
- Target exposure: 20% of total portfolio equity in SPY on BUY.
- Sell: 100% liquidation of SPY position back to cash.
- Hold: no position modification.
- Session gating: real executions occur strictly during regular market hours.
- Dual execution: records into Supabase ledger and mirrors to Alpaca paper account.
"""

from datetime import date
from typing import Any

from core.config import logger

LIVE_TRADER_OWNER_ID = "live-spy-trader"
INITIAL_PORTFOLIO_CASH = 10000.0
TARGET_ALLOCATION_PCT = 0.20


def compute_intraday_trade_sizing(
    cash_balance: float,
    current_shares: int,
    current_price: float,
    action: str,
    target_pct: float = TARGET_ALLOCATION_PCT,
) -> dict[str, Any]:
    """Calculate target trade quantity based on 20% portfolio equity cap."""
    action_clean = (action or "HOLD").strip().upper()

    if current_price <= 0:
        return {
            "signal": "HOLD",
            "shares": 0,
            "target_equity": cash_balance,
            "target_allocation_dollars": 0.0,
            "current_position_value": 0.0,
            "reason": f"Invalid current price (${current_price:.2f})",
        }

    current_shares = max(0, int(current_shares))
    current_val = float(current_shares * current_price)
    total_equity = float(cash_balance + current_val)
    target_allocation_dollars = float(total_equity * target_pct)

    if action_clean == "BUY":
        if current_val < target_allocation_dollars:
            dollars_to_allocate = target_allocation_dollars - current_val
            shares_to_buy = int(dollars_to_allocate // current_price)
            max_affordable = int(cash_balance // current_price) if cash_balance > 0 else 0
            shares_to_buy = min(shares_to_buy, max_affordable)

            if shares_to_buy > 0:
                return {
                    "signal": "BUY",
                    "shares": shares_to_buy,
                    "target_equity": total_equity,
                    "target_allocation_dollars": target_allocation_dollars,
                    "current_position_value": current_val,
                    "reason": f"Sizing up to 20% target equity ({shares_to_buy} shares @ ${current_price:.2f})",
                }
            return {
                "signal": "HOLD",
                "shares": 0,
                "target_equity": total_equity,
                "target_allocation_dollars": target_allocation_dollars,
                "current_position_value": current_val,
                "reason": "Target 20% allocation reached or insufficient cash for 1 share",
            }
        return {
            "signal": "HOLD",
            "shares": 0,
            "target_equity": total_equity,
            "target_allocation_dollars": target_allocation_dollars,
            "current_position_value": current_val,
            "reason": f"Holding value (${current_val:.2f}) is already at or above 20% target (${target_allocation_dollars:.2f})",
        }

    if action_clean == "SELL":
        if current_shares > 0:
            return {
                "signal": "SELL",
                "shares": current_shares,
                "target_equity": total_equity,
                "target_allocation_dollars": 0.0,
                "current_position_value": current_val,
                "reason": f"Liquidating 100% position ({current_shares} shares @ ${current_price:.2f})",
            }
        return {
            "signal": "HOLD",
            "shares": 0,
            "target_equity": total_equity,
            "target_allocation_dollars": 0.0,
            "current_position_value": 0.0,
            "reason": "No SPY shares currently held to sell",
        }

    return {
        "signal": "HOLD",
        "shares": 0,
        "target_equity": total_equity,
        "target_allocation_dollars": target_allocation_dollars,
        "current_position_value": current_val,
        "reason": "Hold stance maintained",
    }


def get_or_create_live_trader_portfolio(
    sb_client: Any,
    owner_id: str = LIVE_TRADER_OWNER_ID,
) -> dict[str, Any]:
    """Retrieve existing portfolio record or seed new row with initial cash."""
    try:
        res = sb_client.table("portfolios").select("*").eq("owner_id", owner_id).execute()
        data = res.data if isinstance(getattr(res, "data", None), list) else []
        if data and isinstance(data[0], dict):
            return data[0]
    except Exception:
        logger.exception("Error checking portfolios table for live trader")

    init_row = {
        "owner_id": owner_id,
        "cash_balance": INITIAL_PORTFOLIO_CASH,
        "total_equity": INITIAL_PORTFOLIO_CASH,
        "buying_power": INITIAL_PORTFOLIO_CASH,
        "excess_liquidity": INITIAL_PORTFOLIO_CASH,
        "maintenance_margin": 0.0,
        "realized": INITIAL_PORTFOLIO_CASH,
        "sma": INITIAL_PORTFOLIO_CASH,
    }
    try:
        insert_res = sb_client.table("portfolios").insert(init_row).execute()
        if (
            insert_res
            and isinstance(getattr(insert_res, "data", None), list)
            and insert_res.data
            and isinstance(insert_res.data[0], dict)
        ):
            return insert_res.data[0]
    except Exception:
        logger.exception("Error inserting initial live trader portfolio")

    return init_row


def get_live_trader_position(
    sb_client: Any,
    portfolio_id: str,
    ticker: str = "SPY",
) -> dict[str, Any]:
    """Fetch current position for ticker from portfolio_positions."""
    try:
        res = (
            sb_client.table("portfolio_positions")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .eq("ticker", ticker)
            .execute()
        )
        data = res.data if isinstance(getattr(res, "data", None), list) else []
        if data and isinstance(data[0], dict):
            return data[0]
    except Exception:
        logger.exception("Error querying live trader position")

    return {"portfolio_id": portfolio_id, "ticker": ticker, "quantity": 0, "average_cost_basis": 0.0}


async def execute_intraday_portfolio_turn(
    sb_client: Any,
    action: str,
    current_price: float,
    is_market_open: bool,
    thought: str = "",
    alpaca_trading_client: Any = None,
    ticker: str = "SPY",
    owner_id: str = LIVE_TRADER_OWNER_ID,
    target_pct: float = TARGET_ALLOCATION_PCT,
) -> dict[str, Any]:
    """Execute intraday portfolio turn with 20% target allocation rules."""
    portfolio = get_or_create_live_trader_portfolio(sb_client, owner_id=owner_id)
    portfolio_id = str(portfolio.get("id", "live-trader-portfolio-id"))

    raw_cash = portfolio.get("cash_balance")
    try:
        cash_balance = float(raw_cash) if raw_cash is not None else INITIAL_PORTFOLIO_CASH
    except (TypeError, ValueError):
        cash_balance = INITIAL_PORTFOLIO_CASH

    position_record = get_live_trader_position(sb_client, portfolio_id=portfolio_id, ticker=ticker)

    raw_shares = position_record.get("quantity")
    try:
        current_shares = int(raw_shares) if raw_shares is not None else 0
    except (TypeError, ValueError):
        current_shares = 0

    raw_basis = position_record.get("average_cost_basis")
    try:
        cost_basis = float(raw_basis) if raw_basis is not None else 0.0
    except (TypeError, ValueError):
        cost_basis = 0.0

    # 1. Off-hours gate
    if not is_market_open:
        pos_val = current_shares * current_price if current_price > 0 else current_shares * cost_basis
        total_equity = cash_balance + pos_val
        return {
            "status": "MARKET_CLOSED",
            "owner_id": owner_id,
            "portfolio_id": portfolio_id,
            "signal": "HOLD",
            "shares": 0,
            "price": current_price,
            "cash_balance": cash_balance,
            "total_equity": total_equity,
            "position_shares": current_shares,
            "position_cost_basis": cost_basis,
            "position_market_value": pos_val,
            "unrealized_pnl": (current_price - cost_basis) * current_shares
            if current_shares > 0 and current_price > 0
            else 0.0,
            "realized_pnl": 0.0,
            "order_id": None,
            "trade_id": None,
        }

    # 2. Invalid price guard
    if current_price <= 0:
        pos_val = current_shares * cost_basis
        return {
            "status": "INVALID_PRICE",
            "owner_id": owner_id,
            "portfolio_id": portfolio_id,
            "signal": "HOLD",
            "shares": 0,
            "price": current_price,
            "cash_balance": cash_balance,
            "total_equity": cash_balance + pos_val,
            "position_shares": current_shares,
            "position_cost_basis": cost_basis,
            "position_market_value": pos_val,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "order_id": None,
            "trade_id": None,
        }

    # 3. Compute sizing
    sizing = compute_intraday_trade_sizing(
        cash_balance=cash_balance,
        current_shares=current_shares,
        current_price=current_price,
        action=action,
        target_pct=target_pct,
    )

    trade_signal = sizing["signal"]
    shares = sizing["shares"]
    trade_id = None
    order_id = None
    realized_pnl = 0.0

    today_str = date.today().isoformat()

    # 4. Handle BUY
    if trade_signal == "BUY" and shares > 0:
        cost = float(shares * current_price)
        cash_balance -= cost
        new_shares = current_shares + shares
        new_cost_basis = ((current_shares * cost_basis) + cost) / new_shares

        # Ledger trade
        trade_data = {
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "signal": "BUY",
            "quantity": shares,
            "price": current_price,
            "total_cost": cost,
            "reasoning": thought,
        }
        res_trade = sb_client.table("trades").insert(trade_data).execute()
        if res_trade.data:
            trade_id = str(res_trade.data[0].get("id"))

        # Upsert position
        sb_client.table("portfolio_positions").upsert(
            {
                "portfolio_id": portfolio_id,
                "ticker": ticker,
                "quantity": new_shares,
                "average_cost_basis": new_cost_basis,
            },
            on_conflict="portfolio_id,ticker",
        ).execute()

        current_shares = new_shares
        cost_basis = new_cost_basis

        # Submit Alpaca paper order if client exists
        if alpaca_trading_client:
            try:
                from alpaca.trading.enums import OrderSide, TimeInForce
                from alpaca.trading.requests import MarketOrderRequest

                order_req = MarketOrderRequest(
                    symbol=ticker,
                    qty=shares,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                )
                order_res = alpaca_trading_client.submit_order(order_req)
                order_id = str(getattr(order_res, "id", ""))
                logger.info(f"Submitted Alpaca paper BUY order for {shares} {ticker} (ID: {order_id})")
            except Exception:
                logger.exception("Failed to submit Alpaca paper BUY order")

    # 5. Handle SELL
    elif trade_signal == "SELL" and shares > 0:
        proceeds = float(shares * current_price)
        realized_pnl = (current_price - cost_basis) * shares
        cash_balance += proceeds

        trade_data = {
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "signal": "SELL",
            "quantity": shares,
            "price": current_price,
            "total_cost": proceeds,
            "realized_pnl": realized_pnl,
            "reasoning": thought,
        }
        res_trade = sb_client.table("trades").insert(trade_data).execute()
        if res_trade.data:
            trade_id = str(res_trade.data[0].get("id"))

        # Clean position from portfolio_positions
        sb_client.table("portfolio_positions").delete().eq("portfolio_id", portfolio_id).eq("ticker", ticker).execute()

        current_shares = 0
        cost_basis = 0.0

        # Submit Alpaca paper order if client exists
        if alpaca_trading_client:
            try:
                from alpaca.trading.enums import OrderSide, TimeInForce
                from alpaca.trading.requests import MarketOrderRequest

                order_req = MarketOrderRequest(
                    symbol=ticker,
                    qty=shares,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                )
                order_res = alpaca_trading_client.submit_order(order_req)
                order_id = str(getattr(order_res, "id", ""))
                logger.info(f"Submitted Alpaca paper SELL order for {shares} {ticker} (ID: {order_id})")
            except Exception:
                logger.exception("Failed to submit Alpaca paper SELL order")

    # 6. Mark to market & persist portfolio metrics
    pos_market_val = current_shares * current_price
    total_equity = cash_balance + pos_market_val
    unrealized_pnl = (current_price - cost_basis) * current_shares if current_shares > 0 else 0.0

    sb_client.table("portfolios").update(
        {
            "cash_balance": cash_balance,
            "total_equity": total_equity,
            "buying_power": cash_balance,
            "excess_liquidity": cash_balance,
            "last_updated_at": "now()",
        }
    ).eq("id", portfolio_id).execute()

    # Upsert daily performance snapshot so leaderboard immediately displays today's equity
    try:
        sb_client.table("portfolio_performance").upsert(
            {
                "portfolio_id": portfolio_id,
                "total_equity": total_equity,
                "cash_balance": cash_balance,
                "buying_power": cash_balance,
                "sma": cash_balance,
                "date": today_str,
            },
            on_conflict="portfolio_id,date",
        ).execute()
    except Exception:
        logger.exception("Failed to upsert portfolio_performance snapshot for live trader")

    status = "EXECUTED" if (trade_signal in ("BUY", "SELL") and shares > 0) else "NO_OP"

    return {
        "status": status,
        "owner_id": owner_id,
        "portfolio_id": portfolio_id,
        "signal": trade_signal,
        "shares": shares,
        "price": current_price,
        "cash_balance": cash_balance,
        "total_equity": total_equity,
        "position_shares": current_shares,
        "position_cost_basis": cost_basis,
        "position_market_value": pos_market_val,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "order_id": order_id,
        "trade_id": trade_id,
    }
