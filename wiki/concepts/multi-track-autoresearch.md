---
tags: [autoresearch, prompt-evolution, multi-model, track-isolation]
category: concept
---

# Multi-Track Autoresearch

Parallel isolated prompt optimization tracks across inference models and trading scopes:
- **Daily Predictor**: Independent lineages for `deepseek-v4-flash`, `MiniMax-M3`, and `~typesafe/jev-latest` (with OpenAI Luna as Jev meta-researcher).
- **Sector Predictor**: Independent lineages for all 4 models (`deepseek-v4-flash`, `MiniMax-M3`, `gemini-3.5-flash-lite`, `gpt-5.6-luna`).
- **Portfolio Trading**: Independent tracks for `track_default`, `track_claude`, and `track_openai`.

Each track maintains its own independent prompt lineage, baseline, ratchet score, and research memory store. Tracks never cross-pollinate or fall back to another track's prompts or takeaways.

## Strict Track Isolation

- **No cross-track fallback**: Prompts and memories are queried strictly by `track_id` and `scope`. If no active variant exists for a model, it falls back to that model's baseline, then seeds a new baseline, never falling back to another model's active prompt.
- **Single active variant per track**: Deploying a new active variant automatically demotes all prior `active` variants for that `track_id` to `saved`, guaranteeing exactly one live strategy per model track.
- **Ratchet comparison scoped to track**: Baseline score comparison and ratchet promotion operate only within the same `track_id`.
- **Track-Isolated Memories (`AUTORESEARCH_INSIGHT`)**: During optimization cycles, meta-researchers synthesize succinct hypotheses and postmortems (`research_insight`). These are recorded in `memories` with `metadata.track_id` and `metadata.scope`.
- **Context Protection & Conditional Decay**: Baseline-winning insights (`is_baseline_beat=True` or `importance_score >= 8`) never decay (0% decay rate). Exploratory or non-winning insights decay at a 50% half-life per 30 days. Retrievals are capped at `limit=5` to prevent context bloat.

## Frontend Enforcement

- `resolveActiveDailyPrompt` now only considers experiments filtered to the selected model. The `allExperiments` prop and `isFallback` flag have been removed.
- Status badges: `active` status only shows `🟢 ACTIVE` for the single active variant; other `active` records (from prior deployments) display `📦 SAVED`.
- The Autoresearch view defaults to inspecting the current active variant when no explicit selection is made.

## Related

- [[entities/autoresearch]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/daily-market-predictor]]
- [[concepts/prompt-section-splitting]]
