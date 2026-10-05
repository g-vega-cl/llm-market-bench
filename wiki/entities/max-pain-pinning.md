---
tags: [entity, strategy, max-pain, options, 0dte, pinning, execution, portfolio, jev]
category: entity
---

# Daily Options Max Pain Pinning Strategy

A systematic, daily intraday portfolio that captures options dealer gamma pinning on liquid index ETFs (SPY and QQQ) into their 4:00 PM session expiration. It is registered under the fixed owner ID `sys-max-pain` and pairs a quantitative 0DTE strike discount filter with a TypeSafe Jev admission gate on OpenRouter Decisions. See [[concepts/max-pain-pinning]] for the underlying options market mechanics.

## Components

- `apps/engine/tasks/max_pain_task.py`: the scheduled daily task orchestrator
- `apps/engine/execution/max_pain.py`: holding-exit rules and rebalance order computation
- `apps/engine/core/llm/max_pain_prompts.py`: Jev question contract and default qualification criteria
- `apps/web/src/features/portfolios/components/StrategyExplainer.tsx`: the `sys-max-pain` explainer card
- `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx`: portfolio dashboard subtitle mapping

## Pipeline

1. **Snapshot and quote fetch**: `fetch_max_pain_snapshot` queries 0DTE options chains via `MassiveOptionsClient` (with fallback to `options_data_cache`), deriving today's Max Pain strike via `calculate_max_pain`.
2. **Quantitative discount filter**: Evaluates the percentage distance from spot price to the Max Pain strike: `(max_pain - spot) / spot`. Candidates must trade at a 0.25% to 2.50% discount below the strike.
3. **Jev gatekeeper**: Each candidate is submitted to `evaluate_candidate_with_jev`, which POSTs a typed `choice` question (`max_pain_admission`) to OpenRouter's Decisions API (`POST /api/alpha/decisions`). A candidate is admitted only if choice is `QUALIFIED` and confidence `>= 70%`, filtering out runaway macro catalysts.
4. **Rebalance**: `compute_max_pain_rebalance_orders` frees cash from exiting holdings and allocates deployable cash equally across qualified index buys with 0.01% (1 bps) friction.
5. **Execution**: Live runs call `portfolio.execute_trade` with Alpaca mirroring and upsert daily performance to `portfolio_performance`.

## Exit Rules

`evaluate_max_pain_holding_exit` returns an exit signal when any trigger fires:

- **Target strike hit (pin achieved)**: Spot price or session high reaches within 0.05% of the Max Pain strike.
- **Session close liquidation (3:50 PM MOC)**: Mandatory exit before the 4:00 PM close to guarantee zero overnight holding.
- **Adverse stop loss**: Current price drops >1.0% below entry price (indicating gamma support breakdown).

## Sizing and Defaults

| Parameter | Default |
| :--- | :--- |
| `SYS_MAX_PAIN_OWNER_ID` | `sys-max-pain` |
| `DEFAULT_MAX_HOLDINGS` | 2 (SPY, QQQ) |
| `DEFAULT_MAX_PAIN_SLIPPAGE_BPS` | 1.0 (0.01%) |
| `DEFAULT_TARGET_PROXIMITY_PCT` | 0.05% |
| `DEFAULT_ADVERSE_STOP_PCT` | 1.0% |
| Discount Range | 0.25% to 2.50% |
| Minimum Jev confidence (`--min-confidence`) | 70.0 |

## CLI

```sh
python -m tasks.max_pain_task \
  [--dry-run] [--action evaluate|entry|exit] [--max-holdings N] [--min-confidence F]
```

`--dry-run` computes and returns the complete rebalance plan without modifying database positions or writing performance rows.

## Related

- [[concepts/max-pain-pinning]]
- [[entities/massive-options]]
- [[entities/macro-options]]
- [[concepts/jev-decisions-model]]
- [[concepts/execution]]
- [[entities/strategy-explainer]]
- [[entities/pipeline]]
