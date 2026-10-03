---
tags: [daily-predictor, spy, alpaca, execution, live-trading]
category: concept
---

# Daily SPY Live Trading Lifecycle

The daily SPY systematic portfolios (`sys-daily-spy-{model}` and `sys-daily-spy-close-{model}`) execute a fully live intraday lifecycle against the Alpaca paper broker, replacing the earlier retroactive backfill model. Trades are entered pre-market, managed during the session, and liquidated before the close. The lifecycle is driven by the `daily-trade` command and two `run_ingest` hooks.

## Phases

### 1. Pre-Market MOO Entry (~9:20 AM ET)
`main.py daily-trade --action entry` runs in `.github/workflows/daily-predictor.yml` before the 9:28 AM ET Alpaca cutoff. `execute_daily_moo_entries`:

- Reads `daily_predictions` for the target date.
- For `UP` predictions: allocates available cash, inserts a `BUY` trade, upserts the SPY holding in `portfolio_positions`, deducts cash, and submits a `MarketOrderRequest` with `TimeInForce.OPG` for the opening cross.
- For `DOWN` predictions: logs a virtual `SHORT` trade in `trades` only — no `portfolio_positions` row and no Alpaca order (guardrail against shorting).
- Target-exit portfolios (`sys-daily-spy-{model}`) only enter when `expected_return_pct > 0` and the model is not Jev; close-exit portfolios (`sys-daily-spy-close-{model}`) always enter.

### 2. Session Open Price Reconciliation (~9:35 AM ET)
`main.py daily-trade --action open` (or `reconcile_daily_open_trades`) runs after the 9:30 AM open once official market prints are established. Pre-market quotes from data providers often report the previous day's close as current price before the 9:30 AM bell.

- Resolves canonical session open price ($P_{open}$) via `get_daily_session_open_price()` from `daily_predictions`, FMP intraday 1-minute bars, or FMP quote `open_price`.
- Reconciles entry `trades.price` and `total_cost` to $P_{open}$ (plus slippage).
- Adjusts `portfolio_positions.average_cost_basis` and updates portfolio cash balance to reflect actual session entry cost.

### 3. Target Limit Orders (~9:35 AM ET)
`place_daily_target_limit_orders` runs from the morning `run_ingest` hook. For each target-exit portfolio holding SPY, it submits an Alpaca limit sell at `cost_basis * (1 + expected_return_pct / 100)`. If touched intraday, Alpaca fills the limit order.

### 4. Afternoon Close Exit (~3:30 PM ET)
`execute_daily_close_exits` runs from the afternoon `run_ingest` hook (`main.py daily-trade --action exit`). It:

- Defensively reconciles entry price to $P_{open}$ if unadjusted.
- Cancels any unfilled target limit orders via `cancel_open_orders_for_agent`.
- Sells held SPY shares at market, deletes the `portfolio_positions` row, and records a `SELL` trade with realized PnL computed strictly against $P_{open}$.
- Closes virtual `SHORT` trades with a `COVER` trade and realized PnL.
- Updates portfolio cash/equity and upserts `portfolio_performance`.

## Alpaca Broker Support

- `AlpacaBroker.submit_market_order` — fire-and-forget market order supporting `DAY` and `OPG` time-in-force. Sell orders are capped to the actual Alpaca position; sells with no position are marked `SKIPPED_NO_POSITION`.
- `AlpacaBroker.cancel_open_orders_for_agent` — cancels open orders whose `client_order_id` is prefixed with the agent id.

## Idempotency & Backfill

- Entry checks for an existing trade on the target date before inserting, so re-runs never double-buy.
- `evaluate_daily_predictions` no longer executes trades by default; retroactive execution is gated behind `--backfill-trades` (default `False`) because live trades now run during market hours.

## Command Interface

`python main.py daily-trade --action {entry|open|target-orders|exit|close}`

## Related

- [[concepts/system-portfolios]]
- [[concepts/alpaca-order-sync]]
- [[concepts/execution]]
- [[entities/daily-market-predictor]]
