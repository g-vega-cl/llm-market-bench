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
    "track_claude": ["claude-haiku-4-5", "deepseek-v4-flash"],
    "track_openai": ["gpt-5.4-nano"]
  }
}
```

When `PromptFactory` builds analysis messages, it resolves an agent's `owner_id` to its track, then fetches the active prompt for that track via `get_active_prompt(track_id=...)`. This ensures Claude agents receive Claude-optimized prompts while OpenAI and default track agents receive their own independently evolved prompts.

## Database Schema & Strict Track Isolation

The `prompt_experiments` table includes a `track_id` column (default `'track_default'`) with an index for fast lookups (applied to remote Supabase via `supabase db push`). All prompt store functions (`get_active_prompt`, `get_active_variant`, `save_variant`, `get_previous_variants`, `get_all_time_baseline`) accept a `track_id` parameter and scope queries strictly to that track:
- **Baseline Independence**: Querying `get_all_time_baseline(track_id='track_claude')` returns only variants created for `track_claude`. If no variants exist yet, it returns `None`, allowing the track to establish its own independent baseline without cross-track score leakage.
- **Demotion Isolation**: `save_variant()` demotes active/baseline variants to `saved` strictly within `WHERE track_id = <track_id>`.

## CLI Support

The CLI entrypoint (`main.py`) supports multi-track execution and stochastic cold-start resets:
```sh
# Run auto-research dry-run for specific track
./apps/engine/.venv/bin/python3 apps/engine/main.py autoresearch --dry-run --track track_claude

# Force a cold-start reset to generate a new prompt from scratch
./apps/engine/.venv/bin/python3 apps/engine/main.py autoresearch --dry-run --track track_openai --cold-start
```

## UI Track Badges & Tabs

- **Auto-Research Arena (`/autoresearch`)**: The `TrackTabs` component renders a tab bar (`track_default`, `track_claude`, `track_openai`). Experiment history tables and detail views render explicit track badges.
- **Portfolios Dashboard (`/portfolios`)**: Portfolio cards detect multi-track agent owner IDs (`getAutoresearchOwnerIds`) and display a dedicated `Track: <Label>` badge.

## Related

- [[entities/autoresearch]] — The auto-research engine module
- [[entities/autoresearch-arena]] — The web UI for browsing experiments
- [[concepts/stochastic-cold-start]] — Randomized cold-start resets to escape local optima
- [[concepts/verifier-bypass]] — Skipping skeptical verification for fast models
