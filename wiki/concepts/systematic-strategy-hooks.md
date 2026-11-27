---
tags: [execution, scheduling, systematic-strategies, market-hours, orchestration]
category: concept
---

# Systematic Strategy Hooks

A single orchestrating function — `run_systematic_strategy_hooks()` in `apps/engine/scripts/update_prices.py` — drives every clock-driven, non-LLM strategy trigger off US/Eastern market hours. It exists so that systematic strategies (weekly sector exits, options Max Pain, PEAD drift rebalance, contrarian sentiment fader, and daily stock pick legs) fire at the correct intraday moment regardless of which tick happens to invoke them.

## Why It Exists

The hooks are driven by the `live-spy-trader` daemon on the MiniPC, not by GitHub Actions. `trading/runner.py` runs `run_systematic_hooks_loop` every 300 seconds while `_is_hooks_window()` is true, and that is the **only** caller of the hook function: the price-update script no longer invokes it, so two schedulers can never execute the same strategy against the same portfolio at once.

`_is_hooks_window()` is derived from the exchange calendar (`MarketCalendar.session_for`, see [[entities/market-calendar]]) rather than the wall clock: it is true from the session open through five minutes past the session close. Holidays return no session, so no hook runs; a half day ends at 13:00 ET and the closing-print tail moves with it. The five-minute tail exists so close-print strategies (the daily stock pick portfolios) can exit on the official closing price, which only exists after the bell. `_is_price_refresh_window` delegates to the same window, so portfolio marks and the hooks can never disagree about whether the market is open.

All time-gated strategy triggers live behind one function that is called **before** portfolios are marked. This ordering matters: the hooks may liquidate positions or spend cash, and those effects must be reflected in the portfolio snapshots taken immediately afterward. Inside the daemon the hooks and the marks loop share a single `asyncio.Lock`, which preserves that guarantee instead of relying on task scheduling luck.

## The Hooks

`run_systematic_strategy_hooks(now_et, dry_run)` evaluates the current ET time and dispatches the strategy families below. Each is wrapped in its own try/except so a failure in one strategy never blocks the others.

| Window (ET) | Condition | Trigger |
|---|---|---|
| Friday, ≥ 15:25 | `weekday() == 4` | `run_sector_trade(action="exit")` — weekly sector portfolio exit |
| Mon–Thu, ≥ 15:25 | `weekday() in (0,1,2,3)` | `execute_horizon_sector_exits(...)` — horizon sector exits |
| ≥ exit deadline (15:50 ET; early-close − 10 min) | any day | `run_max_pain_task(action="exit")` — market-close Max Pain liquidation |
| 09:00–exit deadline | any day | `run_max_pain_task(action="entry")` — intraday Max Pain evaluation/entry |
| 09:35–10:35 | any day | `run_pead_drift_task(...)` — morning PEAD drift evaluation and rebalance |
| 09:35–15:45 | any day | `run_sentiment_fader_task(...)` — contrarian options sentiment fader evaluation |
| 09:31–10:00 | weekday | `run_picks_trade(action="entry")` — daily stock pick legs open at the RTH open print |
| 16:00–16:05 | weekday | `run_picks_trade(action="exit")` — daily stock pick legs close at the official closing print |

### Sector exits (Friday / horizon)

After 15:25 ET the hook checks the weekday. Fridays run the weekly sector portfolio exit via [[entities/sector-trading]]; Monday–Thursday run the horizon-based exits via `sector_horizon_trading`. Both are failsafes for the 15:30 / 16:00 runs.

### Options Max Pain ([[concepts/max-pain-pinning]])

Two windows: entries and intraday target/stop checks run during the regular intraday window (09:00 ET until the Max Pain exit deadline), while the deadline — `min(15:50 ET, session_close − 10 min)` (`_max_pain_exit_deadline`) — is reserved for liquidation/exit as the pinning effect resolves into the close (12:50 ET on 13:00 ET half-days). Any position still unliquidated after an exit pass logs `UNLIQUIDATED_MAX_PAIN_AFTER_EXIT_PASS` and retries on the next tick; at audit time [[entities/portfolio-auditor]] prefers one live exit pass and only then falls back to a modeled RPC exit.

### PEAD drift ([[concepts/pead-drift]])

A single morning window (09:35–10:35 ET) rebalances the `sys-pead-drift` portfolio as the post-earnings drift position is established into the open. The same task is *also* invoked as a hook from the earnings-alpha pipeline (see below).

### Daily stock pick legs (`sys-picks-*`)

`_run_picks_portfolio_hook` opens the 3 UP / 3 DOWN legs of every Daily Stock Picker basket at the official RTH open print (09:31–10:00 ET) and closes them at the official closing print (16:00–16:05 ET). A late basket is never filled on a stale open print — past 10:00 the session is skipped. See [[entities/daily-stock-picker]] and [[concepts/system-portfolios]] §13.

## Dry-Run Support

Every hook accepts a `dry_run` flag that is threaded through to the underlying strategy calls, allowing the whole orchestration to be simulated without executing trades. The daemon always runs them live; `python3 -m scripts.update_prices` no longer triggers hooks at all (it only refreshes quotes, marks and history).

## Earnings-Alpha Trigger

Besides the time-of-day windows, the systematic PEAD strategy is also re-evaluated whenever fresh earnings surprises land. `apps/engine/scripts/update_earnings_alpha.py` calls `run_pead_drift_task()` at the end of its snapshot upsert, so newly computed SUE scores feed directly into the drift portfolio without waiting for the next morning window.

## Metric Persistence

Strategies invoked through these hooks (Max Pain, PEAD) now fully refresh and persist portfolio accounting — they call `portfolio.calculate_reg_t_metrics(current_prices)` followed by `await portfolio.save_metrics()` before upserting to `portfolio_performance`. This replaces the earlier stub values (buying power assumed as 2× cash, SMA forced to 0, realized set equal to total equity) with real Reg T metrics and the true SMA. See [[concepts/pending-settlement-state]] and [[entities/portfolio-auditor]] for the surrounding accounting model.

## Related

- [[entities/pipeline]]
- [[entities/market-calendar]] — the session calendar the hooks window is derived from
- [[concepts/max-pain-pinning]]
- [[concepts/pead-drift]]
- [[entities/sector-trading]]
- [[entities/daily-stock-picker]]
- [[concepts/execution]]
- [[concepts/pending-settlement-state]]
