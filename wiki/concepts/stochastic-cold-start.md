---
tags: [autoresearch, cold-start, optimization, exploration]
category: concept
---

# Stochastic Cold-Start Reset

The stochastic cold-start reset is a mechanism to prevent the auto-research loop from getting trapped in local optima. At randomized intervals (2–5 weeks), the meta-researcher is instructed to ignore all prior prompt history and generate a novel trading strategy from scratch.

## How It Works

Two helper functions in `apps/engine/autoresearch/runner.py` control the cadence:

- **`get_next_cold_start_interval(min_weeks=2, max_weeks=5)`** — Returns a random integer in the given range, determining how many weeks until the next cold start.
- **`should_trigger_cold_start(current_cycle, target_cycle)`** — Returns `True` when the current evaluation cycle meets or exceeds the target cycle.

When triggered, `run_research()` is called with `cold_start=True`. This appends a `COLD START RESET` directive to the system prompt sent to the meta-researcher LLM:

```
=== COLD START RESET ===
This cycle is a COLD START RESET to avoid local optima.
Ignore the previous system prompt strategy.
Generate a novel, high-conviction trading strategy prompt from scratch.
```

The meta-researcher then produces a fresh prompt unconstrained by prior incremental changes, enabling radical exploration of the prompt space.

## Rationale

Incremental prompt optimization (the default mode) risks converging on a locally optimal but globally mediocre strategy. Stochastic cold starts periodically force the system to explore entirely new regions of the prompt landscape, analogous to random restarts in hill-climbing algorithms.

## Related

- [[entities/autoresearch]] — The auto-research engine module
- [[concepts/multi-track-autoresearch]] — Isolated optimization tracks
- [[concepts/auto-research-prompt-improver]] — Weekly autonomous prompt iteration
