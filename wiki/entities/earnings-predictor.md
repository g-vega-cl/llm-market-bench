---
tags: [entity, earnings, predictor, openai, discovery, fmp]
category: entity
---

# Earnings Predictor

`apps/engine/tasks/earnings_predictor.py` generates directional earnings
predictions for candidate tickers using an OpenAI reasoning model, DeepSeek
Flash, and TypeSafe Jev. It first discovers which companies are reporting, then
runs the day-1 movement arena over the discovered candidates.

## Candidate Discovery

`discover_earnings_candidates(target_date_str, ticker=None, limit=5)` resolves the
list of reporting companies through a layered strategy. **SPY is an ETF and never
reports quarterly earnings**, so a `ticker` of `SPY` (or `None`) is treated as
"auto-discover" rather than a literal filter.

1. **Explicit ticker** — when a non-`SPY` ticker is supplied, the function queries
   `earnings_alpha_snapshots` filtered to that ticker (ordered by
   `snapshot_date` descending) and returns the matching rows.
2. **Supabase snapshot window** — with no explicit ticker, it queries
   `earnings_alpha_snapshots` for rows whose `report_date` falls within the last
   **5 days** of the target date (covering weekends), ordered by `report_date`
   then `sue_score` descending. `SPY` rows and duplicate tickers are filtered out
   via a `seen_tickers` set, and the query over-fetches (`limit * 3`) so the
   post-filter still yields up to `limit` candidates.
3. **FMP live earnings calendar fallback** — if fewer than `limit` candidates are
   found and `FMP_API_KEY` is set, it calls
   `https://financialmodelingprep.com/stable/earnings-calendar` for the target
   date. Entries are kept only when they have a symbol (not `SPY`), are not
   already seen, and carry an `epsEstimated` or `epsActual`. They are sorted by
   estimated revenue descending and mapped into the snapshot shape:
   - `report_timing` is `BMO` when `epsActual` is present, else `AMC`.
   - `eps_surprise` = `actual_eps - estimated_eps` when both exist.
   - `revenue_surprise_pct` = `(actual - estimated) / estimated * 100` when both
     exist and estimated revenue is positive.
   - `sue_score` / `is_top_decile_sue` are set from a positive EPS surprise.
   - `is_sloan_accrual_clean` defaults to `True`, `analyst_consensus` to
     `"Moderate Buy"`, and `target_consensus_upside_pct` to `10.0`.
4. **Static fallback** — if both the database and calendar are empty, a single
   sample candidate is returned (the explicit ticker when supplied, otherwise
   `NVDA`).

## CLI

`handle_earnings_predictor` in `apps/engine/cli/predictions.py` normalizes the
`--ticker` argument before dispatch: a raw value of `SPY` (case-insensitive) is
converted to `None` so the default `SPY` never forces a literal SPY lookup and
automatic discovery of actual reporting stocks proceeds.

## Luna Prediction Path

`predict_with_luna` calls the OpenAI client with
`response_model=EarningsPredictionOutput` for structured output. The call passes
`reasoning_effort="none"` — the reasoning models reject structured-output
requests that specify a non-`none` reasoning effort with a 400 error, so the
effort is disabled for this extraction step.

## Related

- [[entities/earnings-alpha]]
- [[entities/earnings-audit]]
- [[concepts/earnings-prediction-strategies]]
- [[entities/cli]]
