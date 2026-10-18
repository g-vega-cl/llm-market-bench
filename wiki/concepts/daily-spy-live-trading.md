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
3. Fetches a quote through `MarketDataManager` and resolves the system portfolio
   via `get_or_create_system_portfolio`.
4. For each prediction, re-normalizes the ticker
   (`str(pred.get("ticker", "SPY")).strip().upper()`) and skips anything that is
   not `SPY` before sizing the position.
5. Submits the order through `AlpacaBroker.submit_market_order` and records the
   trade row.

### SPY-Only Guarantee

The MOO path is deliberately single-instrument. The ticker filter is applied
both in the Supabase query (`.eq("ticker", "SPY")`) and again in the Python
loop, so a mixed batch of SPY and TLT predictions can never leak a bond trade
into the equity entry path. TLT forecasts are executed by their own pipeline —
see [[concepts/daily-tlt-live-trading]].

## Position Sizing

Direction comes from `predicted_direction` (normalized to upper case). Expected
return is taken as `abs(expected_return_pct)`, defaulting to `0.0` when the
field is null, and drives the notional allocated from the system portfolio's
cash balance.

## Exit Path

`execute_daily_close_exits` settles open daily trades at the close, including
short entries, writing `realized_pnl` back onto the entry trade row so the entry
and the cover stay reconciled.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-postmortem]]
- [[concepts/execution]]
- [[concepts/system-portfolios]]
- [[concepts/daily-tlt-live-trading]]
- [[concepts/alpaca-order-sync]]
