---
tags: [concept, daily-predictor, jev, risk-management, confidence-gating, hold]
category: concept
---

# Confidence Gating, HOLD Execution, & The Participation Hurdle

Confidence gating is the architectural mechanism where daily prediction models expressing confidence below a defined threshold (`< 56.0%`) are automatically gated to `HOLD` execution rather than entering high-friction market trades.

## Historical Evolution & The Selectivity Trap

In early iterations of local autoresearch, an ad-hoc `min_confidence` lever was tested that set predictions to `NO_TRADE`. However, this early attempt suffered from two fatal flaws:
1. **The Selectivity Trap / Cowardice**: Without a participation constraint, ratchets evolved toward excessive abstention on choppy sessions, artificially inflating accuracy while refusing to trade.
2. **Schema Invariant Conflict**: The database check constraint only allowed `'UP'` and `'DOWN'`, causing unhandled database exceptions.

Consequently, `NO_TRADE` was deprecated in favor of binary direction.

## The Modern HOLD Architecture (November 2026)

The modern architecture reconciles selectivity with high trade participation through five strict invariants:

### 1. Database Schema Support
Migration `20261109000000_allow_hold_in_daily_predictions.sql` updates the check constraint:
```sql
CHECK (predicted_direction IN ('UP', 'DOWN', 'HOLD'))
```
When gated to `HOLD`:
- `predicted_direction` becomes `'HOLD'`.
- `expected_return_pct` is set to `0.0`.
- `rationale` is prepended with `"[HOLD - Gated from {DIR} ({CONF:.1f}%)]: "`.
- Directional outcome `is_correct` and `intraday_hit` evaluate to `NULL`.
- `conviction_score` evaluates to `0.0` CP (neutral).

### 2. Standard Gating Threshold
Across daily predictor tracks (`apps/engine/tasks/daily_predictor.py` and `apps/engine/tasks/bond_predictor.py`), `apply_confidence_hold_gate` applies:
- `HOLD_CONFIDENCE_THRESHOLD = 56.0%`.
- Calls stating $\ge 56.0\%$ confidence trade their chosen direction (`UP` or `DOWN`).
- Calls stating $< 56.0\%$ confidence are gated to `HOLD`.
- Jev curated tracks may define custom thresholds (e.g. `min_confidence = 0.0` for forced binary direction).

### 3. Move-Aware HOLD Credits
During weekly autoresearch evaluation (`apps/engine/tasks/daily_autoresearch.py`), a `HOLD` session is scored based on the session's realized open-to-close move:
- **Flat / Choppy Sessions** ($|\text{move}| < 0.25\%$): HOLD earns **$+52.0$ pts** credit (rewarding the model for preserving capital and avoiding bid-ask spread and slippage).
- **Normal Sessions** ($0.25\% \le |\text{move}| \le 0.75\%$): HOLD earns **$+45.0$ pts** credit (sub-coin-flip neutral credit).
- **Missed Trend Sessions** ($|\text{move}| > 0.75\%$): HOLD earns only **$+35.0$ pts** credit (penalizing excessive caution and leaving big directional trend days on the table).

### 4. The 75% Participation Hurdle
To permanently eliminate cowardice, weekly autoresearch enforces `TARGET_MIN_TRADE_RATE = 0.75`:
$$\text{participation\_factor} = \min\left(1.0, \frac{\text{trade\_rate}}{0.75}\right)$$
$$\text{final\_score} = \text{base\_score} \times \text{participation\_factor}$$
Models must trade at least 75% of available sessions (at most 1 HOLD per 4–5 sessions). An overly timid prompt that holds 50% of the time suffers a $0.50 / 0.75 = 0.67\times$ haircut on its total ratchet score.

### 5. Execution Pipeline Safety
Systematic daily trading engines (`apps/engine/execution/daily_trading.py`, `daily_live_trading.py`, `daily_bond_trading.py`) skip order entry when `predicted_direction == 'HOLD'`, holding 100% cash and logging flat equity snapshots in `portfolio_performance`.

## Related

- [[entities/daily-market-predictor]] — production prediction runner
- [[entities/daily-score-breakdown]] — web UI component visualizing ratchet score, pillars, and participation factor
- [[concepts/conviction-points]] — logarithmic confidence scoring
- [[concepts/daily-postmortem-taxonomy]] — classification of `PRUDENT_HOLD` vs `TIMID_MAGNITUDE`
