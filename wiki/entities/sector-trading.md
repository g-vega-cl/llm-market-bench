---
tags: [execution, portfolio, system, sector]
category: entity
---

# Systematic Weekly Sector Trading

Live execution engine for 5 weekly sector strategy portfolios: long/short consensus, 20-day uncorrelated momentum, 7-day uncorrelated momentum, naive momentum benchmark, and mean reversion. Enters positions Monday at market open (9:35 AM ET) and exits Friday at market close (4:05 PM ET).

## Architecture

- **Live Entry (`execute_system_sector_entry`, `execute_mechanical_sector_entry`)**: Fetches latest single-cycle predictions (`max(prediction_date)`) and correlation data, resolves sector tickers, deducts purchase cost from `cash_balance`, inserts `BUY`/`SHORT` trades into `trades` table, mirrors long `BUY` limit orders to Alpaca paper trading, and upserts active long holdings into `portfolio_positions`.
- **Live Exit (`execute_system_sector_exit`, `execute_mechanical_sector_exit`)**: Locates open entries, calculates realized PnL, credits proceeds and realized PnL back to `cash_balance`, inserts `SELL`/`COVER` trades, mirrors long `SELL` limit orders to Alpaca, cleans up `portfolio_positions`, and records `portfolio_performance` snapshots.
- **Orchestration (`run_sector_trade`)**: Central dispatcher handling `entry`, `exit`, and `status` actions. Fetches market data via `MarketDataManager`, resolves sector tickers from predictions and correlation data, and delegates to the appropriate entry/exit functions.
- **Zero Backfilling**: Retroactive rebalancing during weekend evaluations in `evaluate_predictions.py` has been removed. All portfolios execute in real time on Mondays/Fridays and mirror to Alpaca without hindsight modifications.
- **Alpaca Mirroring**: Long legs across systematic portfolios (`sys-sector-uncorr-20d`, `sys-sector-uncorr-7d`, `sys-sector-naive-momentum`, `sys-sector-mean-reversion`, and `sys-sector-ls-consensus`) mirror limit orders directly to Alpaca paper broker via `AlpacaBroker`.
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
