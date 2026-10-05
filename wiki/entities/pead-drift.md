---
tags: [entity, strategy, pead, execution, portfolio, jev, earnings]
category: entity
---

# PEAD Drift (Post-Earnings Announcement Drift Strategy)

A systematic, non-LLM-driven portfolio that captures the multi-week institutional drift following top-decile earnings surprises. It is registered under the fixed owner ID `sys-pead-drift` and combines a deterministic quantitative pre-filter (SUE + Sloan accrual quality) with a TypeSafe Jev "System One" admission gate. See [[concepts/pead-drift]] for the underlying market phenomenon.

## Components

- `apps/engine/tasks/pead_drift_task.py` — the scheduled task orchestrator
- `apps/engine/execution/pead_drift.py` — holding-exit rules and rebalance order computation
- `apps/engine/core/llm/pead_prompts.py` — frozen Jev question contract and default criteria
- `apps/web/src/features/portfolios/components/StrategyExplainer.tsx` — the `sys-pead-drift` explainer card

## Pipeline

1. **Candidate fetch** — `fetch_pead_candidates_for_evaluation` queries `earnings_alpha_snapshots` for rows with `sue_score >= 2.0` and `days_since_earnings_report <= 5`, ordered by snapshot date then SUE descending, deduplicated by ticker. See [[entities/earnings-alpha]].
2. **Jev gatekeeper** — each candidate is submitted to `evaluate_candidate_with_jev`, which POSTs a typed `choice` question (`pead_admission`) to OpenRouter's Decisions API (`POST /api/alpha/decisions`). A candidate is admitted only if the choice is `QUALIFIED` **and** confidence `>= 70%`. See [[concepts/jev-decisions-model]].
3. **Rebalance** — `compute_pead_rebalance_orders` sells positions flagged for exit, keeps the rest, and fills open slots with admitted candidates ranked by SUE score.
4. **Execution** — live runs (non `--dry-run`) call `portfolio.execute_trade` for each sale and buy with Alpaca mirroring enabled, then upsert daily rows into `portfolio_performance`.

## Exit Rules

`evaluate_holding_exit` returns an exit signal when either trigger fires:

- **Horizon expiration** — holding days exceed the max (default **30 trading days**, the empirical drift window).
- **Trailing stop** — drawdown from peak price exceeds the trailing threshold (default **5%**).

The peak price is recalculated on each evaluation (`max(peak_price, current_price)`) to maintain a true trailing reference.

## Sizing & Defaults

| Parameter | Default |
|-----------|---------|
| `SYS_PEAD_DRIFT_OWNER_ID` | `sys-pead-drift` |
| `DEFAULT_MAX_HOLDINGS` | 12 |
| `DEFAULT_MAX_HOLDING_DAYS` | 30 |
| `DEFAULT_SLIPPAGE_BPS` | 5.0 (0.05%) |
| `DEFAULT_TRAILING_STOP_PCT` | 5.0 |
| Minimum SUE (`--min-sue`) | 2.0 |
| Minimum Jev confidence (`--min-confidence`) | 70.0 |

Deployable cash (`available_cash + freed_cash`) is split equally across selected buys; slippage is applied by selling at `price * (1 - slip)` and buying at `price * (1 + slip)`. Tickers already held are excluded from buy candidates.

## CLI

```sh
python -m tasks.pead_drift_task \
  [--dry-run] [--max-holdings N] [--holding-days N] [--min-sue F] [--min-confidence F]
```

`--dry-run` computes and returns the full plan without executing trades or writing performance rows.

## Related

- [[concepts/pead-drift]] — the academic drift phenomenon this portfolio exploits
- [[entities/earnings-alpha]] — the `earnings_alpha_snapshots` data source
- [[concepts/jev-decisions-model]] — the typed decision API used as the admission gate
- [[concepts/execution]] — the shared trade execution layer
- [[entities/strategy-explainer]] — the web explainer component
- [[entities/pipeline]]
