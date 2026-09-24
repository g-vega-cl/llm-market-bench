---
tags: [engine, execution, sector, strategy, portfolio]
category: entity
---

# Sector Horizon Trading Engine

Systematic 30-day and 90-day sector long/short portfolio execution engine. Manages multi-week discrete-cycle horizon portfolios that enter, hold to maturity, and exit based on consensus sector predictions.

## Portfolios

1. `sys-sector-ls-30d` — 30-Day Consensus Sector Long/Short Strategy
2. `sys-sector-ls-90d` — 90-Day Consensus Sector Long/Short Strategy

## Key Functions

- `execute_horizon_sector_entries()` — Checks for open positions; if none exist (or if a previous cycle reached maturity and was liquidated), queries the latest `sector_predictions` for the matching `timeframe` and enters via `execute_system_sector_entry`.
- `execute_horizon_sector_exits()` — Checks open trades, computes the earliest entry date, and compares against the maturity date (entry + holding_days). Only exits when today >= maturity.
- `backfill_sector_horizon_portfolios()` — Replays historical discrete cycles from inception, grouping predictions by `(prediction_date, target_date)` and rebalancing only non-overlapping cycles.

## Holding Mechanics

- **30d**: Positions held for 30 calendar days after entry. Maturity = entry_date + timedelta(days=30). No intermediate rebalancing.
- **90d**: Positions held for 90 calendar days. Maturity = entry_date + timedelta(days=90). Designed to capture quarterly macroeconomic and earnings dispersion.
- **Maturity Handling**: When a cycle reaches maturity, the engine liquidates all holdings via `execute_system_sector_exit` (with Alpaca SELL limit orders) before the next cycle entry. This happens within `execute_horizon_sector_entries()` if open positions are detected as matured.

## Idempotency & Conflict Netting

- Cross-timeframe isolation via `resolve_horizon_predictions()`: strictly filters `sector_predictions` by `timeframe == '30d'` or `timeframe == '90d'`, preventing overlap with the weekly `7d` consensus portfolio.
- Conflict cancellation identical to the consensus strategy: tickers predicted as both top and worst are dropped from both sides.

## Scheduling

- **Entry**: Monday 9:35 AM ET via `sector-trade.yml` and Monday ingestion hook, now extended to cover 30d/90d portfolios through `execute_horizon_sector_entries`.
- **Maturity Exit Check**: Daily at 3:30 PM ET via `apps/engine/scripts/update_prices.py` (Mon-Thu) and Friday exit hook. `execute_horizon_sector_exits` is called, checking each portfolio's maturity date.
- **Friday Exit Hook**: Also runs via the existing Friday afternoon sector exit flow.

## Related

- [[entities/sector-trading]]
- [[concepts/system-portfolios]]
- [[entities/sector-predictor-arena]]
