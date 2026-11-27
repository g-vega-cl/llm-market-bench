---
tags: [audit, system-portfolios, reconciliation, auto-heal, health-check]
category: entity
---

# Portfolio Auditor

The Portfolio Auditor (`apps/engine/audit/portfolio_auditor.py`) is a health-check and reconciliation island for the systematic portfolios. It detects missing executions, stale positions, and desynced metrics across the Daily SPY, weekly Sector Strategy, Daily Options Max Pain, and Daily Stock Picker portfolios, and — in auto-heal mode — reconstructs missing trades from canonical historical session prints. It is the safety net that keeps the systematic portfolios consistent with the predictions they are supposed to be trading.

## What It Audits

The auditor walks a window of trading sessions (default 5, weekdays only) and checks four families of portfolios:

- **Daily SPY portfolios** (`sys-daily-spy-*` and `sys-daily-spy-close-*`) — for every `daily_predictions` row on a given date, the matching system portfolio must contain both an entry and an exit trade (2 trades). Fewer than 2 trades is flagged as `MISSING_DAILY_SPY_TRADE`. The close-owner portfolio is always expected; the intraday owner is only expected when the model is not `jev` and the predicted magnitude is non-zero. When trades are present and entry prices are valid, the auditor additionally verifies that the recorded `portfolio_performance` equity for the date matches cumulative equity (prior closing equity + session realized PnL), flagging drift as `DESYNCED_EQUITY_DAILY_SPY`.
- **Weekly Sector portfolios** (`sys-sector-ls-consensus`, `sys-sector-mean-reversion`, `sys-sector-naive-momentum`, `sys-sector-uncorr-20d`, `sys-sector-uncorr-7d`) — these hold positions from Monday 9:35 AM ET through Friday 15:30 ET and must be flat outside that window. Holding positions when the market should be flat is flagged as `UNLIQUIDATED_WEEKLY_SECTOR_POSITION`; holding zero positions mid-week is flagged as `MISSING_WEEKLY_SECTOR_ENTRY`.
- **Daily Options Max Pain portfolio** (`sys-max-pain`, see [[entities/max-pain-pinning]]) — 0DTE index positions must be flat after the 15:50 ET exit deadline (or `session_close − 10 min` on early closes). Audited by the separate `apps/engine/audit/max_pain_auditor.py` island (colocated `apps/engine/audit/test_max_pain_auditor.py`). Any remaining open position is flagged as `UNLIQUIDATED_MAX_PAIN_POSITION` and auto-healed in `--fix` mode: first by a live exit pass (`_attempt_live_max_pain_exit`), then — if that leaves positions open — by `reconcile_unliquidated_max_pain_positions` (`apps/engine/execution/max_pain.py`), which writes a real `SELL` through the `execute_portfolio_trade` RPC at pass time at the live quote or RTH close, with no backfill or backdating.
- **Daily Stock Picker portfolios** (`sys-picks-*`, see [[entities/daily-stock-picker]] and [[concepts/system-portfolios]] §13) — `_audit_picks_portfolios` walks every `PICKS_MODEL_TRACKS` owner (`sys-picks-deepseek-flash`, `sys-picks-MiniMax-M3.1-Flash`, `sys-picks-gpt-6-luna`, `sys-picks-consensus`) and looks for `BUY`/`SHORT` trades still carrying `realized_pnl IS NULL`. A leg whose session has already closed — a prior trading day, or today once 16:05 ET has passed — is flagged as `unliquidated_picks_legs`. In `--fix` mode the auditor resolves each stale session's official close print via `fetch_intraday_prices` and calls `execute_picks_exits` (`apps/engine/execution/stock_picks_trading.py`) to liquidate the legs at that close print, recording the healed equity. Independently of open legs, `_reconcile_picks_performance` re-derives each closed session's expected equity from the trade ledger and flags/heals drift as `desynced_picks_performance`.

## Anomaly Types

| Type | Meaning |
| :--- | :--- |
| `MISSING_DAILY_SPY_TRADE` | A daily prediction exists but the system portfolio has fewer than 2 trades for that date. |
| `INVALID_ENTRY_PRICE_DAILY_SPY` | SPY entry trade price desynced from session open price ($P_{open}$) by > 0.2% (e.g. taking previous close). |
| `UNCLOSED_SHORT_DAILY_SPY` | SPY entry `SHORT` trade has `realized_pnl IS NULL` despite a matching session exit trade, risking resurrection as an active open short on read paths. |
| `DESYNCED_EQUITY_DAILY_SPY` | Performance snapshot equity drifts from cumulative equity (prior closing equity + session realized PnL) by > $2.00, auto-healed in `--fix` mode. |
| `UNLIQUIDATED_WEEKLY_SECTOR_POSITION` | A weekly sector portfolio holds open positions during a period it should be flat (Friday post-close, weekend, or Monday pre-open). |
| `MISSING_WEEKLY_SECTOR_ENTRY` | A weekly sector portfolio has zero positions mid-week, indicating a missed Monday rebalance. |
| `UNLIQUIDATED_MAX_PAIN_POSITION` | `sys-max-pain` holds a 0DTE position past the calendar-aware 15:50 ET exit deadline; auto-healed by a live exit pass first, then by a modeled RPC exit at the live quote or RTH close (no backfill). |
| `unliquidated_picks_legs` | A `sys-picks-*` portfolio still holds `BUY`/`SHORT` legs with `realized_pnl IS NULL` after that session's close print (prior trading day, or today past 16:05 ET), auto-healed by liquidating at the official close print. |
| `desynced_picks_performance` | A closed `sys-picks-*` session's `portfolio_performance.total_equity` drifts from cumulative realized PnL (`INITIAL_PORTFOLIO_CASH` + summed `realized_pnl` of that session's `SELL`/`COVER` rows) by more than $0.05, auto-healed by rewriting the row. |

## Auto-Heal Mode

When run with `--fix` (`auto_heal=True`), the auditor reconstructs missing Daily SPY executions, replaces trades with invalid entry prices using session OHLC prints stored on the prediction (`open_price`, `high_price`, `low_price`, `close_price`) and standard model slippage, and reconciles `UNCLOSED_SHORT_DAILY_SPY` anomalies by computing and mutating `realized_pnl` / `realized_pnl_pct` on the unclosed entry `SHORT` trade. When auto-healing desynced entry prices, the auditor resets portfolio cash to prior-day closing equity from `portfolio_performance`, removes stale trades and positions, and re-executes chronologically to preserve accurate compounded returns. Reconstructed trades are written with `alpaca_status = "BACKFILLED"` so they are transparently distinguishable from live Alpaca executions. See [[concepts/backfilled-trades]] and [[concepts/short-position-display]].

For `unliquidated_picks_legs`, auto-heal fetches the stale session's official close print per ticker (`fetch_intraday_prices(..., force_refresh=True)`) and delegates to `execute_picks_exits(session_date, price_map)`, which writes the `SELL`/`COVER` rows, closes the entry legs' `realized_pnl`, deletes the long `portfolio_positions` rows, and upserts the session's `portfolio_performance` snapshot. A ticker whose close price cannot be resolved is logged via `logger.exception` and left out of the price map rather than priced at a fabricated value.

### Picks Performance Reconciliation (`_reconcile_picks_performance`)

`_reconcile_picks_performance(client, portfolio, owner_id, auto_heal)` verifies that every **closed** `sys-picks-*` session's persisted equity matches the ledger, independent of whether any legs are still open:

1. Reads the portfolio's `portfolio_performance` rows (`date`, `total_equity`) and its `trades` (`signal`, `realized_pnl`, `executed_at`). No performance rows means nothing to check.
2. Collects `open_dates` — the dates of `BUY`/`SHORT` rows still carrying `realized_pnl IS NULL` — and `pnl_by_date`, the summed `realized_pnl` of `SELL`/`COVER` rows per date.
3. Walks the dates in ascending order accumulating `running = INITIAL_PORTFOLIO_CASH + Σ pnl`, and records `expected_by_date[d] = running` **only for dates with no open legs**. A session that is still open is skipped rather than compared against a partial figure.
4. Compares each performance row against its expected equity with a $0.05 tolerance. A mismatch becomes a `desynced_picks_performance` anomaly.
5. Without `auto_heal` the anomaly is flagged for review. With `auto_heal` the row is rewritten to `total_equity = cash_balance = buying_power = realized = expected` and recorded as healed with `new_equity`, logging `Reconciled <owner> <date> portfolio_performance: $old -> $new`.

The check runs both when the owner has no open legs (before the `continue`) and after any stale-leg liquidation, so a healed exit is immediately re-verified against the ledger.

### Incomplete Heals Are Flagged, Never Claimed

`execute_picks_exits` fails closed: a session is closed whole or not at all, so a missing close price for any remaining leg makes it skip that owner entirely (`skipped[owner_id] = "missing close price for <tickers>"`) and write no trades, no position deletions, and no `portfolio_performance` row. The auditor therefore inspects the exit result before recording a heal:

- If `result["portfolios"][owner_id]` is present, the anomaly is moved to `healed` with `details = "Liquidated N leg(s) at the official close print"` (N = the legs actually closed, not the size of the price map) and `new_equity` taken from that owner's result.
- If the owner is absent from the result, the anomaly stays in `flagged` with its details suffixed `auto-heal incomplete: <reason>` (the per-owner `skipped` reason, the top-level `reason`, or `no exit executed`), and a warning is logged.

This keeps the report honest: a heal that wrote nothing is never reported as healed, and the stale legs remain visible for the next run — which resumes cleanly because already-written exit rows at that session's `exit_ts` are skipped by ticker.

When no prior `portfolio_performance` history exists (the portfolio's first session), the auditor anchors the starting equity to `INITIAL_PORTFOLIO_CASH` ($10,000) rather than the portfolio's current `cash_balance`, so a dirty or already-drifted cash figure cannot compound into the healed equity.

For `DESYNCED_EQUITY_DAILY_SPY` anomalies, auto-heal rewrites the date's `portfolio_performance` row (`total_equity`, `cash_balance`, `buying_power`, `realized`) to the expected cumulative equity (prior closing equity + summed `realized_pnl` of the session's `SELL`/`COVER` trades). When the corrected date is the most recent session in the lookback window, the live `portfolios` row is updated to the same values so the portfolio's current state matches the healed history.

Weekly sector anomalies are flagged for review but not auto-healed — they require manual reconciliation.

## CLI

sh
cd apps/engine
PYTHONPATH=. ./venv/bin/python3 main.py audit-portfolios --lookback-days 5 --fix


- `--lookback-days` — number of trading sessions to scan (default 5).
- `--fix` — enable auto-heal / backfill of missing Daily SPY trades.
- `--target-date` — audit a single ISO date instead of a lookback window.

The command prints a Markdown summary table and, when running under GitHub Actions, appends it to `GITHUB_STEP_SUMMARY`.

## CI Integration

The auditor runs automatically in `.github/workflows/daily-predictor.yml` as the **"Reconcile & Auto-Heal System Portfolio Health"** step, gated on `evaluate-daily-predictions` and executed with `always()` so it runs even if earlier steps fail. It invokes `main.py audit-portfolios --lookback-days 5 --fix` with the Supabase, FMP, Massive, and Alpaca secrets injected.

## Report Shape

The audit returns a structured report with `status` (`clean`, `healed`, or `anomalies_detected`), the list of `dates_checked`, `anomalies`, `healed` records, `flagged_for_review`, and a `summary_table_markdown` rendering for terminal and CI consumption.

## Related

- [[concepts/system-portfolios]]
- [[concepts/short-position-display]]
- [[concepts/backfilled-trades]]
- [[entities/daily-market-predictor]]
- [[entities/daily-stock-picker]]
- [[entities/sector-trading]]
- [[entities/daily-postmortem]]
