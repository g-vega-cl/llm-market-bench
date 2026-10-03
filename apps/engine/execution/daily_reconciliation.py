"""Daily Session Open Reconciliation Island.

Reconciles pre-market MOO entry trades and portfolio positions to the official
beginning-of-day (9:30 AM ET) regular session open price.
"""

from datetime import UTC, date, datetime
from typing import Any

from core.config import logger

SYS_DAILY_SPY_CLOSE_OWNER_PREFIX = "sys-daily-spy-close-"
SYS_DAILY_SPY_OWNER_PREFIX = "sys-daily-spy-"


def _get_client(client: Any | None = None) -> Any:
    if client is not None:
        return client
    import execution.daily_trading as dt

    return dt.get_supabase_client()


async def get_daily_session_open_price(
    ticker: str = "SPY",
    target_date: str | None = None,
    client: Any | None = None,
) -> float | None:
    """Resolve official beginning-of-day (9:30 AM ET) regular session open price.

    Checks:
    1. Evaluated or recorded open price in daily_predictions table.
    2. RTH hourly bars or intraday OHLC from fetch_intraday_prices.
    3. Live quote open_price from MarketDataManager.
    """
    target_date_str = target_date or date.today().isoformat()
    sb = _get_client(client)

    # 1. Check daily_predictions table
    try:
        pred_res = (
            sb.table("daily_predictions")
            .select("open_price")
            .eq("target_date", target_date_str)
            .eq("ticker", ticker.upper())
            .execute()
        )
        if pred_res.data:
            val = pred_res.data[0].get("open_price")
            if val is not None and isinstance(val, (int, float, str)):
                try:
                    fval = float(val)
                    if fval > 0:
                        return fval
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        logger.debug(f"Could not read open price from daily_predictions for {ticker} on {target_date_str}: {e}")

    # 2. Check fetch_intraday_prices
    try:
        from tasks.evaluate_daily_predictions import fetch_intraday_prices

        open_p, _, _, _ = await fetch_intraday_prices(ticker, target_date_str)
        if open_p is not None and isinstance(open_p, (int, float, str)):
            try:
                fval = float(open_p)
                if fval > 0:
                    return fval
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.debug(f"fetch_intraday_prices open lookup failed for {ticker} on {target_date_str}: {e}")

    # 3. Check live quote open_price if checking today
    try:
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        quote = await mdm.get_quote(ticker, force_refresh=True)
        quote_open = getattr(quote, "open_price", None) if quote else None
        if quote_open is not None and isinstance(quote_open, (int, float, str)):
            try:
                fval = float(quote_open)
                if fval > 0:
                    return fval
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.debug(f"Quote open_price lookup failed for {ticker}: {e}")

    return None


async def reconcile_daily_open_trades(
    target_date: str | None = None,
    dry_run: bool = False,
    client: Any | None = None,
) -> dict[str, Any]:
    """Reconcile provisional MOO entry trade price and position cost basis to session open.

    Pre-market quotes often report previous day's close. Once market opens at 9:30 AM,
    this function reconciles all daily SPY entry trades for the target date to the true
    session open price, adjusting position cost basis and cash balances accordingly.
    """
    client = _get_client(client)
    target_date_str = target_date or date.today().isoformat()

    open_price = await get_daily_session_open_price("SPY", target_date_str, client=client)
    if not open_price or open_price <= 0:
        logger.warning(f"Cannot reconcile open trades for {target_date_str}: session open price unavailable.")
        return {"status": "skipped", "reason": "Open price unavailable"}

    portfolios_res = (
        client.table("portfolios").select("id, owner_id, cash_balance").like("owner_id", "sys-daily-spy%").execute()
    )
    portfolios = portfolios_res.data or []
    if not portfolios:
        return {"status": "skipped", "reason": "No daily SPY portfolios"}

    reconciled = []

    for p in portfolios:
        portfolio_id = p["id"]
        owner_id = p["owner_id"]
        current_cash = float(p.get("cash_balance") or 0.0)

        trades_res = (
            client.table("trades")
            .select("id, signal, price, quantity, total_cost")
            .eq("portfolio_id", portfolio_id)
            .gte("executed_at", f"{target_date_str}T00:00:00Z")
            .lte("executed_at", f"{target_date_str}T23:59:59Z")
            .execute()
        )
        day_trades = trades_res.data or []
        entry_trades = [t for t in day_trades if t.get("signal") in ("BUY", "SHORT")]
        if not entry_trades:
            continue

        entry_trade = entry_trades[0]
        recorded_price = float(entry_trade["price"])
        qty = int(entry_trade["quantity"])

        if abs(recorded_price - open_price) > 0.01:
            logger.info(
                f"Reconciling {owner_id} entry trade from ${recorded_price:.2f} to session open ${open_price:.2f} (qty={qty})"
            )
            if not dry_run:
                # Update entry trade price and total cost
                client.table("trades").update(
                    {
                        "price": open_price,
                        "total_cost": qty * open_price,
                    }
                ).eq("id", entry_trade["id"]).execute()

                # If long, update portfolio_positions average cost basis and rebalance cash
                if entry_trade.get("signal") == "BUY":
                    client.table("portfolio_positions").update(
                        {
                            "average_cost_basis": open_price,
                            "last_updated_at": datetime.now(UTC).isoformat(),
                        }
                    ).eq("portfolio_id", portfolio_id).eq("ticker", "SPY").execute()

                    # Cash adjustment: refund difference if open was lower, deduct if open was higher
                    cash_delta = (recorded_price - open_price) * qty
                    new_cash = max(0.0, current_cash + cash_delta)
                    client.table("portfolios").update(
                        {
                            "cash_balance": new_cash,
                            "last_updated_at": datetime.now(UTC).isoformat(),
                        }
                    ).eq("id", portfolio_id).execute()

            reconciled.append(
                {
                    "owner_id": owner_id,
                    "trade_id": entry_trade["id"],
                    "old_price": recorded_price,
                    "new_price": open_price,
                    "quantity": qty,
                }
            )

    return {"status": "success", "reconciled": reconciled, "open_price": open_price}
