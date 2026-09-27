---
tags: [autoresearch, cold-start, optimization, exploration, prompt-engineering]
category: concept
---

# Stochastic Cold-Start Reset

The stochastic cold-start reset prevents the autonomous research loop from converging on local optima during weekly prompt evolution. On every scheduled evolution run, each track rolls a 1-in-6 stochastic dice (`roll_cold_start_dice(sides=6)`). If the dice rolls 1, the meta-researcher discards prior strategy text and drafts a new hypothesis from scratch.

## Multi-Track Isolation & Independent Dice Rolls

To allow heterogeneous evolutionary trajectories across models:
- **Independent Per-Track Dice Rolls**: Every scheduled run rolls the 1-in-6 dice for each model track independently. In any given run, some tracks may reset "from 0" while others continue standard incremental evolutions. CLI `--cold-start` flags also support forcing a single track or all tracks.
- **Independent Ratchet History**: Each model track maintains its own all-time baseline and variant lineage. When a cold start variant beats the track baseline, it establishes a new baseline; if it underperforms, the track reverts cleanly to its previous best baseline.

## Multi-Week Lookback Horizon (4 Weeks / 28 Days)

Clean-sheet strategy generation requires broad empirical evidence rather than hyper-optimizing to a single week's market regime. All autoresearch loops ingest a standardized 4-week (28-day) context window:
- **Dual Lookback Architecture**: The weekly ratchet score evaluation remains strictly evaluated over the 7-day deployment week to judge whether the prompt delivered alpha. However, prompt mutation, postmortem summaries, trade rejection audits, and newsletter context receive 28 days of history.
- **Rich Empirical Signals**: Evaluators compile 4 weeks of Wall Street metrics, empirical trades, magnitude calibration errors, and newsletter macro themes to inform the new prompt hypothesis.

## Visual Transparency ("From 0" Badge)

Whenever a variant is generated from scratch:
- The experiment record sets `research_output["is_cold_start"] = True` and `experiment_type="radical"`.
- The web UI displays a `From 0` badge (`variant="soft"`, `colorScheme="warning"`, `size="xs"` / `size="sm"`) across all presentation layers:
  - **Track Tabs**: Visible on the track tab when its currently active variant was generated from 0.
  - **Experiment Tables**: Rendered alongside the experiment type or track badge in portfolio, daily prediction, and sector predictor experiment lists.
  - **Variant Detail Headers**: Displayed in the variant inspection drawer and experiment details cards.

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
