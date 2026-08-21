---
tags: [autoresearch, prompt-evolution, multi-model, track-isolation]
category: concept
---

# Multi-Track Autoresearch

Parallel isolated prompt optimization tracks for distinct portfolio groups (model-specific). Each model (`deepseek-v4-flash`, `MiniMax-M3`) maintains its own independent prompt lineage, baseline, and ratchet score — tracks never cross-pollinate or fall back to another model's prompts.

## Strict Track Isolation

- **No cross-track fallback**: `fetch_active_daily_prompt` queries strictly by `track_id` and `status`. If no active variant exists for a model, it falls back to that model's baseline, then seeds a new baseline — never to another model's active prompt.
- **Single active variant per track**: Deploying a new active variant automatically demotes all prior `active` variants for that `track_id` to `saved`, guaranteeing exactly one live strategy per model track.
- **Ratchet comparison scoped to track**: Baseline score comparison and ratchet promotion operate only within the same `track_id`. The global fallback that previously existed (querying all experiments without track filter) has been removed.

## Frontend Enforcement

- `resolveActiveDailyPrompt` now only considers experiments filtered to the selected model. The `allExperiments` prop and `isFallback` flag have been removed.
- Status badges: `active` status only shows `🟢 ACTIVE` for the single active variant; other `active` records (from prior deployments) display `📦 SAVED`.
- The Autoresearch view defaults to inspecting the current active variant when no explicit selection is made.

## Related

- [[entities/autoresearch]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/daily-market-predictor]]
- [[concepts/prompt-section-splitting]]
