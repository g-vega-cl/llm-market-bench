---
tags: [entity, strategy, max-pain, options, 0dte, pinning, execution, portfolio, jev]
category: entity
---

# Daily Options Max Pain Pinning Strategy

A systematic, daily intraday portfolio that captures options dealer gamma pinning on liquid index ETFs (SPY and QQQ) into their 4:00 PM session expiration. It is registered under the fixed owner ID `sys-max-pain` and pairs a quantitative 0DTE strike discount filter with a TypeSafe Jev admission gate on OpenRouter Decisions. See [[concepts/max-pain-pinning]] for the underlying options market mechanics.

## Components

- `apps/engine/tasks/max_pain_task.py`: the scheduled daily task orchestrator (`fetch_quote_snapshot`, `has_entered_today`, `fetch_max_pain_snapshot`, `run_max_pain_task`)
- `apps/engine/execution/providers/alpaca_max_pain.py`: full-chain open-interest Max Pain (see [[concepts/max-pain-data-sources]])
- `apps/engine/execution/max_pain.py`: holding-exit rules, rebalance order computation (`compute_max_pain_rebalance_orders`), and `reconcile_unliquidated_max_pain_positions` post-close auto-heal
- `apps/engine/core/llm/max_pain_prompts.py`: Jev question contract and default qualification criteria
- `apps/web/src/features/portfolios/components/StrategyExplainer.tsx`: the `sys-max-pain` explainer card
- `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx`: portfolio dashboard subtitle mapping

## Pipeline

1. **Verified chain fetch**: `fetch_max_pain_snapshot` pulls the *full* same-day chain with OCC open interest from Alpaca (`apps/engine/execution/providers/alpaca_max_pain.py`, `GET /v2/options/contracts`) and derives the strike via `calculate_max_pain`. A thin chain (< 10 strikes with OI), missing credentials, HTTP errors, or a non-0DTE nearest expiration make the task skip the ticker (`data_insufficient`) instead of trading. Every skip reason is logged at info level.
2. **Per-holding target strike**: while evaluating open positions, the task resolves each holding's `target_strike` from the freshly verified Alpaca Max Pain strike for that ticker, falling back to `cost_basis * 1.008` only when no verified strike is available. Verified snapshots are cached per ticker for the run so the candidate-evaluation stage does not re-fetch.
3. **Quote snapshot**: `fetch_quote_snapshot` queries FMP `/stable/quote` for `price`, `dayHigh`, and `dayLow` in one call (`dayHigh` is coerced to at least `price`). This supplies the session high used by the pin-achieved exit check. It degrades to zeroed values on missing API key, non-200, or network error, in which case `fetch_current_price` is used as a fallback spot.
4. **Quantitative discount filter**: Evaluates the percentage distance from spot price to the Max Pain strike: `(max_pain - spot) / spot`. Candidates must trade at a 0.25% to 2.50% discount below the strike.
5. **Jev gatekeeper**: Each candidate is submitted to `evaluate_candidate_with_jev`, which POSTs a typed `choice` question (`max_pain_admission`) to OpenRouter's Decisions API (`POST /api/alpha/decisions`). A candidate is admitted only if choice is `QUALIFIED` and confidence `>= 70%`, filtering out runaway macro catalysts.
6. **Same-day idempotency**: Before entry, `has_entered_today(portfolio_id, ticker, today_et)` checks `trades` for an existing `BUY` on the same ET date (skipped for missing or `mock-` portfolio ids). A ticker that already entered today — including one that was exited on a pin touch — is not re-entered later in the session.
7. **Rebalance**: `compute_max_pain_rebalance_orders` frees cash from exiting holdings and allocates deployable cash equally across qualified index buys with 0.01% (1 bps) friction. Sales fill at the target strike (less 1 bps) when the exit reason reports a pin achieved — `raw_price = max(current_price, target_strike)`, so a pullback from the touch does not lower the fill — and at the current/close price otherwise.
8. **Execution**: Live runs call `portfolio.execute_trade` with Alpaca mirroring and upsert daily performance to `portfolio_performance`.

## Exit Rules

`evaluate_max_pain_holding_exit` returns an exit signal when any trigger fires:

- **Target strike hit (pin achieved)**: Spot price or session high (`dayHigh` from FMP `/stable/quote`) reaches within 0.05% of today's verified Alpaca Max Pain strike. When triggered, the sale fills at the target strike (less 1 bps slippage) rather than a lower pullback price, and same-day idempotency (`has_entered_today`) prevents re-entering the same ticker later in the session.
- **Session close liquidation (3:25+ PM MOC)**: Mandatory exit window (`>= 15:25 ET` in `apps/engine/scripts/update_prices.py`, catching the 15:30 ET cron run) before the 4:00 PM close to guarantee zero overnight holding.
- **After-the-fact EOD reconciliation**: If an afternoon cron run is skipped and a position remains open after 16:00 ET (or from a prior trading day), `reconcile_unliquidated_max_pain_positions` (invoked by [[entities/portfolio-auditor]] in `--fix` mode) checks the day's RTH high against the verified Max Pain strike and backfills the `SELL` at the target strike (if touched intraday) or at the RTH close price (`alpaca_status = "BACKFILLED"`).
- **Adverse stop loss**: Current price drops >1.0% below entry price (indicating gamma support breakdown).

## Post-Close Reconciliation

`reconcile_unliquidated_max_pain_positions(portfolio_row, positions, audit_date, client, slippage_bps=1.0)` in `apps/engine/execution/max_pain.py` is the auto-heal path for leftovers:

- Resolves the day's RTH high/low/close via `fetch_intraday_prices` and the verified Alpaca Max Pain strike via `get_verified_max_pain` (falling back to `cost_basis * 1.008` when unavailable).
- Re-runs `evaluate_max_pain_holding_exit` with `is_market_close_window=True` and the session high, filling at `max(close, target_strike)` (less slippage) on a pin-achieved reason, otherwise at the RTH close.
- Inserts a `SELL` trade tagged `alpaca_status = "BACKFILLED"` (executed at 20:00 UTC), deletes the open `portfolio_positions` row, and rewrites portfolio cash, equity, realized, buying power, and excess liquidity, plus a `portfolio_performance` upsert for the audit date.

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
- [[concepts/max-pain-data-sources]]
- [[entities/macro-options]]
- [[concepts/jev-decisions-model]]
- [[concepts/execution]]
- [[entities/strategy-explainer]]
- [[entities/pipeline]]
- [[entities/portfolio-auditor]]
