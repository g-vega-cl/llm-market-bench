---
tags: [entity, auto-research, prompt-improvement]
category: entity
---

# Auto-Research Module

The `apps/engine/autoresearch/` module implements the Karpathy-style autonomous prompt improvement loop. A meta-researcher LLM evaluates weekly live trading performance and iteratively improves the trading prompt.

## Configuration

The auto-research system is configured via:
- `packages/config/models.json`: Defines `AUTORESEARCH_EXPERIMENT_OWNER_IDS` (the agents in the experiment group).
- `apps/engine/core/config.py`: Loads the model names and experiment group from `models.json`.
- `AUTORESEARCH_MODEL`: Environment variable (defaults to DeepSeek) used for the meta-researcher.

## Architecture

The auto-research loop runs weekly:
1. **Safety check** — did the prompt crash trading (< 2 trades)? If so, revert.
2. **Evaluate** — compute a single score: `(portfolio_return% - SPY_return%) - (max_drawdown% × 0.3)`. Find the baseline (best score so far) and show Δ.
3. **Revert on failure** — if score < baseline, revert the active prompt to the baseline via `revert_to_baseline()`. This enforces the Karpathy ratchet: the meta-researcher always builds from the known-good foundation.
4. **Research** — LLM proposes a new prompt variant (incremental or radical) based on the *post-revert baseline*.
5. **Deploy** — always activate the new variant generated in step 4.
6. **Track** — if this week's score > baseline, it becomes the new baseline (best prompt+score pair).

## System-Heavy Prompt Architecture

As of **2026-05-19**, the system moved to a **System-Heavy** architecture to maximize the surface area of evolution for the meta-researcher.

- **System Prompt (The Rulebook)**: Contains 100% of the trading logic, risk management (SMA rules), SOPs (5-Whys), and tool-usage requirements. This part is stored in the database and is mutated by the meta-researcher.
- **User Prompt (The Data Case)**: Reduced to a minimal skeleton that only handles dynamic data injection (News snippets, Portfolio status, Historical context). This part is static in the source code.

This split ensures that the "Brain" (System) is decoupled from the "Environment" (User), allowing the Auto-Research engine to iterate on the very rules of the system itself.

## Files

- `program.md` — the meta-researcher's instructions (constraints and goals)
- `metrics.py` — Wall Street metrics computation + `compute_score()`
- `evaluator.py` — gathers weekly data, computes baseline, formats report
- `researcher.py` — calls DeepSeek v4 Pro with structured output
- `runner.py` — orchestrates the weekly evaluation and deployment cycle
- `prompt_store.py` — DB operations for prompt_experiments
- `bootstrap.py` — initializes the baseline variant (score = 0)
- `window.py` — shared week-window helper

## Key Design Decisions

- **Single score**: One number to optimize — risk-adjusted return vs SPY. No composite of 8 dimensions.
- **No validator**: Removed. The safety checker (< 2 trades → revert) is the only guardrail. Trust the process.
- **Always deploy**: Every week deploys a new prompt. No gate. The meta-researcher always explores.
- **Hard ratchet**: When an experiment fails to beat the baseline, `revert_to_baseline()` is called to set the active prompt back to the baseline before the next experiment. Code-level enforcement — not just instructions to the LLM.
- **Baseline tracking**: The highest score achieved so far (tied to its prompt). The meta-researcher's target. Only moves up.
- **System-Heavy Evolution**: Moving logic from User to System prompt to ensure 100% of the trading "SOP" can be improved by the LLM.
- **Control portfolios are reference only**: Shown in the report but not part of the score.

## Score Formula

```
score = (portfolio_return_pct - spy_return_pct) - (max_drawdown_pct × 0.3)

Baseline = max(all previous scores) — the bar to beat. Only moves up.
The meta-researcher's report shows: "Baseline: X (best so far)  (Δ: +/-Y vs baseline)"
```

## Recent Changes

- **2026-05-19**: **System-Heavy Refactor** — Moved all 16 logic points, SMA rules, and output definitions from the static User prompt to the evolvable System prompt. Reduced User prompt to a data-only skeleton.
- **2026-05-13**: Hard ratchet — `revert_to_baseline()` enforces Karpathy pattern.
- **2026-05-12**: Always deploy — removed activation gate. Every week gets a new prompt regardless of score.
- **2026-05-12**: Baseline tracking — baseline is max historical score, not last week's score. With tests.
- **2026-05-12**: Major simplification — removed validator.py, decision_quality.py. Replaced 8-dimension composite score with single formula. Dropped VIXY regime queries, concordance, conviction calibration, mistake patterns, sample trades, and stagnation checks.

## Related

- [[concepts/auto-research-prompt-improver]] — the concept behind this module
- [[entities/engine]] — the parent engine
