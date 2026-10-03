---
tags: [entity, engine, autoresearch, prompt-evolution]
category: entity
---

# Autoresearch

Karpathy-style autonomous prompt improvement loop that runs weekly (Sunday 6:00 PM ET / 10:00 PM UTC). It evaluates recent daily predictions over the prior 7 days, computes a ratchet score, and mutates the system prompt to improve future performance.

## Implementation

Located in `apps/engine/tasks/daily_autoresearch.py`. The `run_daily_autoresearch_for_model` function:

1. Fetches predictions for the past 7 days for a specific model track (evaluating all available trading sessions for the weekly ratchet score).
2. Fetches context-enriched market postmortems via `fetch_autoresearch_context` across 28 days (4 weeks), querying `newsletter_snapshots`, `memories` (market events, post-mortems, resolutions), magnitude postmortems, and `concept_metrics` (thematic velocity).
3. Evaluates stochastic exploration: each model track rolls an independent 1-in-6 cold-start dice (`roll_cold_start_dice(sides=6)`). If rolled, the track undergoes a clean-sheet cold-start reset with a 4-week empirical evidence window (see [[concepts/stochastic-cold-start]]).
4. Fetches the current active prompt for that model track (strictly by `track_id` and `status`). Falls back to baseline, then seeds a new baseline if none exist.
5. Updates parent variant metrics with the current ratchet score.
6. Compares current score against the best baseline within the same model track. If current exceeds best baseline, promotes to `baseline`.
7. Mutates the prompt using the track's meta-researcher, feeding it the day-by-day catalyst context, empirical trade audits, and active thematic playbooks.
8. Deploys a new active variant, demoting all prior `active` variants for that track to `saved`.

## Track Isolation & Agency-Driven Tooling

- **Strict Track Isolation**: Each model and track maintains independent prompt lineages and memory records:
  - Daily Predictor: `deepseek-v4-flash` and `MiniMax-M3`.
  - Sector Predictor: All 4 models (`deepseek-v4-flash`, `MiniMax-M3`, `gemini-3.5-flash-lite`, `gpt-5.6-luna`).
  - Portfolio Trading: `track_default`, `track_claude`, `track_openai`.
- No cross-track fallback or cross-pollination: prompt queries and memory lookups are always scoped strictly by `track_id` and `scope`.
- Baseline seeding creates a new baseline for a model if none exists.
- **Autoresearch Memories (`AUTORESEARCH_INSIGHT`)**: During each optimization cycle, the meta-researcher synthesizes a succinct causal takeaway or hypothesis postmortem (`research_insight`).
  - Saved to the central pgvector `memories` table with `memory_type="AUTORESEARCH_INSIGHT"` and metadata (`track_id`, `scope`, `is_baseline_beat`, `ratchet_score`, `baseline_score`).
  - Context Anti-Bloat & Tiered Decay: Baseline-beating insights (`is_baseline_beat=True`) are preserved permanently (0% decay). Exploratory, non-winning insights decay at a 50% half-life per 30 days. Retrievals are capped at `limit=5` to safeguard context windows.
- **Track-Specific Tooling**:
  - `query_past_research_memories(track_id, limit)`: Callable tool allowing the portfolio meta-researcher to pull historical hypothesis records on demand.
  - For `track_claude` (the sole track executing skeptical verification), `researcher.py` provides the optional `inspect_verifier_rules_and_rejections` tool inside `run_tool_loop` (see [[concepts/verifier-bypass]]).

## Portfolio Evaluation Math & Do-Nothing Benchmark

Portfolio prompt variants are evaluated weekly across three composite benchmarks (Benchmark-Triad Weighted Model):

$$\text{excess\_return} = 0.4 \times (\text{portfolio} - \text{SPY}) + 0.4 \times (\text{portfolio} - \text{Do-Nothing}) + 0.2 \times (\text{portfolio} - \text{Bond})$$
$$\text{Score} = \text{excess\_return} - (\text{max\_drawdown} \times 0.3)$$

- **Pre-Week Snapshot Mandate for Do-Nothing Return**:
  - The "do-nothing return" measures how the portfolio would have performed if no trades were made during the evaluated week.
  - To prevent intra-week/Monday trades from polluting starting cash and equity, `_do_nothing_return()` strictly retrieves the latest `portfolio_performance` snapshot prior to `week_start` (`date < week_start`).
  - Aligning starting cash with pre-week positions (`executed_at < week_start`) prevents capital deployed on Monday purchases from disappearing from the cash balance without counting the acquired stocks.
  - Newly initialized accounts without prior snapshots fall back to the earliest snapshot in the week (evaluating to 0.00% if entering with 100% cash).

- **Live Mid-Week Tracking vs. Weekend Audited Settlement**:
  - During mid-week active trading, live portfolio returns and SPY benchmarks stream in daily, but position-level counterfactual valuation across constituent portfolios is not computed on live read paths (preserving [[concepts/zero-frontend-compute]]).
  - Live tracking displays a provisional `0.0000%` do-nothing baseline, demarcated in the UI with a `Provisional Do-Nothing (0.00%)` badge and ledger warnings (see [[concepts/pending-settlement-state]]).
  - Weekend evaluation (`evaluator.py`) calculates `_do_nothing_return()`, records `portfolio_details` with per-asset entry/exit valuations, and stamps `evaluated_at`.
  - Portfolios entering a week in 100% cash (e.g. liquidated the prior Friday) produce an audited do-nothing return of `0.0000%`. The UI surfaces this with a `100% Cash at Week Start (0.0000% Return)` badge to distinguish true cash returns from uncalculated provisional fallbacks.
  - This separation is purely for display transparency and does not modify any scoring formulas or evaluation math.

### Historical Audit Note (August 2026 Ratchet Lockout)

Early August 2026 variants (`v20260809-221804` in `track_default` and `v20260816-221127` in `track_claude`) suffered from a temporal cash mismatch where Monday buys reduced cash balance (into negative margin) while the purchased assets were omitted from pre-week holdings. This produced phantom do-nothing returns of -119.8% and -71.1%, inflating variant scores to 15.217 and 16.8998. This locked the Karpathy ratchet, causing all subsequent experiments in late August and early September to be discarded. In September 2026, the engine was patched to enforce pre-week snapshots, and database rows in `prompt_experiments` were updated to their audited scores (0.3186 and 1.7449), unfreezing the ratchet.

## Related

- [[concepts/auto-research-prompt-improver]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/pending-settlement-state]]
- [[concepts/verifier-bypass]]
- [[entities/daily-market-predictor]]
- [[entities/pipeline]]
