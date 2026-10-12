---
tags: [autoresearch, pipeline, evaluation, local-optimization]
category: entity
---

# Local Autoresearch

The local autoresearch orchestrator runs iterative prompt/manifest tournaments to evolve Jev trading strategies. It operates in two phases: an initial development phase on a ~115-day Supabase-backed dataset, and a subsequent 2-year multi-regime arena (October 2024–October 2026) evaluated via zero-lookahead caching.

## Key Components

- **Tournament Orchestrator**: 100-iteration default loop with vault enforcement, baseline calibration, and multi-seed archetype support.
- **Baseline Management**: Active baseline stored under `track_id = 'jev-local-autoresearched'` in `prompt_experiments`. Winning local baselines can be promoted to the production daily predictor arena under the same track. Active demotion of prior records for `jev-local-autoresearched` to `saved` occurs, leaving all other model tracks untouched.

## Historical Raw Vault & Zero-Lookahead Downloader

To expand beyond the ~115 trading days in Supabase without hitting live API rate limits:
- **`historical_downloader.py`**:
  - Bulk downloads FMP EOD bars for SPY and 8 macro proxies (`QQQ`, `DIA`, `IWM`, `TLT`, `IEF`, `GLD`, `USO`, `UUP`).
  - Bulk downloads Polygon 5-min bars for key proxies (`SPY`, `QQQ`, `IWM`, `TLT`) with 12.5s pacing and 65s retry backoff on 429 rate limit errors.
  - Ingests 8,100+ raw Gmail financial newsletters from 2021–2026 via IMAP SSL.
  - Downloads point-in-time Polygon reference news and FRED macroeconomic series (`DGS10`, `DGS2`, `T10Y2Y`, `FEDFUNDS`, `UNRATE`, `ICSA`) into `.historical_raw.db`.
  - Rate-limited via `TokenBucketLimiter` (Polygon 1 req/12.5s, FMP 2.0s).
- **Zero-Lookahead Materializer (`cache_builder.py:build_cache_from_raw_db`)**:
  - Compiles raw records into `.local_autoresearch_cache.db`.
  - Enforces a strict 09:15 AM ET (13:15 UTC) cutoff on all morning news, newsletters, and pre-market bars.
  - Compiles `economic_calendar` from point-in-time FRED observations (10Y/2Y yields, yield curve spread, Fed Funds rate, Initial Jobless Claims).
  - Materializes multi-proxy premarket gaps (`SPY`, `QQQ`, `IWM`, `TLT`), prior session VWAP/CLV profiles, and synthetic newsletter digests.
  - For historical days prior to mid-2024, pre-market price quotes are strictly omitted; regular 09:30 AM open prices are **never** passed into feature context.
- **Dual-Track Regime Vault**:
  - *Primary Arena (2024–2026, ~500 days)*: High-resolution 09:15 AM ET pre-market tape + prior session technicals + morning news.
  - *Regime Vault (2021–2024, ~800+ days)*: Out-of-distribution stress testing across prior regimes using pure macro/narrative setups.

## Baseline Calibration & Multi-Regime Normalization

When transitioning from the initial 115-day development dataset (April–October 2026) to the **507-day 2-year multi-regime arena** (October 2024–October 2026), an evaluation calibration mismatch was observed:
- **Incumbent Champion (`qwen-jev-243de1`)**: Recorded a score of **80.43** on the homogeneous 115-day slice. When dynamically evaluated on the full 507-day 2-year active weeks, its true normalized performance is **50.19** (Train: 40.72, Test: 50.19).
- **Outperforming Mutations**: During tournament search on the 2-year tape, Iteration 9 mutation `qwen-jev-cc6ae6` achieved **51.69** and Iteration 11 mutation `qwen-jev-b779e3` achieved **51.18**, proving that tightened pre-market mechanical confirmation stacks (SPY gap >= 0.30%, QQQ confirmation, VWAP/CLV continuation, and dual risk-on/off triggers) outperform the original champion across 2 years of macro shocks.
- **Dynamic Calibration (`--calibrate-baseline`)**: To avoid comparing candidates against a stale watermark from a different dataset slice, `--calibrate-baseline` forces the runner to re-evaluate the active baseline across the current active weeks pool, updating the local store with a calibrated watermark.

## Multi-Seed Search Archetypes (Avoiding Local Optima)

Sequential mutation from a single champion risks getting trapped in local optima (e.g. minor variations around a 0.30% gap and 60% confidence). To explore disjoint regions of the prompt and manifest design space, the orchestrator supports multi-seed quantitative archetypes (`--seed-archetype`):

| Archetype | Core Hypothesis | Features Included |
| :--- | :--- | :--- |
| `clean-sheet` | Bare format blocks, zero trading rules. Lets Qwen build strategy from first principles. | Basic OHLC + Newsletters |
| `mean-reversion` | Extreme overnight gaps (>= 0.40%) tend to fill after open unless confirmed by macro yields and volume. | SPY, QQQ, IWM, TLT, Options, Intraday VWAP |
| `macro-rates` | 10Y/2Y Treasury yield shifts (TLT/IEF) and 8:30 AM economic surprises drive directional equity regimes. | QQQ, TLT, IEF, GLD, Economic Calendar, Options |
| `momentum-breadth` | Pre-market Gap & Go momentum confirmed by tech (QQQ) and small-cap (IWM) breadth. | QQQ, IWM, DIA, Intraday VWAP/CLV, Options |

Each archetype can be executed into an isolated local SQLite vault (e.g. `.local_autoresearch_meanrev.db`) to cultivate independent evolutionary lineages.

## CLI Usage

```bash
# 1. Download multi-year historical data into local raw SQLite vault
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.historical_downloader \
  --start-date 2024-10-01 --end-date 2026-10-10 --include-news --include-newsletters

# 2. Compile raw data into zero-lookahead feature cache (Primary Arena)
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --build-historical-cache --start-date 2024-10-01 --end-date 2026-10-10

# 3. Compile held-out Regime Vault cache (2021-2024, no pre-market tape leakage)
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --build-historical-cache --regime-vault --vault-cache-db .regime_vault_cache.db \
  --start-date 2021-02-15 --end-date 2024-09-30

# 4. Calibrate baseline and run 100-iteration tournament from calibrated champion
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --iterations 100 --calibrate-baseline --strata-url http://localhost:8080/v1

# 5. Launch a 100-iteration tournament starting from a specific quantitative archetype seed
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --iterations 100 --seed-archetype mean-reversion --local-db .local_autoresearch_meanrev.db \
  --strata-url http://localhost:8080/v1

# 6. Evaluate winning champion against held-out Regime Vault
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --eval-vault --vault-cache-db .regime_vault_cache.db

# 7. Promote champion to remote Supabase under track jev-local-autoresearched
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --promote-best
```
