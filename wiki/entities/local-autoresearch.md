---
tags: [entity, engine, autoresearch, strata, jev, prompt-evolution]
category: entity
---

# Local Autoresearch (Strata + Jev)

The Local Autoresearch loop (`apps/engine/local_autoresearch/`) is an autonomous offline prompt and feature-set evolution engine. It pairs a locally hosted meta-researcher model (**Qwen3.8-Flash-Next via Strata** on localhost port `8080`) with **Jev System One** on OpenRouter to iteratively evolve the Daily S&P 500 Predictor strategy and input data manifest.

## Architectural Roles

1. **Meta-Researcher (Qwen via Strata)**:
   - Hosts Qwen locally using Strata's hybrid GPU/CPU/RAM inference engine (`http://localhost:8080/v1`).
   - Acts as the cognitive architect: mutates both the **Jev Decision Criteria** (`criteria_up`, `criteria_down`, `min_confidence`) AND the **Data Manifest** ("Box of Data" selector).
   - Prunes noisy inputs (e.g. eliminating currency noise `UUP` or filtering out unhelpful newsletter senders from the 15 available).
   - Generates and reads sandboxed causal memories in local SQLite (`.local_autoresearch.db`).

2. **Decision Model (Jev System One via OpenRouter Decisions API)**:
   - Fast, deterministic, sub-second typed classification (`UP` vs `DOWN`).
   - Evaluates point-in-time daily market contexts concurrently via `asyncio.gather`.
   - Incorporates **Confidence Gating**: trades with confidence $< \text{min\_confidence}$ are routed as `NO_TRADE` to protect Sharpe and directional win rate.

## Point-in-Time Hermeticity & Cache

- **Zero Lookahead Guarantee**: On simulated date $T$, market context is strictly built from items timestamped prior to 09:15 AM ET on date $T$.
- **Local Feature Cache** (`.local_autoresearch_cache.db`):
   - Pre-materializes historical trading days, actual OHLC outcomes, and point-in-time newsletter snapshots from Supabase via `cache_builder.py`.
   - Groups trading sessions into atomic **ISO calendar weeks** (`YYYY-Www`).
   - Prevents repetitive remote queries, slashing iteration cycle time to 4–6 seconds.

## Non-Chronological Weekly Grouped K-Fold

To prevent overfitting to the latest market regime while respecting weekly market dynamics:
- **Atomic Weekly Blocks**: Days within a single calendar week (Monday–Friday) are never split across train and test sets.
- **Randomized Split**: Calendar weeks are randomly partitioned (e.g. 75% train weeks, 25% test weeks) across the entire historical timeline.
- **Overfit Penalty**:
  $$\text{Overfit Penalty} = \max(0, \text{Score}_{\text{train}} - \text{Score}_{\text{test}})$$
  $$\text{Effective Score} = \text{Score}_{\text{test}} - 0.5 \times \text{Overfit Penalty}$$
  A prompt that scores well on training weeks but collapses on held-out test weeks is penalized and discarded.

## Module Structure

- `manifest.py`: Pydantic definitions for `DataManifest`, `JevCriteriaConfig`, and `pack_daily_context()`.
- `local_store.py`: Sandboxed SQLite database (`.local_autoresearch.db`) for prompt experiments and causal memories.
- `cache_builder.py`: Historical data extractor and weekly block partitioner (`.local_autoresearch_cache.db`).
- `jev_evaluator.py`: Async concurrent batch evaluator for Jev Decisions API with confidence gating.
- `strata_client.py`: Async client for local Qwen on `http://localhost:8081/v1`.
- `runner.py`: Top-level CLI loop orchestrator.

## Champion Tournament Variant & Discovered Manifest

After a 100-iteration tournament run across historical trading sessions, the winning champion variant was discovered:
- **Variant Tag**: `qwen-jev-243de1` (Score: **80.43**, Out-of-Sample Test Win Rate: **80.0%**).
- **Confidence Gating**: Filter threshold set at `min_confidence = 61.0%`. Predictions below 61% are routed to `NO_TRADE`.
- **Evolved Criteria**:
  - Requires pre-market gap $\ge \pm 0.30\%$ on `SPY`.
  - Directional confirmation from `QQQ`.
  - Prior-day session close above/below VWAP with positive/negative Close Location Value (CLV).
  - Dual confirmation across economic calendar surprises, options positioning skew, and intraday continuation archetype.
- **Curated Manifest ("Box of Data")**:
  - *Included Newsletters*: Filtered down to 2 top narrative senders (`Sherwood News`, `Chartr`), pruning 13 lower-signal senders.
  - *Macro Proxies*: High-beta benchmarks (`QQQ`, `IWM`), while pruning FX currency noise (`UUP`).
  - *Indicator Features*: Synthetic morning newsletter briefing, options derivatives, high-impact economic calendar, and prior session intraday profile. Pruned qualitative market feeling and market health barometer.

## Supabase Promotion & Track Isolation

Winning local baselines can be promoted to the production daily predictor arena without mutating any existing models:
- **Track Isolation**: Stored strictly under `track_id = 'jev-local-autoresearched'` in `prompt_experiments`.
- **Active Demotion**: Demotes prior active records for `jev-local-autoresearched` to `saved`, leaving all other model tracks (`deepseek-v4-flash`, `MiniMax-M3`, `~typesafe/jev-latest`, and sector predictors) 100% untouched.

## CLI Usage

```bash
# Check if Strata server is alive on port 8080
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --check-strata --strata-url http://localhost:8080/v1

# Initialize or refresh the local feature cache from Supabase
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --init-cache --limit-cache-days 90

# Run 20 iterations
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --iterations 20 --strata-url http://localhost:8080/v1

# Dry run promotion to Supabase (prints exact payload and criteria without DB write)
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --promote-best --dry-run

# Promote champion to remote Supabase under track jev-local-autoresearched
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --promote-best
```


## Related

- [[entities/autoresearch]]
- [[entities/daily-market-predictor]]
- [[concepts/risk-adjusted-z-score]]
- [[concepts/multi-track-autoresearch]]
