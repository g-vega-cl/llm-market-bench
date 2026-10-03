---
tags: [execution, reconciliation, daily-spy, market-data, pricing]
category: concept
---

# Session Open Reconciliation

Pre-market Market-On-Open (MOO) entries for the daily SPY systematic portfolios are sized and logged before the 9:30 AM ET bell, when data providers still report the *previous* day's close as the current price. Session Open Reconciliation is the mechanism that anchors every daily entry to the official beginning-of-day (9:30 AM ET) regular session open price ($P_{open}$) once real prints are available, so realized PnL reflects the true open-to-close move rather than a stale pre-market quote.

## Why It Exists

Without reconciliation, a MOO entry logged at the prior close (e.g. $763.99) would produce a phantom gain or loss when the actual session opened at a different level (e.g. $770.58). The reconciliation island guarantees that entry price, cost basis, cash balance, and realized PnL are all computed against the same canonical $P_{open}$.

## Resolving the Session Open Price

`get_daily_session_open_price(ticker, target_date)` resolves $P_{open}$ through a three-tier fallback hierarchy:

1. **`daily_predictions.open_price`** — the evaluated/recorded open stored on the prediction row.
2. **`fetch_intraday_prices`** — RTH hourly bars / intraday OHLC from the evaluation task.
3. **Live quote `open_price`** — the `open_price` field on `MarketDataManager` quotes (populated by providers such as FMP from the quote's `open` field).

Each tier is validated to be a positive number before being accepted; if all fail, the function returns `None` and callers skip reconciliation.

## Reconciling Entry Trades

`reconcile_daily_open_trades(target_date)` walks all `sys-daily-spy%` portfolios and, for each day's entry trade (`BUY` or `SHORT`):

- Updates `trades.price` and `trades.total_cost` to $P_{open}$ when the recorded price differs by more than $0.01.
- For `BUY` entries, updates `portfolio_positions.average_cost_basis` to $P_{open}$ and adjusts portfolio cash by the delta `(recorded_price - open_price) * qty` (refunding if the open was lower, deducting if higher).

Reconciliation runs automatically as the first step of `place_daily_target_limit_orders` (~9:35 AM ET) and defensively again inside `execute_daily_close_exits` (~3:30 PM ET), so both the target limit price and the close PnL are anchored to $P_{open}$.

## Audit Coverage

The [[entities/portfolio-auditor]] flags any daily SPY entry whose price drifts more than 0.2% from the session open as `INVALID_ENTRY_PRICE_DAILY_SPY`. In auto-heal mode the auditor resets portfolio cash to prior-day closing equity, removes the stale trades and positions, and re-executes chronologically so compounded returns stay accurate.

## Related

- [[concepts/daily-spy-live-trading]] — the full daily SPY execution lifecycle this reconciliation supports
- [[entities/portfolio-auditor]] — detects and heals desynced entry prices
- [[entities/market-data]] — source of the `open_price` quote field
- [[concepts/vertical-slice-islands]] — the island pattern the reconciliation module follows
