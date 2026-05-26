import asyncio

from apps.engine.autoresearch.window import get_week_window

from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS
from core.db import get_async_supabase_client


async def test_do_nothing():
    sb_client = await get_async_supabase_client()
    week_start, week_end = get_week_window()
    print(f"Week: {week_start} to {week_end}")

    owner_list = list(AUTORESEARCH_EXPERIMENT_OWNER_IDS)

    # Get portfolio IDs and start of week equity/cash
    res = (
        sb_client.table("portfolio_performance")
        .select("portfolio_id, total_equity, cash_balance, date, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .gte("date", (week_start).isoformat())
        .order("date")
        .limit(len(owner_list))  # Just get the first row for each portfolio on/after week_start
        .execute()
    )
    rows = (await res).data or []
    print("Initial Performance Rows:", rows)

    # Get all trades before week_start
    res_trades = (
        sb_client.table("trades")
        .select("portfolio_id, ticker, signal, quantity, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .lt("executed_at", week_start.isoformat())
        .execute()
    )
    trades = (await res_trades).data or []
    print(f"Found {len(trades)} trades before {week_start}")

    from collections import defaultdict

    positions = defaultdict(lambda: defaultdict(int))
    for t in trades:
        pid = t["portfolio_id"]
        ticker = t["ticker"]
        qty = t["quantity"]
        if t["signal"] == "BUY":
            positions[pid][ticker] += qty
        elif t["signal"] == "SELL":
            positions[pid][ticker] -= qty

    print("Positions at week start:", dict(positions))


if __name__ == "__main__":
    asyncio.run(test_do_nothing())
