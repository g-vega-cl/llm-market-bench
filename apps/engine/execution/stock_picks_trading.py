"""Daily Stock Picker Arena system portfolios (3 UP / 3 DOWN per model track).

Turns each session's baskets in `daily_stock_baskets` into four mechanical long/short
portfolios — one per model track plus the RRF consensus basket:

    sys-picks-deepseek-flash
    sys-picks-MiniMax-M3.1-Flash
    sys-picks-gpt-6-luna
    sys-picks-consensus

Sizing defaults: gross 100%, net 0 — 50% of equity long, 50% short, equal weight per
leg, 5 bps slippage per side. Longs write `portfolio_positions` plus a BUY trade;
shorts live only in `trades` because `portfolio_positions.quantity >= 0`. Entry uses
the session's official open print and exit the official close print, the same basis
`tasks/evaluate_stock_picks.py` grades the picks on, so the portfolio return and the
Picks tab alpha reconcile.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from core.config import logger
from core.db import get_supabase_client
from execution.system_portfolios import DEFAULT_SLIPPAGE_BPS, INITIAL_PORTFOLIO_CASH, get_or_create_system_portfolio
from trading.market_calendar import is_us_trading_day

SYS_PICKS_OWNER_PREFIX = "sys-picks-"
PICKS_MODEL_TRACKS = ("deepseek-flash", "MiniMax-M3.1-Flash", "gpt-6-luna", "consensus")
SYS_PICKS_START_DATE = "2026-11-19"
SESSION_OPEN_ET = time(9, 30)
SESSION_CLOSE_ET = time(16, 0)
LONG_BUDGET_FRACTION = 0.5


def picks_owner_id(model_name: str) -> str:
    """Owner id for a model track, preserving the model's original case."""
    return f"{SYS_PICKS_OWNER_PREFIX}{model_name}"


def trade_timestamp(session_date: str, at: time) -> str:
    """UTC timestamp for an ET session time, DST-correct (unlike legacy hardcoded Z strings)."""
    local = datetime.combine(date.fromisoformat(session_date), at, tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def within_entry_window(now_et: datetime) -> bool:
    """True inside 09:31-10:00 ET, the only window allowed to open a session's legs."""
    return 571 <= now_et.hour * 60 + now_et.minute <= 600


def _price(price_map: dict[str, float], ticker: str) -> float:
    raw = price_map.get(str(ticker).upper())
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return value if value > 0 else 0.0


def _prior_open_dates(client: Any, portfolio_id: str, session_date: str) -> list[str]:
    """Return sorted prior session dates that still have unclosed BUY/SHORT legs."""
    open_trades = (
        client.table("trades")
        .select("signal, executed_at")
        .eq("portfolio_id", portfolio_id)
        .is_("realized_pnl", "null")
        .execute()
        .data
        or []
    )
    return sorted(
        {
            str(t.get("executed_at", ""))[:10]
            for t in open_trades
            if t.get("signal") in ("BUY", "SHORT") and str(t.get("executed_at", ""))[:10] < session_date
        }
    )


def _picks_equity_snapshots(
    client: Any,
    portfolio_id: str,
    session_date: str,
    new_cash: float,
) -> tuple[float, float, float]:
    """Compute (session_equity, total_realized, current_equity) decoupled from later open sessions."""
    all_trades = (
        client.table("trades")
        .select("signal, total_cost, realized_pnl, executed_at")
        .eq("portfolio_id", portfolio_id)
        .execute()
        .data
        or []
    )
    exits = [t for t in all_trades if t.get("signal") in ("SELL", "COVER") and t.get("realized_pnl") is not None]
    if exits:
        session_equity = INITIAL_PORTFOLIO_CASH + sum(
            float(t["realized_pnl"]) for t in exits if str(t.get("executed_at", ""))[:10] <= session_date
        )
        total_realized = INITIAL_PORTFOLIO_CASH + sum(float(t["realized_pnl"]) for t in exits)
    else:
        session_equity = new_cash
        total_realized = new_cash

    open_long_cost = sum(
        float(t.get("total_cost") or 0.0)
        for t in all_trades
        if t.get("signal") == "BUY" and t.get("realized_pnl") is None
    )
    current_equity = max(0.0, new_cash + open_long_cost)
    return session_equity, total_realized, current_equity


def _split_legs(picks: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    longs = sorted(
        [p for p in picks if str(p.get("direction", "")).upper() == "UP"],
        key=lambda p: int(p.get("rank") or 0),
    )
    shorts = sorted(
        [p for p in picks if str(p.get("direction", "")).upper() == "DOWN"],
        key=lambda p: int(p.get("rank") or 0),
    )
    return longs, shorts


def _budgets(equity: float, longs: list[dict], shorts: list[dict]) -> tuple[float, float]:
    if longs and shorts:
        return equity * LONG_BUDGET_FRACTION, equity * (1.0 - LONG_BUDGET_FRACTION)
    if longs:
        return equity, 0.0
    return 0.0, equity


def _open_basket_legs(
    client: Any,
    portfolio_id: str,
    basket_id: str,
    owner_id: str,
    longs: list[dict[str, Any]],
    shorts: list[dict[str, Any]],
    per_long: float,
    per_short: float,
    price_map: dict[str, float],
    slip: float,
    entry_ts: str,
    dry_run: bool,
) -> tuple[list[dict[str, Any]], float]:
    """Insert the entry trades (and long positions) for one basket."""
    legs: list[dict[str, Any]] = []
    long_cost = 0.0

    for pick in longs:
        price = _price(price_map, pick["ticker"])
        if price <= 0:
            logger.warning(f"[{owner_id}] Skipping long {pick['ticker']}: no open price")
            continue
        entry_price = price * (1.0 + slip)
        shares = int(per_long // entry_price) if entry_price > 0 else 0
        if shares <= 0:
            logger.warning(f"[{owner_id}] Skipping long {pick['ticker']}: allocation below one share")
            continue

        trade_id = None
        if not dry_run:
            inserted = (
                client.table("trades")
                .insert(
                    {
                        "portfolio_id": portfolio_id,
                        "ticker": pick["ticker"],
                        "signal": "BUY",
                        "quantity": shares,
                        "price": entry_price,
                        "total_cost": shares * entry_price,
                        "executed_at": entry_ts,
                        "decision_id": basket_id,
                    }
                )
                .execute()
                .data
                or []
            )
            trade_id = inserted[0]["id"] if inserted else None
            client.table("portfolio_positions").upsert(
                {
                    "portfolio_id": portfolio_id,
                    "ticker": pick["ticker"],
                    "quantity": shares,
                    "average_cost_basis": entry_price,
                    "last_updated_at": datetime.now(UTC).isoformat(),
                },
                on_conflict="portfolio_id,ticker",
            ).execute()

        long_cost += shares * entry_price
        legs.append(
            {
                "ticker": pick["ticker"],
                "side": "LONG",
                "quantity": shares,
                "entry_price": entry_price,
                "trade_id": trade_id,
            }
        )

    for pick in shorts:
        price = _price(price_map, pick["ticker"])
        if price <= 0:
            logger.warning(f"[{owner_id}] Skipping short {pick['ticker']}: no open price")
            continue
        entry_price = price * (1.0 - slip)
        shares = int(per_short // entry_price) if entry_price > 0 else 0
        if shares <= 0:
            logger.warning(f"[{owner_id}] Skipping short {pick['ticker']}: allocation below one share")
            continue
        if not dry_run:
            client.table("trades").insert(
                {
                    "portfolio_id": portfolio_id,
                    "ticker": pick["ticker"],
                    "signal": "SHORT",
                    "quantity": shares,
                    "price": entry_price,
                    "total_cost": shares * entry_price,
                    "alpaca_status": "NO_MIRROR",
                    "executed_at": entry_ts,
                    "decision_id": basket_id,
                }
            ).execute()
        legs.append({"ticker": pick["ticker"], "side": "SHORT", "quantity": shares, "entry_price": entry_price})

    return legs, long_cost


async def execute_picks_entries(
    session_date: str,
    price_map: dict[str, float],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    dry_run: bool = False,
    get_supabase_client_fn: Callable | None = None,
    get_or_create_system_portfolio_fn: Callable | None = None,
) -> dict[str, Any]:
    """Open the 3 long / 3 short legs of every basket for one session."""
    if session_date < SYS_PICKS_START_DATE:
        return {"status": "skipped", "reason": f"Before start date {SYS_PICKS_START_DATE}"}
    if not price_map:
        return {"status": "skipped", "reason": "No session open prices"}

    client = (get_supabase_client_fn or get_supabase_client)()
    portfolio_getter = get_or_create_system_portfolio_fn or get_or_create_system_portfolio

    baskets = (
        client.table("daily_stock_baskets")
        .select("*")
        .eq("target_date", session_date)
        .in_("model_name", list(PICKS_MODEL_TRACKS))
        .execute()
        .data
        or []
    )
    if not baskets:
        return {"status": "skipped", "reason": f"No baskets for {session_date}"}

    picks = (
        client.table("daily_stock_picks").select("*").in_("basket_id", [b["id"] for b in baskets]).execute().data or []
    )
    picks_by_basket: dict[str, list[dict[str, Any]]] = {}
    for pick in picks:
        picks_by_basket.setdefault(pick["basket_id"], []).append(pick)

    entry_ts = trade_timestamp(session_date, SESSION_OPEN_ET)
    slip = slippage_bps / 10000.0
    entered: dict[str, Any] = {}
    skipped: dict[str, str] = {}

    for basket in baskets:
        owner_id = picks_owner_id(str(basket["model_name"]))
        basket_picks = picks_by_basket.get(basket["id"], [])
        longs, shorts = _split_legs(basket_picks)
        if not longs and not shorts:
            skipped[owner_id] = "no picks"
            continue

        portfolio = await portfolio_getter(owner_id)
        portfolio_id = str(getattr(portfolio, "id", "") or "")
        if not portfolio_id:
            skipped[owner_id] = "portfolio unavailable"
            continue

        existing = (
            client.table("trades")
            .select("id, ticker, signal")
            .eq("portfolio_id", portfolio_id)
            .eq("executed_at", entry_ts)
            .execute()
            .data
            or []
        )
        if existing:
            skipped[owner_id] = "already entered for this session"
            continue

        prior_dates = _prior_open_dates(client, portfolio_id, session_date)
        if prior_dates:
            skipped[owner_id] = f"unclosed prior legs ({', '.join(prior_dates)})"
            logger.warning(
                f"[{owner_id}] Skipping {session_date} entry: unclosed prior legs on {', '.join(prior_dates)}"
            )
            continue

        equity = float(portfolio.cash_balance)
        long_budget, short_budget = _budgets(equity, longs, shorts)
        per_long = long_budget / len(longs) if longs else 0.0
        per_short = short_budget / len(shorts) if shorts else 0.0

        legs, long_cost = _open_basket_legs(
            client,
            portfolio_id,
            basket["id"],
            owner_id,
            longs,
            shorts,
            per_long,
            per_short,
            price_map,
            slip,
            entry_ts,
            dry_run,
        )

        if not legs:
            skipped[owner_id] = "no priced legs"
            continue

        new_cash = max(0.0, equity - long_cost)
        if not dry_run:
            client.table("portfolios").update(
                {
                    "cash_balance": new_cash,
                    "total_equity": equity,
                    "buying_power": equity,
                    "excess_liquidity": equity,
                    "last_updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", portfolio_id).execute()
            portfolio.cash_balance = new_cash
            await _mirror_long_legs_to_alpaca(legs, owner_id)

        entered[owner_id] = {
            "portfolio_id": portfolio_id,
            "basket_id": basket["id"],
            "legs": legs,
            "long_cost": round(long_cost, 2),
            "cash_after_entry": round(new_cash, 2),
        }
        logger.info(f"[{owner_id}] Picks entry {session_date} (dry_run={dry_run}): {legs}")

    return {
        "status": "success" if entered else "skipped",
        "session_date": session_date,
        "dry_run": dry_run,
        "portfolios": entered,
        "skipped": skipped,
    }


async def execute_picks_exits(
    session_date: str,
    price_map: dict[str, float],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    dry_run: bool = False,
    get_supabase_client_fn: Callable | None = None,
    get_or_create_system_portfolio_fn: Callable | None = None,
) -> dict[str, Any]:
    """Close every leg opened for one session at the official close print."""
    if session_date < SYS_PICKS_START_DATE:
        return {"status": "skipped", "reason": f"Before start date {SYS_PICKS_START_DATE}"}

    client = (get_supabase_client_fn or get_supabase_client)()
    portfolio_getter = get_or_create_system_portfolio_fn or get_or_create_system_portfolio
    exit_ts = trade_timestamp(session_date, SESSION_CLOSE_ET)
    slip = slippage_bps / 10000.0
    closed: dict[str, Any] = {}
    skipped: dict[str, str] = {}

    for model_name in PICKS_MODEL_TRACKS:
        owner_id = picks_owner_id(model_name)
        portfolio = await portfolio_getter(owner_id)
        portfolio_id = str(getattr(portfolio, "id", "") or "")
        if not portfolio_id:
            skipped[owner_id] = "portfolio unavailable"
            continue

        open_trades = (
            client.table("trades")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .is_("realized_pnl", "null")
            .execute()
            .data
            or []
        )
        open_entries = [
            t
            for t in open_trades
            if t.get("signal") in ("BUY", "SHORT") and str(t.get("executed_at", "")).startswith(session_date)
        ]
        if not open_entries:
            skipped[owner_id] = "flat"
            continue

        existing_exits = (
            client.table("trades")
            .select("ticker,signal")
            .eq("portfolio_id", portfolio_id)
            .eq("executed_at", exit_ts)
            .execute()
            .data
            or []
        )
        exited_tickers = {str(row["ticker"]) for row in existing_exits if row.get("signal") in ("SELL", "COVER")}
        remaining = [entry for entry in open_entries if str(entry["ticker"]) not in exited_tickers]
        if not remaining:
            skipped[owner_id] = "already exited for this session"
            continue

        # Fail closed: a session is closed whole or not at all. Writing exits for the
        # priced legs would persist an equity that silently omits the ones we could not price.
        unpriced = sorted({str(entry["ticker"]) for entry in remaining if _price(price_map, entry["ticker"]) <= 0})
        if unpriced:
            skipped[owner_id] = f"missing close price for {','.join(unpriced)}"
            logger.warning(f"[{owner_id}] Leaving {session_date} open: no close price for {', '.join(unpriced)}")
            continue

        cash = float(portfolio.cash_balance)
        long_proceeds = 0.0
        short_pnl_total = 0.0
        realized_pnl_total = 0.0
        legs: list[dict[str, Any]] = []

        for entry in remaining:
            price = _price(price_map, entry["ticker"])
            shares = int(entry["quantity"])
            entry_price = float(entry["price"])
            is_long = entry["signal"] == "BUY"
            exit_price = price * (1.0 - slip) if is_long else price * (1.0 + slip)
            pnl = (exit_price - entry_price) * shares if is_long else (entry_price - exit_price) * shares
            pnl_pct = (
                ((exit_price / entry_price) - 1.0) * 100.0
                if is_long
                else ((entry_price - exit_price) / entry_price) * 100.0
            )
            exit_signal = "SELL" if is_long else "COVER"

            if is_long:
                long_proceeds += shares * exit_price
            else:
                short_pnl_total += pnl
            realized_pnl_total += pnl

            if not dry_run:
                client.table("trades").insert(
                    {
                        "portfolio_id": portfolio_id,
                        "ticker": entry["ticker"],
                        "signal": exit_signal,
                        "quantity": shares,
                        "price": exit_price,
                        "total_cost": shares * exit_price,
                        "realized_pnl": pnl,
                        "realized_pnl_pct": pnl_pct,
                        "alpaca_status": "NO_MIRROR",
                        "executed_at": exit_ts,
                        "decision_id": entry.get("decision_id"),
                    }
                ).execute()
                client.table("trades").update({"realized_pnl": pnl, "realized_pnl_pct": pnl_pct}).eq(
                    "id", entry["id"]
                ).execute()
                if is_long:
                    client.table("portfolio_positions").delete().match(
                        {"portfolio_id": portfolio_id, "ticker": entry["ticker"]}
                    ).execute()

            legs.append({"ticker": entry["ticker"], "side": exit_signal, "quantity": shares, "pnl": round(pnl, 4)})

        if not legs:
            skipped[owner_id] = "no close prices"
            continue

        new_cash = max(0.0, cash + long_proceeds + short_pnl_total)
        session_equity, total_realized, current_equity = _picks_equity_snapshots(
            client, portfolio_id, session_date, new_cash
        )
        if not dry_run:
            client.table("portfolios").update(
                {
                    "cash_balance": new_cash,
                    "total_equity": current_equity,
                    "realized": total_realized,
                    "buying_power": current_equity,
                    "excess_liquidity": current_equity,
                    "last_updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", portfolio_id).execute()
            client.table("portfolio_performance").upsert(
                {
                    "portfolio_id": portfolio_id,
                    "date": session_date,
                    "total_equity": session_equity,
                    "cash_balance": session_equity,
                    "buying_power": session_equity,
                    "sma": 0.0,
                    "realized": session_equity,
                },
                on_conflict="portfolio_id,date",
            ).execute()
            # `Portfolio.total_equity` is a derived property (metrics → cash), so the
            # in-memory object is never told its equity; the row written above is truth.
            portfolio.cash_balance = new_cash

        closed[owner_id] = {
            "portfolio_id": portfolio_id,
            "legs": legs,
            "realized_pnl": round(realized_pnl_total, 4),
            "equity": round(session_equity, 2),
        }
        logger.info(f"[{owner_id}] Picks exit {session_date} (dry_run={dry_run}): equity ${session_equity:,.2f}")

    return {
        "status": "success" if closed else "skipped",
        "session_date": session_date,
        "dry_run": dry_run,
        "portfolios": closed,
        "skipped": skipped,
    }


async def get_picks_portfolios_status() -> dict[str, Any]:
    """Current legs, cash and equity for every sys-picks-* portfolio."""
    client = get_supabase_client()
    summary: dict[str, Any] = {}

    for model_name in PICKS_MODEL_TRACKS:
        owner_id = picks_owner_id(model_name)
        portfolio = await get_or_create_system_portfolio(owner_id)
        if not portfolio.id:
            summary[owner_id] = {"portfolio_id": None, "positions": [], "open_trades": []}
            continue
        positions = (
            client.table("portfolio_positions")
            .select("ticker, quantity, average_cost_basis")
            .eq("portfolio_id", str(portfolio.id))
            .execute()
            .data
            or []
        )
        open_trades = (
            client.table("trades")
            .select("id, ticker, signal, quantity, price, executed_at")
            .eq("portfolio_id", str(portfolio.id))
            .is_("realized_pnl", "null")
            .execute()
            .data
            or []
        )
        summary[owner_id] = {
            "portfolio_id": str(portfolio.id),
            "cash_balance": portfolio.cash_balance,
            "total_equity": portfolio.total_equity,
            "positions": positions,
            "open_trades": open_trades,
        }
    return summary


async def _mirror_long_legs_to_alpaca(legs: list[dict[str, Any]], owner_id: str) -> None:
    """Mirror long legs to the Alpaca paper book; failures never block DB truth."""
    from core.config import ALPACA_API_KEY, ALPACA_SECRET_KEY

    if not (ALPACA_API_KEY and ALPACA_SECRET_KEY):
        return
    try:
        from execution.alpaca_broker import AlpacaBroker

        broker = AlpacaBroker()
        for leg in legs:
            if leg["side"] != "LONG" or not leg.get("trade_id"):
                continue
            await broker.submit_limit_order(
                trade_id=UUID(str(leg["trade_id"])),
                ticker=leg["ticker"],
                quantity=int(leg["quantity"]),
                signal="BUY",
                limit_price=round(float(leg["entry_price"]), 2),
                agent_id=owner_id,
            )
    except Exception:
        logger.exception(f"Alpaca mirror error during picks entry for {owner_id}")


async def _picks_entry_tickers(client: Any, session_date: str) -> list[str]:
    """Tickers in today's baskets that need an opening quote."""
    baskets = (
        client.table("daily_stock_baskets")
        .select("id")
        .eq("target_date", session_date)
        .in_("model_name", list(PICKS_MODEL_TRACKS))
        .execute()
        .data
        or []
    )
    if not baskets:
        return []
    picks = (
        client.table("daily_stock_picks").select("ticker").in_("basket_id", [b["id"] for b in baskets]).execute().data
        or []
    )
    return sorted({str(p["ticker"]).upper() for p in picks if p.get("ticker")})


async def _picks_open_leg_tickers(client: Any) -> list[str]:
    """Tickers with an open BUY/SHORT leg across the four picks portfolios."""
    tickers: set[str] = set()
    portfolios = (
        client.table("portfolios")
        .select("id")
        .in_("owner_id", [picks_owner_id(m) for m in PICKS_MODEL_TRACKS])
        .execute()
        .data
        or []
    )
    for portfolio in portfolios:
        open_trades = (
            client.table("trades")
            .select("ticker")
            .eq("portfolio_id", str(portfolio["id"]))
            .is_("realized_pnl", "null")
            .execute()
            .data
            or []
        )
        tickers.update(str(t.get("ticker", "")).upper() for t in open_trades if t.get("ticker"))
    return sorted(tickers)


async def run_picks_trade(
    action: str = "entry",
    target_date: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Orchestrate picks portfolio entry, exit, or status with live quotes."""
    if action == "status":
        return {"status": "success", "action": "status", "portfolios": await get_picks_portfolios_status()}

    now_et = datetime.now(ZoneInfo("America/New_York"))
    session_date = target_date or now_et.date().isoformat()
    if session_date < SYS_PICKS_START_DATE:
        return {"status": "skipped", "reason": f"Before start date {SYS_PICKS_START_DATE}"}

    if not is_us_trading_day(date.fromisoformat(session_date[:10])):
        return {"status": "skipped", "reason": f"Not a US trading day: {session_date}"}

    from execution.market_data import MarketDataManager

    client = get_supabase_client()
    mdm = MarketDataManager()

    if action in ("entry", "open"):
        if session_date == now_et.date().isoformat() and not within_entry_window(now_et):
            return {"status": "skipped", "reason": "Outside the 09:31-10:00 ET entry window"}
        tickers = await _picks_entry_tickers(client, session_date)
        if not tickers:
            return {"status": "skipped", "reason": f"No picks to trade for {session_date}"}
        quotes = await mdm.get_quotes(tickers, force_refresh=True)
        price_map = {}
        for ticker, quote in quotes.items():
            open_price = quote.open_price if getattr(quote, "open_price", None) else quote.price
            if open_price and open_price > 0:
                price_map[ticker] = float(open_price)
        return await execute_picks_entries(session_date, price_map, dry_run=dry_run)

    if action in ("exit", "close"):
        tickers = await _picks_open_leg_tickers(client)
        if not tickers:
            return {"status": "skipped", "reason": "No open picks legs to close"}
        quotes = await mdm.get_quotes(tickers, force_refresh=True)
        price_map = {t: float(q.price) for t, q in quotes.items() if q.price and q.price > 0}
        return await execute_picks_exits(session_date, price_map, dry_run=dry_run)

    return {"status": "error", "message": f"Unsupported action: {action}"}
