---
tags: [short-positions, portfolios, web, engine, pnl]
category: concept
---

# Short Position Display

System portfolios (notably the long/short sector strategies) hold both long and short legs. Because the `portfolio_positions` table enforces a `quantity_not_negative` check constraint, short legs cannot be stored as negative quantities there. Instead, open shorts live in the `trades` table as rows with `signal = 'SHORT'` and `realized_pnl IS NULL`. Both the LLM reporting tools and the web frontend synthesize these two sources on read to present a unified Current Positions view.

## Storage Model

- **Long legs** → `portfolio_positions` (mirrored to Alpaca).
- **Short legs** → `trades` rows with `signal = 'SHORT'` and `realized_pnl IS NULL`.
- **Current prices for shorts** → `market_data_cache`.

## Engine Read Path

`execute_get_system_portfolios_tool` (`apps/engine/analytics/system_portfolios_report.py`) queries open shorts, joins `market_data_cache` for the latest price, and computes inverted mark-to-market PnL:

- `unrealized_pnl_usd = (avg_cost - current_price) * quantity`
- `unrealized_pnl_pct = (avg_cost - current_price) / avg_cost * 100`

Each short line is tagged `[SHORT]` and labeled "Short Entry" instead of "Avg Cost". Long positions are tagged with `side = "LONG"`.

## Web Read Path

`fetchPositions` (`apps/web/src/features/portfolios/api/fetch-portfolios.ts`) fetches `position_pnl` (longs) and open `trades` (shorts) in parallel, resolves current prices from `market_data_cache`, and merges them into a single `PositionWithReasoning[]` with a `side` field of `LONG` or `SHORT`. Shorts fall back to a default reasoning string ("Systematic short sector allocation.") when no matching decision exists. The combined list is sorted by ticker.

## UI

`PositionsTable` renders a `SHORT` badge for short legs and a `LONG` badge for long legs whenever the portfolio holds any shorts. Invested cash and allocation percentages use gross notional exposure (`Math.abs(quantity * average_cost_basis)`), so shorts contribute positively to the totals. The expanded row shows "Sold Short:" with the trade timestamp for shorts, versus "Bought:" for longs.

## Related

- [[concepts/system-portfolios]]
- [[entities/sector-trading]]
- [[entities/web-app]]
