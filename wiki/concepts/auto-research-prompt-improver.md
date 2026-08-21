---
tags: [autoresearch, prompt-evolution, meta-researcher, ratchet]
category: concept
---

# Auto-Research Prompt Improver

Weekly autonomous prompt iteration via a meta-researcher LLM (DeepSeek Flash). The system evaluates recent prediction performance, computes a multi-factor ratchet score, and mutates the trading prompt to improve future predictions.

## Pipeline (Twice-Weekly: Sun & Wed 6:00 PM ET)

1. **Fetch predictions** for the past 3 days for a specific model track.
2. **Fetch current active prompt** for that model track (strictly scoped by `track_id`). If none exists, fall back to the model's baseline, then seed a new baseline if needed.
3. **Update parent variant metrics** with the current ratchet score.
4. **Ratchet comparison**: Compare current score against the best baseline score within the same model track. If the current score exceeds the best baseline, promote it to `baseline` status.
5. **Mutate prompt** using DeepSeek Flash meta-researcher, generating a new variant.
6. **Deploy new active variant**: Insert a new `active` record for the model track, demoting all prior `active` variants for that track to `saved`.

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
