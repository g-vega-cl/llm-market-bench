---
tags: [earnings, pead, sue, bellwethers, analytics, engine]
category: entity
---

# Earnings Alpha Analytics

The Earnings Alpha subsystem in the engine computes Post-Earnings Announcement Drift (PEAD), Standardized Unexpected Earnings (SUE), Sloan accrual quality, analyst revision momentum, and sector bellwether diffusion across the S&P 500 universe.

## Core Analytics

- `calculate_sue` in `apps/engine/analytics/earnings_alpha.py` — SUE = (Actual EPS - Estimated EPS) / StdDev(historical surprises). Uses trailing up-to-8-quarter surprise history, flags top-decile SUE >= +2.0 with a positive surprise, requires at least 4 quarters of history, and applies an epsilon guard for zero variance.
- `calculate_sloan_accrual_quality` — (Net Income - Operating Cash Flow) / Total Assets; clean when <= +0.10.
- `calculate_post_earnings_drift` — drift % and SPY-benchmarked alpha after an earnings print.
- `check_pre_earnings_runup` — flags extreme parabolic moves (>25% in 20 days) before the announcement.
- `apps/engine/analytics/bellwether_classifier.py` — classifies sector constituents: top 5 by market cap reporting within the first 14 days of the reporting cycle become `EARLY_BELLWETHER`; the rest are `DOWNSTREAM_PEER`. It also evaluates the 14-day active signal window and cap-weighted operating margin surprise delta.

## Pipeline & Storage

- `apps/engine/scripts/update_earnings_alpha.py` — daily batch fetch from FMP `/stable/earnings`, key metrics, analyst consensus, price targets, and quotes; computes snapshot fields; upserts into `earnings_alpha_snapshots` on `(snapshot_date, ticker)`.
- `sector_bellwether_signals` table stores per-constituent classification, report status, and active signal state.
- `.github/workflows/update-earnings-alpha.yml` runs the script at 10:30 and 21:30 UTC on weekdays.

## LLM Tools

Three canonical tools are registered in `apps/engine/core/llm/tools.py` and dispatch through `execute_tool` to `apps/engine/tools/earnings_alpha_tools.py`:

- `get_pead_candidates(sector?, min_sue=2.0, limit=15)` — queries Supabase snapshots for top-decile candidates.
- `get_earnings_revisions(ticker)` — FMP analyst consensus, buy/hold/sell distribution, and price target upside.
- `get_sector_bellwethers(sector)` — active reported bellwether signals and upcoming unannounced peers.

## Related

- [[concepts/earnings-prediction-strategies]]
- [[entities/earnings-audit]]
- [[entities/tool-registry]]
- [[entities/database]]
- [[entities/engine]]
- [[entities/pipeline]]
