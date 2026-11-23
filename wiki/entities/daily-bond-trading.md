---
tags: [entity, engine, execution, bond, tlt, trading]
category: entity
---

# Daily Bond Trading (TLT)

`apps/engine/execution/daily_bond_trading.py` executes the systematic **close-exit** strategy for **TLT** (iShares 20+ Year Treasury Bond ETF). It is the fixed-income parallel to the SPY daily trading module, holding a duration position from the 09:30 ET open until session close rather than targeting an intraday profit limit.

## Strategy Mechanics

- **Pre-market MOO entry** (`execute_daily_bond_moo_entries`): reads all TLT predictions for the target date from `daily_predictions`. Sizing uses the session open price, falling back to a live pre-market quote. `UP` predictions place a `BUY` (long) trade; `DOWN` predictions place a `SHORT` trade. An idempotency check skips re-entry when a trade already exists for the owner on the target date.
- **Session close exit** (`execute_daily_bond_close_exits` → `execute_system_daily_bond_close_trade`): computes the open-to-close execution against the TLT close price, logging an entry trade at 09:30 ET and an exit trade at 16:00 ET carrying realized PnL. For `DOWN` predictions the realized PnL is booked on the entry leg to model the short leg correctly.

The shared helper `compute_daily_trade_execution` performs the execution math with `exit_on_target=False`, and `get_or_create_system_portfolio` provisions one system portfolio per model. On close the portfolio cash, equity, realized, buying power, and a `portfolio_performance` row are updated with realized PnL.

## DST-Aware Session Timestamps

`_et_session_stamp(target_date, hour, minute)` converts an Eastern-Time session time on the target date into a UTC ISO timestamp via `ZoneInfo("America/New_York")` and `astimezone(UTC)`. The entry leg is stamped at 09:30 ET and the exit leg at 16:00 ET, so the stored `executed_at` values track the actual US session across both EDT and EST:

| Session time (ET) | EDT (UTC-4) | EST (UTC-5) |
| :--- | :--- | :--- |
| 09:30 entry | `13:30:00Z` | `14:30:00Z` |
| 16:00 exit | `20:00:00Z` | `21:00:00Z` |

The previous hardcoded `T13:30:00Z` / `T20:00:00Z` literals were EDT-only and an hour early once the US switched to EST.

## Portfolios & Owner IDs

Each model gets its own systematic portfolio keyed by the owner prefix `SYS_DAILY_TLT_CLOSE_OWNER_PREFIX = "sys-daily-tlt-close-"`, e.g. `sys-daily-tlt-close-gpt-6-luna`, `sys-daily-tlt-close-deepseek-flash`, `sys-daily-tlt-close-jev`. Entries allocate 100% of available portfolio cash.

## Slippage

`DEFAULT_BOND_CLOSE_SLIPPAGE_BPS = 2.0` — a tight 0.02% friction reflecting institutional-grade TLT liquidity.

## CLI & Scheduling

`main.py daily-trade --ticker TLT --action entry|exit|open|close` routes to the bond functions via `apps/engine/cli/trading.py`. `--ticker ALL` fans out to both SPY and TLT legs. The workflow `.github/workflows/daily-predictor.yml` invokes `daily-predictor --ticker TLT` and the TLT trade legs. Bottom-up evaluation (`tasks/evaluate_daily_predictions.py`) and audit reconciliation ([[entities/portfolio-auditor]]) route TLT predictions to `execute_system_daily_bond_close_trade`.

## Related

- [[entities/bond-predictor]] — the producer of TLT predictions
- [[concepts/system-portfolios]]
- [[concepts/daily-tlt-live-trading]]
- [[entities/portfolio-auditor]]
