---
tags: [daily-predictions, autoresearch, scoring, ui, fallback-resolution]
category: concept
---

# Experiment Display Score

The **experiment display score** is the single resolution rule the daily-predictions UI uses to decide what score to show for a prompt experiment. It exists because a `PromptExperiment` row can legitimately have an empty `metrics` object — for example a freshly seeded baseline whose predictions have already been evaluated but whose metrics were never materialized. Showing `Pending` in that case hides real, already-computed performance.

## Resolution Order

`getExperimentDisplayScore(exp, predictions)` in `apps/web/src/features/daily-predictions/utils/daily-predictions-helpers.ts` resolves in two steps:

1. **Stored metrics** — if `exp.metrics.score` is a number, return it. This is the authoritative value written by the engine.
2. **Ratchet fallback** — if `predictions` are supplied and non-empty, call `resolveRatchetMetrics(exp, predictions)` (exported from `DailyScoreBreakdown`) and return its `score` when numeric.

If neither yields a number, the helper returns `null`, and callers render `Pending`.

## Why the Fallback Lives in the UI

The engine remains the source of truth for persisted metrics; the fallback is a *display* concern only. It recomputes the same ratchet score from the evaluated prediction rows already loaded by the page, so the sidebar, header, and milestone cards agree with the score breakdown table without requiring a metrics backfill.

## Consumers

Every surface that shows an experiment score routes through this helper, so they never disagree:

- `VariantSidebar` / `VariantSidebarItem` — the variant list score badge
- `SelectedVariantHeader` — the `Score:` field in the selected-variant header
- `AutoresearchMilestoneCards` — via `computeExperimentMilestones(experiments, predictions)`, which uses the helper for the active prompt, the best baseline, and the parent experiment when computing the delta

Because the fallback needs prediction rows, `predictions` is threaded as an optional prop from `DailyPredictionsPage` down through `AutoresearchMilestoneCards`, `AutoresearchHistoryArena`, `VariantSidebar`, and `SelectedVariantHeader`. Omitting it degrades gracefully to the stored-metrics-only behavior.

## The `track_default` Sentinel

Experiments created before per-track routing carry `track_id = 'track_default'`. Two places special-case it:

- `SPY_PREDICTOR_MODELS` — the DeepSeek Flash matcher accepts `track_default` in addition to any model name containing `deepseek`, so legacy experiments still group under the right predictor.
- `isPredictionInExperiment` in `DailyScoreBreakdown` — the track filter is skipped when `experiment.track_id === 'track_default'`, preventing legacy experiments from being filtered out of their own score breakdown.

## Related

- [[entities/daily-score-breakdown]] — the component that owns `resolveRatchetMetrics` and ratchet score computation
- [[entities/autoresearch-arena]] — the arena UI that consumes the display score
- [[entities/daily-predictor-backtest-arena]] — backtest counterpart of the same arena
- [[entities/autoresearch]] — the experiment lifecycle these scores rank
