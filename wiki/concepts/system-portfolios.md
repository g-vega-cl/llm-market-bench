---
tags: [portfolio, system, mechanical, intraday, sector, trading]
category: concept
---

# System Portfolios (Mechanical Strategies)

System portfolios are automated, rule-based investment and trading strategies that execute systematically based on predictive signals produced by LLM pipelines without requiring ad-hoc LLM order generation.

## Implemented Strategies

### 1. Weekly Sector Long/Short Strategy (`sys-sector-ls-consensus`)
- **Inception / Start Date**: `2026-08-17` (`SYS_SECTOR_START_DATE`). Prior historical prediction windows are evaluated for scores and calibration but skipped for portfolio trade rebalancing.
- **Signal**: 7-day predictions from `sector_predictions` table generated weekly by multi-model sector predictors.
- **Universe**: Major US Sector ETFs (`XLE`, `XLF`, `XLK`, `XLI`, `XLP`, `XLY`, `XLU`, `XLV`, `XLB`, `XLC`, `XBI`, `XOP`).
- **Position Sizing & Rebalancing**:
  - Aggregates unique predicted best sectors (Long Bucket) and unique worst sectors (Short Bucket).
  - **Conflict Netting**: If any sector ETF appears in both the predicted best and predicted worst sets, it is dropped from both sides to eliminate contradictory exposures.
  - 50% of available equity is allocated equally across clean Long sectors.
  - 50% of available equity is allocated equally across clean Short sectors.
- **Execution Timing**: Entered at Monday Market Open (9:35 AM ET) and liquidated at Friday Market Close (4:05 PM ET).
- **Execution Friction**: 5 bps (0.05%) slippage on entries and exits.
- **Trigger**: Executed live via `apps/engine/execution/sector_trading.py` triggered by `.github/workflows/sector-trade.yml` and the Monday morning ingestion hook. Also reconciled retrospectively in `apps/engine/tasks/evaluate_predictions.py`. Supports `--force` flag for manual backfilling. State hydration is robust to `NULL` margin metrics via fallback coercion in `Portfolio.initialize()`.

### 2. Daily S&P Intraday Trader (`sys-daily-spy-{model}`)
- **Signal**: Daily 9:30 AM – 4:00 PM ET S&P 500 predictions (`UP` or `DOWN`, `expected_return_pct`, `confidence`) from `daily_predictions` table.
- **Portfolios**: One dedicated system portfolio per model track (e.g. `sys-daily-spy-deepseek-v4-flash`, `sys-daily-spy-minimax-m3`).
- **Target Asset**: `SPY`
- **Position Sizing**: 100% of available cash/equity allocated per session.
- **Execution Mechanics**:
  - **Entry Price**: Open Price $\times (1 \pm 0.0005)$ (5 bps slippage).
  - **Profit Target Exit**: If intraday price reaches target return ($P_{open} \times (1 \pm |\text{expected\_return\_pct}| / 100)$), position closes immediately at the profit target price.
  - **Time-Based Exit**: If profit target is not reached during regular trading hours, position is closed at 3:30 PM ET price (or Day Close price) with 5 bps slippage.
- **Idempotency Guardrails**: Re-evaluation runs (`--force`) cleanly remove previous session trades and revert prior realized PnL before executing and recording the updated trade, guaranteeing zero double-buy or duplicate-trade compounding.
- **Trigger**: Integrated into the daily predictor evaluation pipeline (`apps/engine/tasks/evaluate_daily_predictions.py`).

### Idempotency & Timeframe Guardrails
- **Strict 7-Day Window Scoping**: The sector predictor produces predictions across 4 horizons (`7d`, `30d`, `60d`, `90d`). Weekly system portfolios (`sys-sector-ls-consensus` and the 4 mechanical sector benchmarks) strictly filter on `timeframe == '7d'`, preventing longer-horizon monthly or quarterly prediction evaluations from falsely triggering weekly portfolio rebalances.
- **Idempotent Rebalancing**: If `evaluate_predictions.py` or mechanical rebalances are executed with `--force`, any existing trades matching the window boundaries (`week_start_date` and `week_end_date`) are purged and their net PnL is subtracted before re-allocating, ensuring exact idempotency.

### 3. 20-Day Uncorrelated Sector Momentum (`sys-sector-uncorr-20d`)
- **Signal**: Rolling 90-day correlation matrix + trailing 20-day (~1 month) sector returns from `correlation_data`.
- **Selection Rule**: Identifies all sector ETF pairs with Pearson $|\rho| < 0.30$, selecting the pair with the highest average trailing return.
- **Allocation**: 50% Asset A, 50% Asset B.
- **Trigger**: Executed live via `apps/engine/execution/sector_trading.py` (Monday 9:35 AM ET entry, Friday 4:05 PM ET exit) triggered by `.github/workflows/sector-trade.yml` and the Monday ingestion hook. Reconciled retrospectively via `apps/engine/tasks/evaluate_predictions.py`.

### 4. 7-Day Uncorrelated Sector Momentum (`sys-sector-uncorr-7d`)
- **Signal**: Rolling 90-day correlation matrix + trailing 7-day sector returns from Sunday `correlation_data` snapshot.
- **Selection Rule**: Top uncorrelated pair ($|\rho| < 0.30$) by trailing 7-day return. Mirrors the *Uncorrelated Pairs with Positive Momentum* table.
- **Allocation**: 50% Asset A, 50% Asset B.
- **Trigger**: Executed live via `apps/engine/execution/sector_trading.py` (Monday 9:35 AM ET entry, Friday 4:05 PM ET exit) triggered by `.github/workflows/sector-trade.yml` and the Monday ingestion hook. Reconciled retrospectively via `apps/engine/tasks/evaluate_predictions.py`.

### 5. 20-Day Unconstrained Momentum Benchmark Control (`sys-sector-naive-momentum`)
- **Signal**: Trailing 20-day sector returns from `correlation_data` (unconstrained by correlation).
- **Selection Rule**: Top 2 highest-returning sector ETFs. Allows high-beta concentration (e.g. XLK + SMH).
- **Role**: Serves as the quantitative control group to benchmark the drawdown reduction provided by the $|\rho| < 0.30$ filter.
- **Allocation**: 50% Asset A, 50% Asset B.
- **Trigger**: Executed live via `apps/engine/execution/sector_trading.py` (Monday 9:35 AM ET entry, Friday 4:05 PM ET exit) triggered by `.github/workflows/sector-trade.yml` and the Monday ingestion hook. Reconciled retrospectively via `apps/engine/tasks/evaluate_predictions.py`.

### 6. 7-Day Sector Mean Reversion (`sys-sector-mean-reversion`)
- **Signal**: Trailing 7-day sector returns from `correlation_data`.
- **Selection Rule**: Bottom 2 worst-performing sector ETFs (oversold bounce).
- **Empirical Backtest**: +47.24% 1-year return, 1.87 Sharpe, -8.97% max drawdown, exploiting the weekly overreaction reversal anomaly.
- **Allocation**: 50% Asset A, 50% Asset B.
- **Trigger**: Executed live via `apps/engine/execution/sector_trading.py` (Monday 9:35 AM ET entry, Friday 4:05 PM ET exit) triggered by `.github/workflows/sector-trade.yml` and the Monday ingestion hook. Reconciled retrospectively via `apps/engine/tasks/evaluate_predictions.py`.

### 7. Frontier Technology Supercycle Strategy (`sys-frontier-tech`)
- **Signal**: Monthly autonomous discovery of pre-explosion gestation themes scored against a 5-point supercycle rubric.
- **Selection Rule**: Small-cap pure-play equities on major US exchanges with $\ge \$100\text{M}$ market cap, $\ge \$1\text{M}$ daily volume, $\ge 18$ months cash runway, and price $\le 150\%$ of 200-day moving average.
- **Allocation**: Venture power-law sizing (2% to 4% per stock) across 5 to 8 themes with multi-year retention and fundamental thesis death exits.
- **Trigger**: Rebalanced monthly via `apps/engine/tasks/frontier_tech_task.py`. Detailed documentation in [[entities/frontier-tech-portfolio]].

### 8. Daily S&P Close Trader (`sys-daily-spy-close-{model}`)
- **Signal**: Daily 9:30 AM – 4:00 PM ET S&P 500 predictions (`UP` or `DOWN`) from `daily_predictions` table.
- **Portfolios**: Dedicated system portfolio per model track (e.g. `sys-daily-spy-close-deepseek-v4-flash`, `sys-daily-spy-close-MiniMax-M3`).
- **Target Asset**: `SPY`
- **Position Sizing**: 100% of available cash/equity allocated per session.
- **Execution Mechanics**:
  - **Entry Price**: Open Price $\times (1 \pm 0.0002)$ (2 bps / 0.02% slippage reflecting SPY liquidity).
  - **Target Hits Ignored**: Holds throughout the regular session without exiting on midday profit target touches.
  - **Session Close Exit**: Position is closed at 3:50 PM ET market close price with 2 bps slippage.
- **Idempotency Guardrails**: Re-evaluation runs (`--force`) clean up previous session trades and revert prior realized PnL before re-allocating.
- **Trigger**: Executed alongside target-exit portfolios in `apps/engine/tasks/evaluate_daily_predictions.py`. Backfilled historically via `apps/engine/tasks/backfill_daily_close_portfolios.py`.

## Related
- [[entities/frontier-tech-portfolio]]
- [[entities/daily-market-predictor]]
- [[entities/sector-predictor-arena]]
- [[concepts/minimax-portfolio]]
- [[entities/strategy-explainer]]
