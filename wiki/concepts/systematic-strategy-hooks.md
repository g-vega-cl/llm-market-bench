---
tags: [execution, scheduling, systematic-strategies, market-hours, orchestration]
category: concept
---

# Systematic Strategy Hooks

A single orchestrating function in the price-update script — `run_systematic_strategy_hooks()` — drives every clock-driven, non-LLM strategy trigger off US/Eastern market hours. It exists so that systematic strategies (weekly sector exits, options Max Pain, PEAD drift rebalance) fire at the correct intraday moment regardless of which cron invocation happens to run.

## Why It Exists

The daily price update (`apps/engine/scripts/update_prices.py`) is invoked repeatedly through market hours. Rather than scattering ad-hoc `if now_et.hour ...` branches throughout the script, all time-gated strategy triggers live behind one function that is called **before** portfolios are loaded. This ordering matters: the hooks may liquidate positions or spend cash, and those effects must be reflected in the portfolio snapshots loaded immediately afterward.

## The Hooks

`run_systematic_strategy_hooks(now_et, dry_run)` evaluates the current ET time and dispatches up to three strategy families. Each is wrapped in its own try/except so a failure in one strategy never blocks the others.

| Window (ET) | Condition | Trigger |
|---|---|---|
| Friday, ≥ 15:25 | `weekday() == 4` | `run_sector_trade(action="exit")` — weekly sector portfolio exit |
| Mon–Thu, ≥ 15:25 | `weekday() in (0,1,2,3)` | `execute_horizon_sector_exits(...)` — horizon sector exits |
| ≥ 15:45 | any day | `run_max_pain_task(action="exit")` — market-close Max Pain liquidation |
| 09:00–15:44 | any day | `run_max_pain_task(action="entry")` — intraday Max Pain evaluation/entry |
| 09:35–10:35 | any day | `run_pead_drift_task(...)` — morning PEAD drift evaluation and rebalance |

### Sector exits (Friday / horizon)

After 15:25 ET the hook checks the weekday. Fridays run the weekly sector portfolio exit via [[entities/sector-trading]]; Monday–Thursday run the horizon-based exits via `sector_horizon_trading`. Both are failsafes for the 15:30 / 16:00 runs.

### Options Max Pain ([[concepts/max-pain-pinning]])

Two windows: entries are evaluated during the regular intraday window (09:00–15:44), while the final 15 minutes (≥ 15:45) are reserved for liquidation/exit as the pinning effect resolves into the close.

### PEAD drift ([[concepts/pead-drift]])

A single morning window (09:35–10:35 ET) rebalances the `sys-pead-drift` portfolio as the post-earnings drift position is established into the open. The same task is *also* invoked as a hook from the earnings-alpha pipeline (see below).

## Dry-Run Support

Every hook accepts a `dry_run` flag that is threaded through to the underlying strategy calls, allowing the whole orchestration to be simulated without executing trades. `update_prices(dry_run=...)` forwards its flag into the hook function.

## Earnings-Alpha Trigger

Besides the time-of-day windows, the systematic PEAD strategy is also re-evaluated whenever fresh earnings surprises land. `apps/engine/scripts/update_earnings_alpha.py` calls `run_pead_drift_task()` at the end of its snapshot upsert, so newly computed SUE scores feed directly into the drift portfolio without waiting for the next morning window.

## Metric Persistence

Strategies invoked through these hooks (Max Pain, PEAD) now fully refresh and persist portfolio accounting — they call `portfolio.calculate_reg_t_metrics(current_prices)` followed by `await portfolio.save_metrics()` before upserting to `portfolio_performance`. This replaces the earlier stub values (buying power assumed as 2× cash, SMA forced to 0, realized set equal to total equity) with real Reg T metrics and the true SMA. See [[concepts/pending-settlement-state]] and [[entities/portfolio-auditor]] for the surrounding accounting model.

## Related

- [[entities/pipeline]]
- [[concepts/max-pain-pinning]]
- [[concepts/pead-drift]]
- [[entities/sector-trading]]
- [[concepts/execution]]
- [[concepts/pending-settlement-state]]
