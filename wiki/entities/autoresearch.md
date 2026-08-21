---
tags: [entity, engine, autoresearch, prompt-evolution]
category: entity
---

# Autoresearch

Karpathy-style autonomous prompt improvement loop that runs twice weekly (Sun & Wed 6:00 PM ET). It evaluates recent daily predictions, computes a ratchet score, and mutates the system prompt to improve future performance.

## Implementation

Located in `apps/engine/tasks/daily_autoresearch.py`. The `run_daily_autoresearch_for_model` function:

1. Fetches predictions for the past 3 days for a specific model track.
2. Fetches the current active prompt for that model track (strictly by `track_id` and `status`). Falls back to baseline, then seeds a new baseline if none exist.
3. Updates parent variant metrics with the current ratchet score.
4. Compares current score against the best baseline within the same model track. If current exceeds best baseline, promotes to `baseline`.
5. Mutates the prompt using DeepSeek Flash meta-researcher.
6. Deploys a new active variant, demoting all prior `active` variants for that track to `saved`.

## Track Isolation

- Each model (`deepseek-v4-flash`, `MiniMax-M3`) has its own independent prompt lineage.
- No cross-track fallback: queries are always scoped by `track_id`.
- Baseline seeding creates a new baseline for a model if none exists.

## Related

- [[concepts/auto-research-prompt-improver]]
- [[concepts/multi-track-autoresearch]]
- [[entities/daily-market-predictor]]
- [[entities/pipeline]]
