---
tags: [autoresearch, multi-track, prompt-optimization, isolation]
category: concept
---

# Multi-Track AutoResearch

Multi-track AutoResearch enables parallel, isolated prompt optimization loops for distinct portfolio groups. Each track (e.g., `track_default`, `track_claude`, `track_openai`) maintains its own active prompt, experiment history, and baseline metrics — preventing overwrite collisions when different model families optimize independently.

## Track Isolation

Each track is identified by a `track_id` string stored in the `prompt_experiments` database table. The `AUTORESEARCH_TRACKS` config in `models.json` maps track IDs to lists of model owner IDs:

```json
{
  "AUTORESEARCH_TRACKS": {
    "track_default": ["gemini-3.1-flash-lite", "deepseek-v4-pro", "MiniMax-M3"],
    "track_claude": ["claude-haiku-4-5"]
  }
}
```

When `PromptFactory` builds analysis messages, it resolves an agent's `owner_id` to its track, then fetches the active prompt for that track via `get_active_prompt(track_id=...)`. This ensures Claude agents receive Claude-optimized prompts while the default track agents receive their own independently evolved prompts.

## Database Schema

The `prompt_experiments` table includes a `track_id` column (default `'track_default'`) with an index for fast lookups. All prompt store functions (`get_active_prompt`, `get_active_variant`, `save_variant`, `get_previous_variants`, `get_all_time_baseline`) accept a `track_id` parameter and scope queries accordingly.

## UI Track Tabs

The `TrackTabs` component on the AutoResearch Arena page derives unique track IDs from experiment data and renders a tab bar. Users can toggle between tracks to view isolated experiment histories, baseline metrics, and prompt diffs. Track labels are human-readable (e.g., `track_claude` → "Claude").

## Fallback Behavior

If a `track_id` query fails (e.g., column missing in older DB instances), all prompt store functions fall back to a base query without the `track_id` filter, ensuring backward compatibility.

## Related

- [[entities/autoresearch]] — The auto-research engine module
- [[entities/autoresearch-arena]] — The web UI for browsing experiments
- [[concepts/stochastic-cold-start]] — Randomized cold-start resets to escape local optima
- [[concepts/verifier-bypass]] — Skipping skeptical verification for fast models
