---
tags: [sentiment-fader, execution, cooldown, fail-closed, options]
category: concept
---

# Sentiment Fader Re-entry Cooldown & Fail-Closed Ticks

The [[entities/sentiment-fader]] strategy runs on a 5-minute systematic hook during the session, so every tick sees a fresh plan. Two invariants keep that cadence from churning capital or acting on incomplete data:

1. a ticker that has been **exited today (ET)** is blocked from re-entry for the rest of the session, and
2. a tick that cannot read the trade ledger or a live price for a held position **aborts** rather than trading blind.

## Same-Day Exit Cooldown

`compute_sentiment_fader_rebalance_orders` accepts `cooldown_tickers` and builds

```python
blocked_tickers = retained_tickers | exited_tickers | normalized_cooldown
```

where `exited_tickers` are the tickers this tick is selling and `cooldown_tickers` are every ticker with a `SELL` executed since the start of the current `America/New_York` day. A blocked ticker is dropped from `eligible_candidates` even when its Put/Call ratio still qualifies as an extreme-panic entry.

Without this, a 1.5% adverse stop-loss liquidation would immediately re-qualify the same ticker (its P/C ratio is unchanged by a stop) and churn the position back in on the very next tick, structurally locking in the loss.

`_load_recent_trade_state(portfolio_id)` loads this in **one** query: the last 500 trades for the portfolio (`ticker, signal, executed_at`, newest first) are folded into `(holding_days_by_ticker, same_day_exited)`. Holding days come from the most recent `BUY` per ticker; `same_day_exited` collects `SELL` tickers whose `executed_at >= start_of_day_utc` (the ET day boundary converted to UTC, so DST is handled by the zone database rather than a fixed offset).

## Fail-Closed Ticks

Because the cooldown is the strategy's only anti-churn guard, a ledger read failure cannot degrade to "no cooldown":

- **Trade state lookup fails** → the task returns `{"status": "error", ...}` before evaluating anything. No entries, no exits.
- **Held position has no live spot price** → `_evaluate_holdings` raises and the tick aborts. Previously a missing quote silently substituted `average_cost_basis`, which meant a position could be liquidated (or marked) at a historical price and could falsely trip the max-holding-days or stop-loss rules.
- **A planned `SELL` returns no trade id** → dependent `BUY`s for that tick are aborted and the tick returns `status: "error"`. Frees-cash-then-buy ordering must never proceed on capital that was not actually realized.

Each of these paths is covered hermetically (`test_run_sentiment_fader_task_fails_closed_when_trade_state_lookup_fails`, `..._fails_closed_on_missing_held_quote`, `..._aborts_buys_when_sell_fails`).

## Execution & Snapshotting

The rebalance plan is executed by `_execute_rebalance_plan`, which calls `Portfolio.execute_trade` for every sale then every buy (see [[concepts/atomic-trade-execution]]) with an explicit `reason` — `Contrarian Panic Entry (P/C: <ratio>)` for entries and the exit rule's own text for liquidations — so the ledger carries the trigger. After any fills, one `portfolio.record_performance_snapshot(current_prices)` writes the ET-dated `portfolio_performance` row; the ad-hoc upsert that previously duplicated that shape is gone.

## Related

- [[entities/sentiment-fader]] — the portfolio, defaults, and exit rules
- [[concepts/options-sentiment-fading]] — the underlying microstructure thesis
- [[concepts/atomic-trade-execution]] — the RPC every fill commits through
- [[concepts/systematic-strategy-hooks]] — the 5-minute intraday tick that invokes this task
- [[concepts/backfilled-trades]] — how stale legs are reconciled after the fact
