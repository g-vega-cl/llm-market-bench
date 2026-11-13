---
tags: [macro, treasury, yield-curve, regime, fred, fmp, sector-predictor]
category: concept
---

# Yield Curve Regime Classification

`apps/engine/analytics/yield_curve.py` classifies the US Treasury term structure into a monetary-policy regime and renders it as a Markdown block for agent prompts. It reads the full curve (3M, 2Y, 5Y, 10Y, 30Y), derives the key spreads, and maps the shape plus its recent drift onto one of four actionable regimes — or an explicit `UNAVAILABLE` state when the data cannot support a classification.

## Regimes

`YieldCurveRegime` is a `StrEnum`:

| Regime | Meaning | Factor tailwinds (excerpt) |
| :--- | :--- | :--- |
| `BULL_STEEPENER` | Yields falling, long end falling faster — easing / growth re-acceleration | Growth, small caps, long duration |
| `BEAR_STEEPENER` | Yields rising, long end rising faster — reflation / term-premium expansion | Cyclicals, commodities, banks |
| `BULL_FLATTENER` | Yields falling, short end falling faster — late-cycle easing | Defensives, quality, duration |
| `BEAR_FLATTENER` | Yields rising, short end rising faster — hawkish Fed / tightening | Cash, short-duration Treasuries (`SHV`), defensives |
| `UNAVAILABLE` | Insufficient or missing curve data — no classification is asserted | *(empty)* |

`FACTOR_TAILWINDS` and `FACTOR_HEADWINDS` map each regime to sector/asset lists. `UNAVAILABLE` maps to empty lists so no fabricated rotation advice ever reaches a prompt.

## Classification

`classify_yield_curve_regime(history)` sorts the daily rows by date and uses the latest two observations:

- **Spreads** — `spread_10y_2y_bps`, `spread_10y_3m_bps`, `spread_30y_5y_bps`, each `round((long − short) × 100, 1)`.
- **5-day delta** — `spread_10y_2y_5d_delta_bps`, the change in the 10Y-2Y spread between the latest and prior observation.
- **Yield level direction** — `RISING` / `FALLING` / `NEUTRAL` from the level move.
- **Regime** — the spread sign (inverted vs normal) combined with the spread delta (steepening vs flattening) and the level direction.

## Missing-Data Discipline

The classifier never coerces a missing tenor to zero. Three helpers enforce this:

- `_opt_float(row, key)` returns `None` for missing, empty, or unparseable values instead of `0.0`.
- `_spread_bps(long_val, short_val)` returns `None` unless **both** tenors are present, so a missing 3M or 30Y yield yields a `None` spread rather than a fake one.
- `_format_bps(val)` renders `` `+30.0 bps` `` for numbers and `` `N/A` `` for `None`.

Rows lacking `year10` or `year2` are filtered out before classification (`valid_rows`), because those two tenors are the minimum needed for a spread-based regime call.

## UNAVAILABLE State

`classify_yield_curve_regime` returns the `UNAVAILABLE` payload in two cases:

1. **No valid rows** — empty history, or every row missing `year10`/`year2`. All spreads are `None`, `yield_level_direction` is `UNAVAILABLE`, and both factor lists are empty.
2. **Fewer than two valid observations** — a single point can produce spreads but no 5-day delta, so no regime is asserted. Spreads that *are* computable are still returned.

`format_yield_curve_regime_markdown` renders `N/A` for missing spreads and `N/A (insufficient data)` for empty tailwind/headwind lists, so a degraded report is visibly degraded rather than silently neutral.

## Data Sources & Fallback Chain

`get_yield_curve_regime_report()` resolves the curve through an ordered chain and stamps the result with a `source` field:

1. **FMP** — `GET https://financialmodelingprep.com/stable/treasury-rates` when `FMP_API_KEY` is set. A 200 response with a non-empty list is classified and returned with `source = "FMP"`.
2. **FRED** — `_fetch_fred_yield_history()` fans out over the `treasury_3m`, `treasury_2y`, `treasury_5y`, `treasury_10y`, and `treasury_30y` aliases via `fetch_fred_series_observations(..., lookback_periods=10)` using `asyncio.gather(..., return_exceptions=True)`. Observations are pivoted into per-date rows keyed by `month3` / `year2` / `year5` / `year10` / `year30`, and only dates carrying **both** `year10` and `year2` are retained. Two or more aligned dates are required; the result carries `source = "FRED"`.
3. **None** — when both feeds fail, the `UNAVAILABLE` payload is returned with `source = "NONE"`.

A missing `FMP_API_KEY` is logged at info level and falls straight through to FRED rather than returning a neutral default. Every failure path uses `logger.exception` so the traceback survives.

The curated macro dashboard (`get_curated_macro_dashboard` in `apps/engine/core/fred.py`) fetches 10 observations per indicator instead of 3, so its shared `treasury_10y` / `treasury_2y` cache entries satisfy the yield-curve alignment requirement. See [[concepts/macroeconomic-data-fred]].

## Consumers

- **Sector predictor** — `_build_sector_macro_context()` in `apps/engine/tasks/sector_predictor.py` injects the rendered Markdown into every horizon prompt, but only when `source != "NONE"` **and** `regime != "UNAVAILABLE"`, so a degraded curve never masquerades as a regime call. See [[entities/sector-predictor-arena]].
- **Bond predictor** — reasons over the curve for `TLT` duration trades (see [[entities/bond-predictor]]).
- **Agent tool** — `get_yield_curve_regime` exposes the same classification to pull-based trading agents (see [[entities/tool-registry]]).
- **Treasury tool** — `get_treasury_yield_curve` reports the raw tenor snapshot and spreads (see [[entities/treasury-yield-curve-tool]]).

## Tests

`apps/engine/tests/test_fsi_analytical_tools.py` covers the FRED fallback (`test_get_yield_curve_regime_report_falls_back_to_fred`, asserting `BULL_STEEPENER`, `+30.0` bps 10Y-2Y, `+10.0` bps 10Y-3M, `FALLING`, `source == "FRED"`) and the missing-tenor / empty-history behavior (`test_classify_yield_curve_regime_handles_missing_tenors_and_empty_history`). `apps/engine/tests/test_sector_predictor.py` asserts the macro context is injected and that an `UNAVAILABLE` curve is omitted.

## Related

- [[concepts/macroeconomic-data-fred]] — the FRED series layer and alias map
- [[entities/treasury-yield-curve-tool]] — raw tenor snapshot tool
- [[entities/bond-predictor]] — primary duration consumer
- [[entities/sector-predictor-arena]] — injects the regime into every horizon prompt
- [[concepts/anthropic-fs-insights]] — the `get_yield_curve_regime` tool design
