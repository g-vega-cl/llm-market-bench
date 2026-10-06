---
tags: [audit, system-portfolios, reconciliation, auto-heal, health-check]
category: entity
---

# Portfolio Auditor

The Portfolio Auditor (`apps/engine/audit/portfolio_auditor.py`) is a health-check and reconciliation island for the systematic portfolios. It detects missing executions, stale positions, and desynced metrics across the Daily SPY and weekly Sector Strategy portfolios, and — in auto-heal mode — reconstructs missing trades from canonical historical session prints. It is the safety net that keeps the systematic portfolios consistent with the predictions they are supposed to be trading.

## What It Audits

The auditor walks a window of trading sessions (default 5, weekdays only) and checks two families of portfolios:

- **Daily SPY portfolios** (`sys-daily-spy-*` and `sys-daily-spy-close-*`) — for every `daily_predictions` row on a given date, the matching system portfolio must contain both an entry and an exit trade (2 trades). Fewer than 2 trades is flagged as `MISSING_DAILY_SPY_TRADE`. The close-owner portfolio is always expected; the intraday owner is only expected when the model is not `jev` and the predicted magnitude is non-zero.
- **Weekly Sector portfolios** (`sys-sector-ls-consensus`, `sys-sector-mean-reversion`, `sys-sector-naive-momentum`, `sys-sector-uncorr-20d`, `sys-sector-uncorr-7d`) — these hold positions from Monday 9:35 AM ET through Friday 15:30 ET and must be flat outside that window. Holding positions when the market should be flat is flagged as `UNLIQUIDATED_WEEKLY_SECTOR_POSITION`; holding zero positions mid-week is flagged as `MISSING_WEEKLY_SECTOR_ENTRY`.

## Anomaly Types

| Type | Meaning |
| :--- | :--- |
| `MISSING_DAILY_SPY_TRADE` | A daily prediction exists but the system portfolio has fewer than 2 trades for that date. |
| `INVALID_ENTRY_PRICE_DAILY_SPY` | SPY entry trade price desynced from session open price ($P_{open}$) by > 0.2% (e.g. taking previous close). |
| `UNCLOSED_SHORT_DAILY_SPY` | SPY entry `SHORT` trade has `realized_pnl IS NULL` despite a matching session exit trade, risking resurrection as an active open short on read paths. |
| `UNLIQUIDATED_WEEKLY_SECTOR_POSITION` | A weekly sector portfolio holds open positions during a period it should be flat (Friday post-close, weekend, or Monday pre-open). |
| `MISSING_WEEKLY_SECTOR_ENTRY` | A weekly sector portfolio has zero positions mid-week, indicating a missed Monday rebalance. |

## Auto-Heal Mode

When run with `--fix` (`auto_heal=True`), the auditor reconstructs missing Daily SPY executions, replaces trades with invalid entry prices using session OHLC prints stored on the prediction (`open_price`, `high_price`, `low_price`, `close_price`) and standard model slippage, and reconciles `UNCLOSED_SHORT_DAILY_SPY` anomalies by computing and mutating `realized_pnl` / `realized_pnl_pct` on the unclosed entry `SHORT` trade. When auto-healing desynced entry prices, the auditor resets portfolio cash to prior-day closing equity from `portfolio_performance`, removes stale trades and positions, and re-executes chronologically to preserve accurate compounded returns. Reconstructed trades are written with `alpaca_status = "BACKFILLED"` so they are transparently distinguishable from live Alpaca executions. See [[concepts/backfilled-trades]] and [[concepts/short-position-display]].

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
- [[entities/sector-trading]]
- [[entities/daily-postmortem]]
