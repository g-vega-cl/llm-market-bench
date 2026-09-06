---
tags: [entity, engine, autoresearch, prompt-evolution]
category: entity
---

# Autoresearch

Karpathy-style autonomous prompt improvement loop that runs weekly (Sunday 6:00 PM ET / 10:00 PM UTC). It evaluates recent daily predictions over the prior 7 days, computes a ratchet score, and mutates the system prompt to improve future performance.

## Implementation

Located in `apps/engine/tasks/daily_autoresearch.py`. The `run_daily_autoresearch_for_model` function:

1. Fetches predictions for the past 7 days for a specific model track (evaluating all available trading sessions).
2. Fetches context-enriched market postmortems via `fetch_autoresearch_context` across 14 days, querying `newsletter_snapshots`, `memories` (market events, post-mortems, resolutions), and `concept_metrics` (thematic velocity).
3. Fetches the current active prompt for that model track (strictly by `track_id` and `status`). Falls back to baseline, then seeds a new baseline if none exist.
4. Updates parent variant metrics with the current ratchet score.
5. Compares current score against the best baseline within the same model track. If current exceeds best baseline, promotes to `baseline`.
6. Mutates the prompt using DeepSeek Flash meta-researcher, feeding it the day-by-day catalyst context and active thematic playbooks.
7. Deploys a new active variant, demoting all prior `active` variants for that track to `saved`.

## Track Isolation & Agency-Driven Tooling

- Each model (`deepseek-v4-flash`, `MiniMax-M3`) has its own independent prompt lineage.
- No cross-track fallback: queries are always scoped by `track_id`.
- Baseline seeding creates a new baseline for a model if none exists.
- **Track-Specific Tooling**: For `track_claude` (the sole track executing skeptical verification), `researcher.py` provides the optional `inspect_verifier_rules_and_rejections` tool inside `run_tool_loop`. The meta-researcher autonomously pulls the verifier SOP rules and rejection logs on demand rather than having data forcibly pre-injected into prompts (see [[concepts/verifier-bypass]]).

## Related

- [[concepts/auto-research-prompt-improver]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/verifier-bypass]]
- [[entities/daily-market-predictor]]
- [[entities/pipeline]]
