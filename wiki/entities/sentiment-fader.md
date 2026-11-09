---
tags: [entity, strategy, sentiment, options, put-call-ratio, contrarian, execution, portfolio]
category: entity
---

# Contrarian Options Sentiment Fader Strategy

A systematic, rule-based portfolio that exploits retail crowd sentiment exhaustion in the options market across liquid US index ETFs (SPY and QQQ). Registered under the fixed owner ID `sys-sentiment-fader`, the strategy fades extreme options Put/Call volume panics to capture mean-reverting oversold bounces. See [[concepts/options-sentiment-fading]] for the theoretical microstructure and empirical mechanics.

## Components

- `apps/engine/execution/sentiment_fader.py`: Core signal evaluation (`evaluate_sentiment_signal`), exit rules (`evaluate_sentiment_holding_exit`), and order calculation (`compute_sentiment_fader_rebalance_orders`).
- `apps/engine/tasks/sentiment_fader_task.py`: Scheduled daily task orchestrator (`fetch_sentiment_snapshot`, `run_sentiment_fader_task`).
- `apps/engine/scripts/update_prices.py`: Clock-driven systematic hook executing intraday during regular trading hours (see [[concepts/systematic-strategy-hooks]]).
- `apps/web/src/features/portfolios/components/StrategyExplainer.tsx`: Explainer card for `sys-sentiment-fader`.
- `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx`: Dashboard subtitle mapping.

## Pipeline & Signal Generation

1. **Options Sentiment Snapshot**: `fetch_sentiment_snapshot` calls `MassiveOptionsClient.get_options_snapshot` and calculates derivatives positioning via `calculate_options_sentiment`, pulling Put/Call volume ratio (`pv_ratio`), open interest ratio (`poi_ratio`), ATM implied volatility, and 25-delta volatility skew.
2. **Panic Entry Gate**: When the intraday Put/Call volume ratio reaches $\ge 1.30$ (95th percentile crowd panic), the strategy flags extreme put capitulation and triggers an equal-weighted long entry across qualified index proxies (SPY, QQQ).
3. **Rebalancing & Execution**: Cash is distributed equally across active buy candidates with a 1 bps (0.01%) slippage deduction. Trades execute live via `portfolio.execute_trade` and mirror to Alpaca paper broker without retroactive backfilling.

## Exit Discipline

Positions are managed dynamically with strict downside and time-horizon risk controls:

- **Euphoria Exit (Take Profit)**: When options volume flips into extreme call complacency (`pv_ratio <= 0.60`), open long legs are systematically liquidated to lock in mean-reversion gains.
- **Adverse Stop Loss**: A 1.5% drop below entry price immediately triggers liquidation to protect capital against severe macro trend breakdowns.
- **Maximum Holding Horizon**: All positions have a hard 3-day holding ceiling, ensuring capital does not stay locked in dead money if an oversold bounce fails to develop promptly.

## Sizing and Defaults

| Parameter | Default |
| :--- | :--- |
| `SYS_SENTIMENT_FADER_OWNER_ID` | `sys-sentiment-fader` |
| Universe | `SPY`, `QQQ` |
| `DEFAULT_PANIC_THRESHOLD_PC` | 1.30 (Put/Call Volume Ratio $\ge 1.30$) |
| `DEFAULT_EUPHORIA_THRESHOLD_PC` | 0.60 (Put/Call Volume Ratio $\le 0.60$) |
| `DEFAULT_FADER_STOP_LOSS_PCT` | 1.5% |
| `DEFAULT_FADER_MAX_HOLDING_DAYS` | 3 days |
| `DEFAULT_FADER_SLIPPAGE_BPS` | 1.0 (0.01%) |

## Related

- [[concepts/options-sentiment-fading]]
- [[entities/massive-options]]
- [[entities/max-pain-pinning]]
- [[concepts/systematic-strategy-hooks]]
- [[concepts/system-portfolios]]
- [[entities/portfolio-auditor]]
