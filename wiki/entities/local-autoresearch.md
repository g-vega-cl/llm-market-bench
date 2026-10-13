---
tags: [autoresearch, pipeline, evaluation, local-optimization]
category: entity
---

# Local Autoresearch

The local autoresearch orchestrator runs iterative prompt/manifest tournaments to evolve Jev trading strategies. It operates in two phases: an initial development phase on a ~115-day Supabase-backed dataset, and a subsequent 2-year multi-regime arena (October 2024–October 2026) evaluated via zero-lookahead caching.

## Key Components

- **Tournament Orchestrator**: 100-iteration default loop with vault enforcement, baseline calibration, and multi-seed archetype support.
- **Baseline Management**: Active baseline stored under `track_id = 'jev-local-autoresearched'` in `prompt_experiments`. Winning local baselines can be promoted to the production daily predictor arena under the same track. Active demotion of prior records for `jev-local-autoresearched` to `saved` occurs, leaving all other model tracks untouched.
- **Pure Directional Evaluation**: Uses [[concepts/pure-directional-scoring]] to evaluate binary direction models without artificial intraday hit assumptions:
  $$\text{Score} = (0.65 \times \text{Traded Win Rate}) + (0.25 \times \text{Close Accuracy}) + (0.10 \times \text{Selectivity}) - (\text{Mean Brier} \times 20.0)$$
  Eliminates dummy intraday hit artifacts and directly rewards disciplined confidence gating.


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

When transitioning from the initial 115-day development dataset (April–October 2026) to the **507-day 2-year multi-regime arena** (October 2024–October 2026) under [[concepts/pure-directional-scoring]]:
- **Calibrated Baseline**: Re-evaluating the prior champion `qwen-jev-27e3a6` yielded a calibrated score of **55.98** across the 85 active optimization weeks (404 trading sessions, 21 weeks held out in vault).
- **Discovered Champion (`qwen-jev-9b7a55`)**: Discovered on Iteration 9 of Batch 1:
  - **Effective Score**: **59.41** (+3.43 improvement over calibrated baseline).
  - **Overfit Penalty**: **0.0%** (Train: 42.98%, Test: 59.41%), demonstrating zero memorization and true held-out out-of-sample edge.
  - **Confidence Gate**: Filter threshold set at `min_confidence = 62.0%`.
  - **Mechanical Confirmation Rules**: Requires SPY overnight gap $\ge \pm 0.30\%$ confirmed by QQQ gap in the same direction by $\ge \pm 0.15\%$, prior session SPY close relative to VWAP with positive/negative CLV, plus either candle archetype continuation or two independent risk-on/off triggers from economic surprises and options skew.
  - **Pruned Manifest**: Pruned synthetic narrative commentary and currency noise (`UUP`), retaining only mechanical newsletters (`Sherwood News`, `Chartr`), pre-market proxies (`QQQ`, `IWM`), options skew, FRED economic prints, and prior intraday technical profiles.


## 10-Batch Tournament Curriculum & Grand Champion

To eliminate local optima traps, the tournament was executed across 10 distinct quantitative archetype seeds (30 iterations each, totaling **300 iterations** across 404 active sessions and 106 calendar weeks):

| Batch | Archetype Key | Champion Variant | Pure Directional Score | Overfit Penalty | Primary Feature Focus |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **Batch 1** | `mean-reversion` | `qwen-jev-e0c4c5` | **58.38** | 0.0% | Fades extreme unconfirmed gaps ($\ge \pm 0.45\%$) |
| **Batch 2** | `macro-rates` | `qwen-jev-4a034d` | **58.26** | 0.0% | 10Y/2Y yields (`TLT`/`IEF`) & 8:30 AM economic surprises |
| **Batch 3** | `momentum-breadth` | `qwen-jev-2a50aa` | **54.47** | 0.0% | Gap & Go momentum with `QQQ` & `IWM` breadth |
| **Batch 4** | `volatility-skew` | `qwen-jev-e57394` | **54.65** | 0.0% | Options put/call volume distribution & delta skew |
| **Batch 5** | `opening-drive` | `qwen-jev-de9469` | **57.08** | 0.0% | Institutional CLV/VWAP value migration |
| **Batch 6** | `cross-asset-flight` | `qwen-jev-bc8dc3` | **57.19** | 0.0% | Equity vs Treasuries vs Gold safe-haven flight |
| **Batch 7** | `trend-exhaustion` | `qwen-jev-ad283a` | **56.18** | 0.0% | Fades multi-day extended directional momentum |
| **Batch 8** | `selective-catalyst` | `qwen-jev-df4d78` | **54.28** | 0.0% | High-impact 8:30 AM economic prints (strict gating) |
| **Batch 9** | `contrarian-sentiment` | `qwen-jev-d723b5` | **59.72** 🏆🥇 | 0.0% | Fades retail sentiment extremes when tape diverges |
| **Batch 10** | `clean-sheet` | `qwen-jev-ae23a2` | **57.45** | 0.0% | Unconstrained first-principles evolution |

### The Grand Champion: `qwen-jev-d723b5` (Score: 59.72)

Discovered in Batch 9, `qwen-jev-d723b5` achieved the highest score across all 300+ iterations evaluated:
- **Effective Score**: **59.72** (Train: 45.71%, Out-of-sample Test: **59.72%**, Overfit Penalty: **0.0%**).
- **Confidence Gate**: Filter threshold set at `min_confidence = 58.0%`.
- **Bounded Gap Hurdle**: Gaps must lie strictly within **$\pm 0.15\%$ and $\pm 0.65\%$**, effectively filtering flat chop ($<0.15\%$) while avoiding unhedged black-swan open anomalies ($>0.65\%$).
- **Confirmation Logic**:
  - *UP Call*: SPY overnight gap is negative (-0.15% to -0.65%) with QQQ equal or more negative, but prior session closed above VWAP with positive CLV and constructive candle archetype, and no catastrophic downside economic surprise.
  - *DOWN Call*: SPY overnight gap is positive (+0.15% to +0.65%) with QQQ equal or more positive, but prior session closed below VWAP with negative CLV and weak candle archetype, and no upside economic shock.
- **Zero-Narrative Manifest**: Qwen discovered that completely pruning all 15 newsletters (`selected_newsletters: []`) and all synthetic commentary eliminated conflicting qualitative noise, leaving a pure mechanical stack: `QQQ` pre-market tape, prior session VWAP/CLV intraday technicals, and FRED economic calendar safety checks.

## Locked Vault Stress Test & Post-Mortem

When evaluating the 10 batch winners out-of-distribution across the **21 sequestered Locked Vault weeks (103 trading days)**, a major failure mode was revealed:
- `qwen-jev-d723b5` (Batch 9 Champion) collapsed from **59.72** active score down to **40.11** vault score, trading 102/103 days with only **43.1% win rate** (worse than random).
- The gap-fading heuristic failed in persistent trend regimes, repeatedly calling DOWN on morning green opens with only 33.3% accuracy.
- Conversely, `qwen-jev-ad283a` (Batch 7: `trend-exhaustion`) demonstrated robust out-of-distribution generalization, achieving **55.6% win rate** and a **52.20 vault score** by filtering out 30 low-conviction days via strict confidence gating.
- For detailed root-cause forensics on market efficiency limits, information horizon asymmetry, and the selectivity scoring trap, see [[concepts/daily-directional-predictability-limits]].



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

# 8. Run Strata (Qwen) + Laya Double-Ratchet Tournament (see [[concepts/strata-laya-double-ratchet]])
# Uses --no-cache to enforce fresh daily briefings per session day (mirrors live 9:15 AM ET execution)
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --double-ratchet --iterations 10 --no-cache --cache-db .local_autoresearch_cache.db
```
