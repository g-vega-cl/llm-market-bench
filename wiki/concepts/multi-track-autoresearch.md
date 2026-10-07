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
- **Ratchet comparison scoped to track**: Baseline score comparison and ratchet promotion operate only within the same `track_id`. For portfolio trading tracks (`track_default`, `track_claude`, `track_openai`), baselines are evaluated using the Unified Risk-Adjusted Z-Score in $\sigma$ units (see [[concepts/risk-adjusted-z-score]]), ensuring individual track baselines cannot be permanently frozen by volatile market regimes or lucky outlier weeks.
- **Track-Isolated Memories (`AUTORESEARCH_INSIGHT`)**: During optimization cycles, meta-researchers synthesize succinct hypotheses and postmortems (`research_insight`). These are recorded in `memories` with `metadata.track_id` and `metadata.scope`.
- **Independent Stochastic Cold-Start**: During weekly evolution, each track rolls the 1-in-6 stochastic dice (`roll_cold_start_dice(sides=6)`) independently. One track can reset "from 0" based on 4 weeks of empirical history while another executes an incremental mutation (see [[concepts/stochastic-cold-start]]).
- **Multi-Week Lookback Horizon (28 Days)**: Prompt synthesis and postmortem analysis across all tracks ingest a 28-day window of market events and predictions, while the weekly ratchet score remains strictly evaluated over the 7-day active week.
- **Context Protection & Conditional Decay**: Baseline-winning insights (`is_baseline_beat=True` or `importance_score >= 8`) never decay (0% decay rate). Exploratory or non-winning insights decay at a 50% half-life per 30 days. Retrievals are capped at `limit=5` to prevent context bloat.

## Frontend Enforcement

- `resolveActiveDailyPrompt` now only considers experiments filtered to the selected model. The `allExperiments` prop and `isFallback` flag have been removed.
- Status badges: `active` status only shows `🟢 ACTIVE` for the single active variant; other `active` records (from prior deployments) display `📦 SAVED`.
- The Autoresearch view defaults to inspecting the current active variant when no explicit selection is made.

## Related

- [[entities/autoresearch]]
- [[concepts/risk-adjusted-z-score]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/daily-market-predictor]]
- [[concepts/prompt-section-splitting]]
