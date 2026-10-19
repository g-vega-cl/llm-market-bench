---
tags: [analytics, trend, momentum, zero-lookahead, technicals]
category: concept
---

# Trend Profile (Multi-Day Momentum Vector)

`analytics/trend_profile.py` computes point-in-time multi-day technical trend features strictly from verified historical prices. It is the single source of truth for the "Multi-Day Momentum & Trend Vector" block injected into predictor prompts, replacing ad-hoc inline SMA/return calculations.

## Guarantees

- **Zero lookahead** — any bar whose date is on or after `target_date` is filtered out before computation, so a pre-market run never sees the current session's close.
- **Zero hallucination** — indicators are strictly `None` when there is insufficient history. `sma_20` requires ≥ 20 completed bars; `return_5d_pct` requires ≥ 5 bars. No partial-window SMA is ever fabricated.

## Metrics

`compute_trend_profile(history, target_date)` returns a `TrendProfile` dataclass with:

- `prior_date` / `prior_close` — the most recent verified session close strictly before the target date.
- `return_5d_pct` — rolling 5-day return (weekly cycle).
- `sma_20` / `sma_20_dist_pct` — 20-day Simple Moving Average and the prior close's distance from it (monthly cycle).
- `sequence_3d` — 3-day direction sequence, e.g. `UP (+0.3%) -> DOWN (-0.2%) -> UP (+0.6%)`.
- `bars_used` and a pre-rendered `summary` / `summary_lines` block for prompt injection.

`as_dict()` serializes the profile into the structured `data_record["trend_vector"]` for downstream curation.

## Consumers

- **Daily market predictor** — `get_structured_daily_market_context` fetches 45 days of history, computes the profile, appends `summary_lines` to the context, and stores `trend_vector` in the data record (see [[entities/daily-market-predictor]]).
- **Bond predictor** — `construct_lean_bond_prompt` and `compile_jev_bond_context` accept a `trend_summary` and inject it as "Trend & Multi-Day Momentum" (see [[entities/daily-bond-trading]]).
- **Local autoresearch** — `pack_daily_context` gates the block behind `DataManifest.include_trend_vector` (default `True`), and `format_raw_point_in_time_inputs` falls back to `day_record["trend_vector"]["summary"]` when the cache DB is absent.

## Related

- [[concepts/zero-lookahead-materialization]]
- [[entities/daily-market-predictor]]
- [[entities/daily-bond-trading]]
- [[concepts/curated-data-manifest]]
