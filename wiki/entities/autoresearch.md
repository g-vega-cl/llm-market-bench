---
tags: [entity, engine, autoresearch, prompt-evolution]
category: entity
---

# Autoresearch

Karpathy-style autonomous prompt improvement loop that runs weekly (Sunday 6:00 PM ET / 10:00 PM UTC). It evaluates portfolio trading performance over the prior 7 days, computes a risk-adjusted ratchet score, and mutates the system prompt to improve future trading execution.

## Architecture & Implementation

The core portfolio auto-research pipeline is located in `apps/engine/autoresearch/`:

- **Runner** (`apps/engine/autoresearch/runner.py`): Top-level orchestrator that checks trade execution safety, invokes evaluation, manages baseline ratchet comparisons, and rolls stochastic cold-start dice.
- **Evaluator** (`apps/engine/autoresearch/evaluator.py`): Gathers weekly trade executions, computes benchmark-relative returns, and formats structured evaluation reports.
- **Metrics** (`apps/engine/autoresearch/metrics.py`): Implements the canonical evaluation math via `compute_score()`.
- **Researcher** (`apps/engine/autoresearch/researcher.py`): Meta-researcher LLM interface that synthesizes prompt mutations and manages cognitive tool selection.

> [!NOTE]
> Portfolio Autoresearch optimizes the core trading prompt (`CORE_ANALYSIS_SYSTEM_PROMPT`). It is decoupled from the Daily Market Predictor autoresearch loop (`apps/engine/tasks/daily_autoresearch.py`, see [[entities/daily-market-predictor]]) and the Sector Predictor loop (`apps/engine/tasks/predictor_autoresearch.py`, see [[entities/sector-predictor-arena]]).

### Weekly Loop Execution Flow:
1. Fetches executions and portfolio performance across the 7-day evaluation window for each model track.
2. Ingests context-enriched market postmortems across 28 days (4 weeks) including newsletter snapshots, event memories, and thematic velocity.
3. Evaluates stochastic exploration: rolls an independent 1-in-6 cold-start dice (`roll_cold_start_dice(sides=6)`). If rolled, the track undergoes a clean-sheet reset (see [[concepts/stochastic-cold-start]]).
4. Retrieves the current active prompt for the track (scoped strictly by `track_id`).
5. Updates parent variant metrics with the current ratchet score.
6. Compares the current variant's Z-score against the track's all-time baseline. If the score exceeds baseline, promotes to `baseline`; otherwise, reverts to previous baseline before mutating.
7. Mutates the prompt using the track's meta-researcher, selecting allowed tools and modular prompt blocks.
8. Deploys a new active variant, demoting prior `active` variants for that track to `saved`.

## Track Isolation & Agency-Driven Tooling

- **Strict Track Isolation**: Each model and track maintains independent prompt lineages and memory records:
  - Daily Predictor: `deepseek-v4-flash`, `MiniMax-M3`, `~typesafe/jev-latest`.
  - Sector Predictor: `deepseek-v4-flash`, `MiniMax-M3`, `gemini-3.5-flash-lite`, `gpt-5.6-luna`.
  - Portfolio Trading: `track_default`, `track_claude`, `track_openai`.
- No cross-track fallback or cross-pollination: prompt queries and memory lookups are always scoped strictly by `track_id` and `scope` (see [[concepts/multi-track-autoresearch]]).
- **Autoresearch Memories (`AUTORESEARCH_INSIGHT`)**: During each optimization cycle, the meta-researcher synthesizes a succinct causal takeaway or hypothesis postmortem (`research_insight`).
  - Saved to the central pgvector `memories` table with `memory_type="AUTORESEARCH_INSIGHT"` and metadata (`track_id`, `scope`, `is_baseline_beat`, `ratchet_score`, `baseline_score`).
  - Context Anti-Bloat & Tiered Decay: Baseline-beating insights (`is_baseline_beat=True`) are preserved permanently (0% decay). Exploratory, non-winning insights decay at a 50% half-life per 30 days. Retrievals are capped at `limit=5`.
- **Track-Specific Tooling**:
  - `query_past_research_memories(track_id, limit)`: Callable tool allowing the portfolio meta-researcher to pull historical hypothesis records on demand.
  - For `track_claude` (the sole track executing skeptical verification), `researcher.py` provides the optional `inspect_verifier_rules_and_rejections` tool inside `run_tool_loop` (see [[concepts/verifier-bypass]]).

## Portfolio Evaluation Math (Unified Risk-Adjusted Z-Score Model)

Portfolio prompt variants are evaluated weekly using the Unified Risk-Adjusted Z-Score, normalized by weekly effective volatility (see [[concepts/risk-adjusted-z-score]]):

$$\text{Composite Excess Return} = 0.4 \times (\text{portfolio} - \text{SPY}) + 0.4 \times (\text{portfolio} - \text{Do-Nothing}) + 0.2 \times (\text{portfolio} - \text{Bond})$$
$$\text{Net Excess Return} = \text{Composite Excess Return} - (\text{max\_drawdown} \times 0.3)$$
$$\text{Weekly Effective Volatility} = \frac{\max(\sigma_{\text{portfolio}}, \sigma_{\text{market}}, 10.0\%)}{\sqrt{52}}$$
$$\text{Score} = \frac{\text{Net Excess Return}}{\text{Weekly Effective Volatility}} \quad (\text{units of } \sigma)$$

### Why We Added the Z-Score Model

1. **Preventing Karpathy Ratchet Lockout (July 19 Outlier)**:
   Under unnormalized net excess return, turbulent macro market weeks produced massive percentage returns that permanently froze the ratchet baseline. On the week of July 19, 2026, variant `v20260719-183000` scored an uncalibrated `24.16`, establishing an impossible hurdle that locked out all subsequent mutations for months. Normalizing by weekly effective volatility recalibrated this outlier to its true statistical baseline of `2.52σ`, unfreezing the ratchet.
2. **Market-Anchored Regime Normalization**:
   During volatile macro market weeks (high SPY $\sigma$), raw percentage swings expand naturally. Dividing by market volatility deflates wide beta swings so high-volatility weeks cannot create unrepeatable, runaway baseline scores. Conversely, in low-volatility calm weeks, precision alpha is scaled up so quiet weeks have an equal opportunity to beat the ratchet.
3. **Idiosyncratic Risk Deflator**:
   If an agent takes extreme, reckless meme bets that exceed market volatility ($\sigma_{\text{portfolio}} > \sigma_{\text{market}}$), the denominator expands to the portfolio's own volatility, mathematically deflating lucky tail-risk flukes.
4. **Historical Backfill**:
   All 35 historical prompt variants in Supabase were recalculated under this formula via `apps/engine/scripts/backfill_normalized_scores.py`.

- **Pre-Week Snapshot Mandate for Do-Nothing Return**:
  - The "do-nothing return" measures how the portfolio would have performed if no trades were made during the evaluated week.
  - To prevent intra-week/Monday trades from polluting starting cash and equity, `_do_nothing_return()` strictly retrieves the latest `portfolio_performance` snapshot prior to `week_start` (`date < week_start`).
  - Aligning starting cash with pre-week positions (`executed_at < week_start`) prevents capital deployed on Monday purchases from disappearing from the cash balance without counting the acquired stocks.
  - Newly initialized accounts without prior snapshots fall back to the earliest snapshot in the week (evaluating to 0.00% if entering with 100% cash).

- **Live Mid-Week Tracking vs. Weekend Audited Settlement**:
  - During mid-week active trading, live portfolio returns and SPY benchmarks stream in daily, but position-level counterfactual valuation across constituent portfolios is not computed on live read paths (preserving [[concepts/zero-frontend-compute]]).
  - Live tracking displays a provisional `0.0000%` do-nothing baseline, demarcated in the UI with a `Provisional Do-Nothing (0.00%)` badge and ledger warnings (see [[concepts/pending-settlement-state]]).
  - Weekend evaluation (`evaluator.py`) calculates `_do_nothing_return()`, records `portfolio_details` with per-asset entry/exit valuations, and stamps `evaluated_at`.
  - Portfolios entering a week in 100% cash produce an audited do-nothing return of `0.0000%`, surfaced in the UI with a `100% Cash at Week Start (0.0000% Return)` badge.

### Historical Audit Note (August 2026 Ratchet Lockout)

Early August 2026 variants (`v20260809-221804` in `track_default` and `v20260816-221127` in `track_claude`) suffered from a temporal cash mismatch where Monday buys reduced cash balance (into negative margin) while the purchased assets were omitted from pre-week holdings. This produced phantom do-nothing returns of -119.8% and -71.1%, inflating variant scores to 15.217 and 16.8998. This locked the Karpathy ratchet, causing all subsequent experiments in late August and early September to be discarded. In September 2026, the engine was patched to enforce pre-week snapshots, and database rows in `prompt_experiments` were updated to their audited scores (0.3186 and 1.7449), unfreezing the ratchet.

## Related

- [[concepts/risk-adjusted-z-score]]
- [[entities/autoresearch-arena]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/pending-settlement-state]]
- [[concepts/prompt-experiment-lifecycle]]
- [[concepts/verifier-bypass]]
- [[entities/daily-market-predictor]]
- [[entities/pipeline]]
