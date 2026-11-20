---
tags: [concept, execution, daily-predictor, spy, moo]
category: concept
---

# Daily SPY Live Trading

`apps/engine/execution/daily_live_trading.py` — turns the daily SPY directional
forecasts into real market-on-open (MOO) entries, and later settles the exits.

## MOO Entry Path

`execute_daily_moo_entries(target_date=None, dry_run=False)`

1. Resolves the target date (defaults to today) and queries `daily_predictions`
   for that date **filtered to `ticker = "SPY"`** at the database level.
2. If no SPY predictions exist, logs `No daily SPY predictions found for
   <date>. Skipping MOO entry.` and returns
   `{"status": "skipped", "reason": "No predictions found", "entries": []}`.
3. Fetches a quote through `MarketDataManager` and, for each allowed owner,
   resolves the system portfolio via `get_or_create_system_portfolio`.
4. For each prediction, re-normalizes the ticker
   (`str(pred.get("ticker", "SPY")).strip().upper()`) and skips anything that is
   not `SPY` before sizing the position.
5. Skips any prediction whose `model_name` is not in
   `ALLOWED_DAILY_SPY_MODELS` (see [[concepts/daily-spy-owner-allowlist]]), then
   resolves the target owner set with `resolve_daily_spy_owners(model_name,
   expected_return_pct)` — the close owner always, plus the intraday target-exit
   owner when the magnitude is non-zero.
6. Delegates each per-portfolio entry to `_execute_single_moo_portfolio_entry`,
   which performs the idempotency check, sizes the position, writes the trade /
   position / cash rows, and submits the Alpaca OPG market order.
7. Submits the order through `AlpacaBroker.submit_market_order` and records the
   trade row.

### SPY-Only Guarantee

The MOO path is deliberately single-instrument. The ticker filter is applied
both in the Supabase query (`.eq("ticker", "SPY")`) and again in the Python
loop, so a mixed batch of SPY and TLT predictions can never leak a bond trade
into the equity entry path. TLT forecasts are executed by their own pipeline —
see [[concepts/daily-tlt-live-trading]].

### Arena-Model-Only Guarantee

The entry path is also single-arena: only the three active SPY predictor models
(`deepseek-flash`, `MiniMax-M3.1-Flash`, `~typesafe/jev-latest`) ever get a
portfolio. A `gpt-6-luna` SPY row — `gpt-6-luna` runs the TLT and Picks arenas,
not SPY — is logged and skipped, so no `sys-daily-spy-gpt-6-luna` portfolio is
ever created. The allowlist and its lifecycle-wide enforcement are documented in
[[concepts/daily-spy-owner-allowlist]].

## Target Limit Orders

`place_daily_target_limit_orders` (~9:35 AM ET) filters the `sys-daily-spy-%`
portfolios through `is_allowed_daily_spy_owner` and scopes its
`daily_predictions` lookup with `.eq("ticker", "SPY")`, so a same-day TLT
prediction for the same model can never supply the wrong profit target.

## Position Sizing

Direction comes from `predicted_direction` (normalized to upper case). Expected
return is taken as `abs(expected_return_pct)`, defaulting to `0.0` when the
field is null, and drives the notional allocated from the system portfolio's
cash balance.

## Exit Path

`execute_daily_close_exits` settles open daily trades at the close, including
short entries, writing `realized_pnl` back onto the entry trade row so the entry
and the cover stay reconciled. Its `sys-daily-spy%` portfolio set is filtered
through `is_allowed_daily_spy_owner`, so archived or stray owners are never
liquidated by the close path.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-postmortem]]
- [[concepts/execution]]
- [[concepts/system-portfolios]]
- [[concepts/daily-spy-owner-allowlist]]
- [[concepts/daily-tlt-live-trading]]
- [[concepts/alpaca-order-sync]]
