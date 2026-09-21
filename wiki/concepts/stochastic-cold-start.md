---
tags: [autoresearch, cold-start, optimization, exploration, prompt-engineering]
category: concept
---

# Stochastic Cold-Start Reset

The stochastic cold-start reset prevents the autonomous research loop from converging on local optima during weekly prompt evolution. On every scheduled evolution run, each track rolls a 1-in-6 stochastic dice (`roll_cold_start_dice(sides=6)`). If the dice rolls 1, the meta-researcher discards prior strategy text and drafts a new hypothesis from scratch.

## Multi-Track Isolation & Guardrails

To prevent synchronized destabilization across models, batch runners (`run_all` in portfolio autoresearch, `run_daily_autoresearch` in daily predictor, and `run_predictor_autoresearch` in sector predictor) enforce a strict guardrail:
- **Maximum 1 Cold Start Per Run**: Across any multi-track batch execution, at most 1 model track may trigger a stochastic cold start reset.
- **Independent Ratchet History**: Each model track maintains its own all-time baseline and variant lineage. When a cold start variant beats the track baseline, it establishes a new baseline; if it underperforms, the track reverts cleanly to its previous best baseline.

## Structural Constraints & Frozen Sections

A cold start is never literally empty. As defined in [[concepts/prompt-section-splitting]], system prompts consist of three segments:
1. **Frozen Engine Header**: System constraints, risk guardrails, pricing protocols, and context injection rules. Managed entirely by the engine and strictly frozen.
2. **Mutable Autoresearch Body**: Analytical strategies, market playbooks, indicator interpretations, and conviction rules. This is the only section the meta-researcher can mutate.
3. **Frozen Output Schema**: JSON schemas and formatting requirements. Enforced automatically by the engine.

During a cold start reset:
- The evaluation report strips the `# Baseline Prompt` and `# Latest Experiment Prompt` sections, replacing them with a directive instructing the LLM to invent an entirely novel strategy from scratch.
- The LLM's raw output is sanitized through `split_prompt()`, `split_daily_predictor_prompt()`, or `split_predictor_prompt()` to ensure no duplicate header tags pollute the prompt store.
- The experiment is recorded with `experiment_type="radical"` and `research_output["is_cold_start"] = True`.

## Coverage Across Prediction Domains

The stochastic cold start reset is active across all three automated prompt evolution loops:
- **Portfolio Autoresearch (`apps/engine/autoresearch/runner.py`)**: Multi-asset trade generator prompt evolution.
- **Daily SPY Predictor (`apps/engine/tasks/daily_autoresearch.py`)**: S&P 500 intraday movement and magnitude calibration prompts.
- **Sector Rotation Predictor (`apps/engine/tasks/predictor_autoresearch.py`)**: Sector ETF leaderboard and uncorrelated pair prediction prompts.

## Related

- [[entities/autoresearch]] (The auto-research engine module)
- [[concepts/multi-track-autoresearch]] (Parallel isolated optimization tracks)
- [[concepts/prompt-section-splitting]] (Frozen headers, mutable bodies, and frozen JSON schemas)
- [[concepts/auto-research-prompt-improver]] (Weekly autonomous prompt iteration)
