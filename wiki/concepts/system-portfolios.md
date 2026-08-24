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
- **Execution Timing**: Entered at Monday Market Open and liquidated at Friday Market Close.
- **Execution Friction**: 5 bps (0.05%) slippage on entries and exits.
- **Trigger**: Integrated into the sector predictor evaluation rebalance pipeline (`apps/engine/tasks/evaluate_predictions.py`). Supports `--force` flag for manual backfilling. State hydration is robust to `NULL` margin metrics via fallback coercion in `Portfolio.initialize()`.

### 2. Daily S&P Intraday Trader (`sys-daily-spy-{model}`)
- **Signal**: Daily 9:30 AM – 4:00 PM ET S&P 500 predictions (`UP` or `DOWN`, `expected_return_pct`, `confidence`) from `daily_predictions` table.
- **Portfolios**: One dedicated system portfolio per model track (e.g. `sys-daily-spy-deepseek-v4-flash`, `sys-daily-spy-minimax-m3`).
- **Target Asset**: `SPY`
- **Position Sizing**: 100% of available cash/equity allocated per session.
- **Execution Mechanics**:
  - **Entry Price**: Open Price $\times (1 \pm 0.0005)$ (5 bps slippage).
  - **Profit Target Exit**: If intraday price reaches target return ($P_{open} \times (1 \pm |\text{expected\_return\_pct}| / 100)$), position closes immediately at the profit target price.
  - **Time-Based Exit**: If profit target is not reached during regular trading hours, position is closed at 3:30 PM ET price (or Day Close price) with 5 bps slippage.
- **Trigger**: Integrated into the daily predictor evaluation pipeline.

## Related
- [[entities/daily-market-predictor]]
- [[entities/sector-predictor-arena]]
- [[concepts/minimax-portfolio]]
