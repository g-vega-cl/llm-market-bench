---
tags: [postmortem, taxonomy, evaluation, daily-predictor, autoresearch, hold]
category: concept
---

# Daily Post-Mortem Taxonomy

A **closed root-cause taxonomy** used by the [[entities/daily-postmortem]] island to classify the outcome of each intraday S&P 500 (SPY) prediction. Constraining the diagnosis to a fixed set of categories keeps the post-mortem machine-readable, comparable across days and models, and safe to feed into automated prompt evolution without free-form hallucination.

## Categories

- **`ACCURATE_CAPTURE`** — direction and magnitude hit cleanly.
- **`PRUDENT_HOLD`** — abstention (`HOLD`) on a flat / choppy / conflicting session (|open-to-close move| < 0.35%). The hold was the correct behavior; `flawed_assumption='None'` and `was_predictable=True`. Not promoted into memory.
- **`TIMID_MAGNITUDE`** — correct direction, but the target was capped too low on a large trend day; also used to classify a `HOLD` through an unambiguous trend expansion (|move| > 0.75%) as excessive caution.
- **`OVERSHOT_TARGET`** — correct direction, but the target exceeded the session's realized volatility.
- **`CATALYST_INVERSION`** — the cited catalyst occurred, but the market reacted in the opposite direction (e.g. "sell the news").
- **`INTRADAY_REVERSAL`** — the thesis worked in the first 1–2 hours, then faded or reversed in the afternoon.
- **`RANGEBOUND_CHOP`** — a flat tape with no momentum, where a direction was forced on chop.
- **`UNFORESEEN_SHOCK`** — a breaking headline after 9:30 AM drove an unpredictable move.

## HOLD Handling

Whether a `HOLD` prediction was a prudent abstention or a costly missed trend depends on the realized session move:

- |open-to-close move| < 0.35% (flat / choppy / conflicting tape) → `PRUDENT_HOLD`.
- |move| > 0.75% (unambiguous strong directional expansion) → `TIMID_MAGNITUDE` (held through a trend it should have traded).

`PRUDENT_HOLD` is treated like `ACCURATE_CAPTURE` for memory feedback: predictable, but nothing to learn, so no `AUTORESEARCH_INSIGHT`/lesson is promoted. See [[concepts/confidence-gating]] for the gating mechanics and move-aware HOLD credits that decide these outcomes upstream.

## Predictability Flag

Alongside the category, each diagnosis carries a `was_predictable` boolean. It is `True` when the outcome was foreseeable from pre-market signals, options positioning, or macro indicators, and `False` when driven by random noise inside a tight range or by post-open breaking news. Only predictable, non-`ACCURATE_CAPTURE`, non-`PRUDENT_HOLD` failures are promoted into memory and the weekly autoresearch loop.

## Why a Closed Set

- **Comparability** — categories aggregate cleanly across models and dates for the leaderboard and weekly summaries.
- **Actionability** — each category maps to a distinct corrective heuristic (e.g. `TIMID_MAGNITUDE` → widen targets on trend days; `CATALYST_INVERSION` → check cross-asset momentum before trading a catalyst).
- **Grounding** — the taxonomy forces the diagnosing model to cite evidence from the verified price tape or evening brief rather than inventing narratives.

## Related

- [[entities/daily-postmortem]] — the island that applies the taxonomy
- [[entities/daily-market-predictor]] — the predictions being classified
- [[concepts/confidence-gating]] — HOLD gating and move-aware HOLD credits
- [[concepts/magnitude-calibration]] — related magnitude-error analysis
- [[concepts/hallucination-audit]] — grounding discipline
