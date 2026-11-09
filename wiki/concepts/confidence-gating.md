---
tags: [confidence, gating, hold, predictor, jev, laya, thresholds]
category: concept
---

# Confidence Gating (HOLD Gate)

The confidence gate converts low-conviction directional predictions into `HOLD` signals before execution. It is applied in `apps/engine/tasks/daily_predictor.py` via `apply_confidence_hold_gate`.

## Threshold Resolution

The gate's `min_confidence` is resolved per model, not globally:

- **Curated models** (`jev_curated`, `laya_curated`) parse their own `min_confidence` from the raw prompt JSON via `parse_jev_curated_prompt_content` / `parse_laya_curated_prompt_content`. The parsed value is threaded through `_execute_model_daily_prediction` as the seventh tuple element and passed to the gate.
- **Instructor and MiniMax models** default to `HOLD_CONFIDENCE_THRESHOLD` (56.0%).
- `parse_jev_curated_prompt_content` falls back to `HOLD_CONFIDENCE_THRESHOLD` when the prompt omits `min_confidence` (previously a hardcoded 50.0).

## Gate Behavior

When a prediction's confidence falls below the resolved threshold, the gate rewrites the direction to `HOLD` and prefixes the rationale with `[HOLD - Gated from <DIR> (<conf>%)]`. The expected return is zeroed.

## No Silent Exception Swallowing

The previous implementation wrapped raw-prompt JSON parsing in `contextlib.suppress(Exception)`, silently swallowing malformed prompts. Parsing now propagates through the typed parser and the gate receives the resolved threshold explicitly. `contextlib.suppress(Exception)` is forbidden in production engine code and is enforced by `verify.sh`.

## Related

- [[concepts/jev-decisions-model]] — JEV curated prompt parsing
- [[concepts/laya-decisions-model]] — Laya curated prompt parsing
- [[concepts/conviction-points]] — conviction scoring
- [[entities/daily-market-predictor]] — daily predictor task
