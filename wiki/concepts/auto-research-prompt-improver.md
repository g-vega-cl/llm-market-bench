---
tags: [concept, autoresearch, prompt-improver, meta-research]
category: concept
---

# Auto-Research Prompt Improver

Weekly autonomous prompt iteration via a meta-researcher LLM. The system evaluates live trading performance over the past week and generates an improved trading prompt for the next week.

## Mechanism

1. The meta-researcher (`apps/engine/autoresearch/researcher.py`) receives the current trading prompt, recent performance metrics, and the list of available tools and modular prompt blocks.
2. It proposes changes: which tools to include, which prompt blocks to enable, and a free-form change description.
3. The new prompt and block selection are persisted to the database for the next trading cycle.

## Modifiable Elements

The researcher can toggle:

- **Pull tools**: The list of non-execution tools available to the analysis agent (e.g., `get_portfolio_ledger`, `get_todays_news_menu`, `get_ticker_news`, `web_search`, and many more). Execution tools (`calculate_buy_quantity`, `calculate_sell_quantity`) are force-injected and not togglable.
- **Prompt blocks**: Enable/disable any of the modular discipline blocks (`let_winners_run`, `cut_losers_fast`, `catalyst_expiry_timer`, `five_whys_causal`, `mece_risk_partition`, `options_vol_discipline`, `macro_regime_routing`, `disconfirming_evidence_gate`, `catalyst_radar_discipline`, `forward_calendar_scenario_anticipation`, `ticker_news_verification`, `shadow_banking_liquidity_plumbing`).

## Monthly Meta-Autoresearcher (Mutation Yield Ratchet)

Both the weekly Portfolio autoresearcher (`apps/engine/autoresearch/researcher.py`) and the weekly Daily S&P Predictor autoresearcher (`apps/engine/tasks/daily_autoresearch.py`) are supervised by a monthly meta-autoresearcher (`apps/engine/autoresearch/meta_autoresearch.py`):

1. **Monthly Cadence Gate**: Piggybacks onto `run_all` in `apps/engine/autoresearch/runner.py`. On the first weekly run of each calendar month (`1 <= today.day <= 7` with no existing `META_AUTORESEARCH_PROGRAM` variant for that month), it audits the prior 30 days of evaluated weekly prompt experiments across `CORE_ANALYSIS_SYSTEM_PROMPT` and `DAILY_PREDICTOR_PROMPT`.
2. **Mutation Yield Scoring (`compute_monthly_mutation_yield`)**: Evaluates the meta-researcher on how often its weekly mutations beat their track baselines rather than raw market direction:
   - **Baseline Beat Rate (50% weight)**: Percentage of evaluated weekly mutations that beat or matched their parent/baseline score.
   - **Normalized Clamped Score Delta (35% weight)**: Mean `score - parent_score` clamped to `[-15.0, +15.0]` and scaled to `[0, 100]`.
   - **Non-Crash Rate (15% weight)**: Percentage of weekly mutations that did not crash trading execution.
3. **Empirical Block & Mode Leaderboard (`compute_block_and_type_leaderboard`)**: Aggregates 30-day beat rates and mean score deltas per modular prompt block in `selected_prompt_blocks` and per mutation mode (`incremental` vs `radical`).
4. **Meta-Directive Ratchet & Injection**: Compares the active `META_AUTORESEARCH_PROGRAM` variant (`track_id = "meta_autoresearch"`) against the best historical meta-baseline. If Mutation Yield regresses, it reverts to the baseline meta-directives before mutating. Weekly Portfolio and Daily autoresearch runs inject the active meta-directives and 30-day empirical block leaderboard via `get_active_meta_directives_sync()`.

## Related

- [[concepts/modular-prompt-blocks]]
- [[entities/autoresearch]]
- [[entities/daily-market-predictor]]
