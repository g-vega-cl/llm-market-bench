---
tags: [entity, engine, autoresearch, prompt-evolution]
category: entity
---

# Autoresearch

Karpathy-style autonomous prompt improvement loop that runs weekly (Sunday 6:00 PM ET / 10:00 PM UTC). It evaluates portfolio trading performance over the prior 7 days, computes a risk-adjusted ratchet score, and mutates the system prompt to improve future trading execution.

## Architecture & Implementation

The core portfolio auto-research pipeline is located in `apps/engine/autoresearch/`:

- **Runner** (`apps/engine/autoresearch/runner.py`): Top-level orchestrator that checks trade execution safety, invokes evaluation, manages baseline ratchet comparisons, rolls stochastic cold-start dice, and triggers the monthly meta-autoresearch check on the first weekend of each calendar month.
- **Evaluator** (`apps/engine/autoresearch/evaluator.py`): Gathers weekly trade executions, computes benchmark-relative returns, and formats structured evaluation reports.
- **Metrics** (`apps/engine/autoresearch/metrics.py`): Implements the canonical evaluation math via `compute_score()`.
- **Researcher** (`apps/engine/autoresearch/researcher.py`): Meta-researcher LLM interface that synthesizes prompt mutations and manages cognitive tool selection.
- **Monthly Meta-Autoresearcher** (`apps/engine/autoresearch/meta_autoresearch.py`): Evaluates 30-day cross-track weekly mutations (`CORE_ANALYSIS_SYSTEM_PROMPT` and `DAILY_PREDICTOR_PROMPT`) on **Mutation Yield** (50% Baseline Beat Rate, 35% Clamped Score Delta, 15% Non-Crash Rate), builds an empirical 30-day prompt-block leaderboard, and ratchets `META_AUTORESEARCH_PROGRAM` directives consumed by both `apps/engine/autoresearch/researcher.py` and `apps/engine/tasks/daily_autoresearch.py`.
  - **Bayesian-Shrunk Block Leaderboard**: `compute_block_and_type_leaderboard` ranks blocks and mutation modes by a shrunk beat rate toward a neutral 50% prior — $\text{shrunk} = 50.0 + (\text{raw} - 50.0) \cdot \frac{n}{n + 4}$ — so a single lucky use (100% raw) cannot outrank a battle-tested block (e.g. 80% over 10 uses). The formatted leaderboard table exposes both `Beat Rate %` and `Shrunk Rate %` columns.
  - **Clean Directive Splicing**: `splice_research_program(program_text, meta_directives)` replaces the mutable `## How to Improve the Prompt` heuristics section in `program.md` in place, preventing conflicting duplicate instruction blocks when the portfolio researcher injects active meta-directives.
  - **24-Hour TTL Cache**: `get_active_meta_directives_sync()` memoizes the active directives plus empirical leaderboard in a process-level cache (`_META_DIRECTIVES_CACHE`, `ttl_seconds = 86400.0`), avoiding repeated DB round-trips on every weekly run. `clear_meta_directives_cache()` busts the cache explicitly after a new `META_AUTORESEARCH_PROGRAM` variant is inserted.

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

## Predictor-Track Baseline Guard

The two predictor loops — Daily SPY (`tasks/daily_autoresearch.py`) and Sector (`tasks/predictor_autoresearch.py`) — no longer scan for a raw maximum stored score when they look for the variant to compare against. Both call `select_baseline_candidate(variants, exclude_tag)` from `apps/engine/core/conviction_scoring.py`, which:

- skips any variant whose `metrics.predictions_evaluated` is below `MIN_BASELINE_SAMPLE = 5` (a single lucky call near 98/100 would otherwise become an unreachable ceiling and force a revert every week), and
- shrinks each surviving candidate's stored score toward a neutral 50 prior with `shrunk_baseline_score(score, n) = 50 + (score − 50) · n/(n + 10)`, so five calls keep a third of their apparent edge and twenty keep two thirds; a missing sample count shrinks fully to 50.

The parent/active tag is always excluded from its own comparison set, and when no variant clears the guard the loop falls back to the parent prompt's score. Full derivation lives in [[concepts/conviction-points]]. Stored historical scores must be consistent with the current formula for this comparison to be meaningful; `apps/engine/scripts/backfill_conviction_scores.py` rewrites row-level `conviction_score` values and per-experiment metrics for the daily and sector prompts (dry run by default, `--apply` to write), matching predictions by prompt tag with a track-scoped evaluation-window fallback and excluding backtest rows.

### Shared Backfill & Realignment Core (`core/conviction_backfill.py`)

The one-shot backfill CLI (`apps/engine/scripts/backfill_conviction_scores.py`) and the sector realignment task (`apps/engine/tasks/realign_predictor_baseline.py`) share a single implementation module, `apps/engine/core/conviction_backfill.py`, so the two entry points cannot drift apart. It provides:

- `recompute_daily_conviction(rows)` / `recompute_sector_conviction(rows)` — re-score evaluated prediction rows with `conviction_points()`. The sector variant prices the best leg against `confidence` and the worst leg against `worst_confidence` only when that column is present, averaging the legs; legacy rows without a stated worst-pick probability skip that leg rather than borrowing the best-pick confidence.
- `match_predictions_by_tag(experiments, predictions, tag_key, date_key, model_key)` — attributes evaluated predictions to the variant that produced them. An exact prompt tag wins; when a variant has no tagged rows (older rows predate the tag column), it falls back to the variant's `week_start`/`week_end` evaluation window, scoped to the experiment's model track so one model's predictions cannot score another model's prompt. `track_default` is treated as a shared scope and pools models. Backtest rows (`is_backtest_tag`) are always excluded from the live ratchet.
- `recompute_experiment_metrics(experiments, predictions, tag_key, calculator)` — produces a per-experiment report carrying `old_score`, `new_metrics`, and `prediction_count`, skipping backtest experiments.
- `propose_track_realignment(report)` — groups the report by `track_id` and picks each track's winner through `select_baseline_candidate` (active variant excluded, minimum-sample and shrinkage guards applied). It returns one proposal per experiment carrying the recomputed metrics plus optional `status` (`baseline` / `saved`) and `parent_tag` updates, so callers write metrics and status in a single update.
- `summarize_tracks(proposals)` — condenses proposals into a per-track `{baseline_tag, baseline_score, active_tag}` summary.

Because realignment is per track, a strong prompt in one model's lineage can never set another model's baseline, and a single-sample fluke is never promoted.

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
- [[concepts/conviction-points]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/pending-settlement-state]]
- [[concepts/prompt-experiment-lifecycle]]
- [[concepts/verifier-bypass]]
- [[entities/daily-market-predictor]]
- [[entities/sector-predictor-arena]]
- [[entities/pipeline]]
