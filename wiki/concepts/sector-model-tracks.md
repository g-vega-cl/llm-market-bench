---
tags: [sector-predictor, autoresearch, multi-model, tracks, ratchet, prompt-evolution]
category: concept
---

# Sector Model Tracks

The Sector Predictor's prompt auto-research is not a single global loop — it runs an **independent Karpathy-style prompt evolution loop per LLM model**. Each model (DeepSeek Flash, MiniMax-M3, Gemini 3.5, OpenAI GPT-5.6) maintains its own ratchet baseline, active prompt variant, lineage history, and math audit. This isolation prevents a strong model's prompt mutations from being evaluated against another model's predictions, and lets each model's strategy evolve on its own trajectory.

## Track Definition

Tracks are defined in `apps/web/src/features/ai-predictions/lib/sector-tracks.ts` as `SECTOR_MODEL_TRACKS`, an ordered list of `SectorTrackConfig` objects. Each config carries:

- `id` — one of `all`, `deepseek`, `minimax`, `gemini`, `openai`, `legacy`
- `label` / `shortLabel` — display names (e.g. `DeepSeek Flash` / `DeepSeek`)
- `badgeColorScheme` / `badgeClass` — Tailwind badge styling
- `matches(trackId, variantTag)` — case-insensitive substring match against an experiment's `track_id` and `variant_tag`
- `matchesPrediction(modelName)` — substring match against a prediction's `model_name`

Matching is deliberately fuzzy: an experiment belongs to a track if either its `track_id` or its `variant_tag` contains the model keyword (e.g. `deepseek`, `minimax`, `gemini`, `gpt`/`openai`).

## Legacy / Default Track

`LEGACY_TRACK_CONFIG` is a catch-all that matches any experiment that does **not** match one of the four standard model tracks. It is only surfaced in the UI when at least one such experiment exists (`getAvailableTracks`). Legacy predictions are never filtered out — `filterPredictionsByTrack` returns all predictions for both `all` and `legacy`.

## Per-Track Metrics

- **Ratchet baseline** (`calculateTrackBaselineScore`) — the maximum `metrics.score` across the track's experiments, formatted to 4 decimals, or `N/A` when empty. This is the high-water mark the track must beat.
- **Active variant** (`findTrackActiveVariant`) — the `variant_tag` of the experiment whose `status` is `active`, else `N/A`.
- **Cold start** (`isSectorTrackColdStart`) — true when the track's active (or first) experiment is flagged as a cold start via `isExperimentColdStart`.
- **Summary** (`computeModelTrackSummaries`) — aggregates the above plus experiment count and status (`active` / `baseline` / `none`) for each of the four standard tracks, powering the overview grid.

## UI Surface

The Prompt Auto-Research tab (`PredictorAutoresearchTab`) is driven entirely by the active track:

- `PredictorTrackTabs` — horizontal selector with an **All Models** tab plus one tab per available track, each showing an experiment count and a `From 0` cold-start badge.
- `PredictorModelOverviewGrid` — when **All Models** is active, renders a 4-card grid showing each model's active variant, ratchet baseline score, experiment count, and status side-by-side.
- `PredictorTrackHeaderCards` — when a single track is selected, shows that model's all-time baseline score and active prompt.
- The experiment history table and details pane (score breakdown, research rationale, cognitive toolbox, prompt blocks, prompt diff, segmented prompt inspector) are filtered strictly to the selected track's experiments and predictions.

Selecting a track resets the selected experiment to the first experiment in that track.

## Related

- [[entities/sector-predictor-arena]] — the Arena page hosting the track-isolated autoresearch tab
- [[concepts/multi-track-autoresearch]] — the general multi-track autoresearch pattern
- [[concepts/auto-research-prompt-improver]] — the underlying prompt evolution loop
- [[concepts/prompt-experiment-lifecycle]] — experiment statuses and lineage
