---
tags: [autoresearch, prompt-evolution, meta-researcher, ratchet]
category: concept
---

# Auto-Research Prompt Improver

Weekly autonomous prompt iteration via a meta-researcher LLM (DeepSeek Flash). The system evaluates recent prediction performance, computes a multi-factor ratchet score, and mutates the trading prompt to improve future predictions.

## Pipeline (Weekly: Sunday 6:00 PM ET / 10:00 PM UTC)

1. **Fetch predictions** for the prior 7 days for a specific model track (evaluating all available trading sessions).
2. **Fetch context-enriched postmortems**: Queries `newsletter_snapshots`, `memories` (market events, post-mortems, resolutions), and `concept_metrics` (thematic velocity & mention counts) across the prior 14 days via `fetch_autoresearch_context`.
3. **Fetch current active prompt** for that model track (strictly scoped by `track_id`). If none exists, fall back to the model's baseline, then seed a new baseline if needed.
4. **Update parent variant metrics** with the current ratchet score.
5. **Ratchet comparison**: Compare current score against the best baseline score within the same model track. If the current score exceeds the best baseline, promote it to `baseline` status; if lower, revert to the best baseline prompt.
6. **Mutate prompt** using DeepSeek Flash meta-researcher, feeding it the enriched postmortem with day-by-day catalyst context, timid vs overshooting diagnosis, and active thematic playbooks.
7. **Deploy new active variant**: Insert a new `active` record for the model track, demoting all prior `active` variants for that track to `saved`.

## Context-Enriched Postmortems & Thematic Learning

Rather than evaluating raw numerical predictions in isolation, the meta-researcher receives an event-enriched postmortem table:
- **Daily Catalyst Alignment**: Cross-references prediction dates with ingested newsletters and market events to identify why magnitude was timid or overshooting on high-impact catalyst days.
- **Thematic Playbooks**: Injects top active narrative clusters from `concept_metrics` (with velocity scores) to allow the meta-researcher to discover cause-and-effect market dynamics autonomously.

## Ratchet Score Formula

$$\text{Ratchet Score} = (0.55 \times \text{close\_accuracy\_pct}) + (0.35 \times \text{intraday\_hit\_pct}) + (0.10 \times \text{magnitude\_capture\_pct}) - (\text{mean\_brier} \times 50.0)$$

## Key Design Decisions

- **Track-scoped baselines**: Baselines are per-model, not global. Each model track has its own `baseline` variant.
- **No cross-track fallback**: The system never falls back to another model's active prompt or baseline.
- **Single active variant**: Only one `active` variant per model track at any time.

## Related

- [[entities/autoresearch]]
- [[concepts/multi-track-autoresearch]]
- [[entities/daily-market-predictor]]
- [[concepts/brier-score]]
- [[concepts/magnitude-calibration]]
