---
tags: [execution, portfolio, system, sector]
category: entity
---

# Systematic Weekly Sector Trading

Live execution engine for 5 weekly sector strategy portfolios: long/short consensus, 20-day uncorrelated momentum, 7-day uncorrelated momentum, naive momentum benchmark, and mean reversion. Enters positions Monday at market open (9:35 AM ET) and exits Friday at market close (4:05 PM ET).

## Architecture

- **Live Entry (`execute_system_sector_entry`, `execute_mechanical_sector_entry`)**: Fetches latest predictions and correlation data, resolves sector tickers, performs idempotency checks, inserts `BUY`/`SHORT` trades into `trades` table, and upserts long positions into `portfolio_positions`.
- **Live Exit (`execute_system_sector_exit`, `execute_mechanical_sector_exit`)**: Locates open entries, calculates realized PnL, inserts `SELL`/`COVER` trades, cleans up `portfolio_positions`, updates portfolio cash/equity/buying power, and writes daily `portfolio_performance` snapshots.
- **Orchestration (`run_sector_trade`)**: Central dispatcher handling `entry`, `exit`, and `status` actions. Fetches market data via `MarketDataManager`, resolves sector tickers from predictions and correlation data, and delegates to the appropriate entry/exit functions.
- **Idempotency**: Skips re-entry if trades already exist for the same portfolio + executed_at timestamp. Skips exit if exit trades already exist for the same ticker + cycle.
- **Short Tracking**: Short positions are tracked via `trades` table (DB constraint `quantity_not_negative` prevents negative `portfolio_positions`). Open shorts are loaded separately during price updates to compute unrealized PnL.

## Strategies Executed

1. `sys-sector-ls-consensus` — Weekly Sector Long/Short Consensus Strategy (trend-following)
2. `sys-sector-uncorr-20d` — 20-Day Uncorrelated Sector Momentum
3. `sys-sector-uncorr-7d` — 7-Day Uncorrelated Sector Momentum
4. `sys-sector-naive-momentum` — 20-Day Unconstrained Momentum Benchmark Control
5. `sys-sector-mean-reversion` — 7-Day Sector Mean Reversion

## Scheduling

- **Monday 9:35 AM ET**: Entry triggered by `sector-trade.yml` (GitHub Actions schedule) and Monday morning ingestion hook in `main.py run_ingest`.
- **Friday 4:05 PM ET**: Exit triggered by `sector-trade.yml` schedule.
- **Manual trigger**: `python3 main.py sector-trade --action entry|exit|status --target-date YYYY-MM-DD --dry-run`

## Related

- [[concepts/system-portfolios]] — Overview of all system portfolio strategies
- [[entities/sector-predictor-arena]] — Weekly sector ETF predictions and evaluation pipeline
- [[entities/pipeline]] — Full daily pipeline including Monday market data ingestion
- [[entities/engine]] — Python data engine
- [[entities/database]] — `trades`, `portfolio_positions`, `portfolio_performance` tables
- [[concepts/execution]] — Pre-market validation and trade settlement
