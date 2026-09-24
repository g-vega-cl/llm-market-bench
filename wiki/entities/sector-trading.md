---
tags: [execution, portfolio, system, sector]
category: entity
---

# Systematic Weekly Sector Trading

Live execution engine for 5 weekly sector strategy portfolios: long/short consensus, 20-day uncorrelated momentum, 7-day uncorrelated momentum, naive momentum benchmark, and mean reversion. Enters positions Monday at market open (9:35 AM ET) and exits Friday before market close (3:30 PM ET).

## Architecture

- **Live Entry (`execute_system_sector_entry`, `execute_mechanical_sector_entry`)**: Fetches latest single-cycle predictions (`max(prediction_date)`) and correlation data, resolves sector tickers, deducts purchase cost from `cash_balance`, inserts `BUY`/`SHORT` trades into `trades` table, mirrors long `BUY` limit orders to Alpaca paper trading, and upserts active long holdings into `portfolio_positions`.
- **Live Exit (`execute_system_sector_exit`, `execute_mechanical_sector_exit`)**: Locates open entries, calculates realized PnL, credits proceeds and realized PnL back to `cash_balance`, inserts `SELL`/`COVER` trades, mirrors long `SELL` limit orders to Alpaca, cleans up `portfolio_positions` after Alpaca order placement, and records `portfolio_performance` snapshots.
- **Orchestration (`run_sector_trade`)**: Central dispatcher handling `entry`, `exit`, and `status` actions. Fetches market data via `MarketDataManager`, resolves sector tickers from predictions and correlation data, and delegates to the appropriate entry/exit functions.
- **Zero Backfilling**: Retroactive rebalancing during weekend evaluations in `evaluate_predictions.py` has been removed. All portfolios execute in real time on Mondays/Fridays and mirror to Alpaca without hindsight modifications.
- **Alpaca Mirroring**: Long legs across systematic portfolios (`sys-sector-uncorr-20d`, `sys-sector-uncorr-7d`, `sys-sector-naive-momentum`, `sys-sector-mean-reversion`, and `sys-sector-ls-consensus`) mirror limit orders directly to Alpaca paper broker via `AlpacaBroker`.
- **Idempotency**: Skips re-entry if trades already exist for the same portfolio + executed_at timestamp. Skips exit if exit trades already exist for the same ticker + cycle.
- **Short Tracking**: Short positions are tracked via `trades` table (DB constraint `quantity_not_negative` prevents negative `portfolio_positions`). Open shorts are loaded separately during price updates to compute unrealized PnL.

## Strategies Executed

1. `sys-sector-ls-consensus` — Weekly Sector Long/Short Consensus Strategy (trend-following, 7d horizon)
2. `sys-sector-ls-30d` — 30-Day Sector Long/Short Consensus Strategy (monthly cycle, 30d horizon)
3. `sys-sector-ls-90d` — 90-Day Sector Long/Short Consensus Strategy (quarterly cycle, 90d horizon)
4. `sys-sector-uncorr-20d` — 20-Day Uncorrelated Sector Momentum
5. `sys-sector-uncorr-7d` — 7-Day Uncorrelated Sector Momentum
6. `sys-sector-naive-momentum` — 20-Day Unconstrained Momentum Benchmark Control
7. `sys-sector-mean-reversion` — 7-Day Sector Mean Reversion

## Scheduling

- **Monday 9:35 AM ET**: Entry triggered by `sector-trade.yml` (GitHub Actions schedule) and Monday morning ingestion hook in `main.py run_ingest`. For 30d and 90d portfolios, if an existing cycle reached maturity, it automatically liquidates and submits Alpaca SELL limit orders before rolling into the next prediction cycle with new BUY limit orders.
- **Friday 3:30 PM ET**: Exit triggered by the Friday afternoon ingestion hook in `apps/engine/main.py run_ingest` (dispatched via Cloudflare Cron Dispatcher at 3:30 PM ET), the 3:30 PM / 4:00 PM ET price updater hook in `apps/engine/scripts/update_prices.py` (`update-prices.yml`), and `sector-trade.yml` schedule as a backup (allowing 30 minutes before 4:00 PM close for Alpaca DAY limit fills). Weekly portfolios close out, and horizon portfolios are checked for maturity.
- **Daily 3:30 PM ET Horizon Maturity Check**: On all trading days (Mon-Fri) near market close, `apps/engine/scripts/update_prices.py` checks whether active 30d or 90d positions have reached their target maturity date. If matured, it executes `execute_horizon_sector_exits`, liquidates holdings, and submits Alpaca SELL limit orders.
- **Manual trigger**: `python3 main.py sector-trade --action entry|exit|status --target-date YYYY-MM-DD --dry-run`

## Related

- [[concepts/system-portfolios]] — Overview of all system portfolio strategies
- [[entities/sector-predictor-arena]] — Weekly sector ETF predictions and evaluation pipeline
- [[entities/pipeline]] — Full daily pipeline including Monday market data ingestion
- [[entities/engine]] — Python data engine
- [[entities/database]] — `trades`, `portfolio_positions`, `portfolio_performance` tables
- [[concepts/execution]] — Pre-market validation and trade settlement
