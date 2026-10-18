---
tags: [entity, postmortem, analysis, daily-predictor, feedback-loop]
category: entity
---

# Daily Post-Mortem

`apps/engine/analysis/daily_postmortem.py` — the feedback phase of the daily
predictor loop. After the session closes, every daily prediction is audited
against the actual intraday tape and the verified evening market brief, and the
resulting lesson is written back into agent memory.

## Entry Point

`run_daily_postmortem(target_date, force=False, client=None, luna_client=None)`

1. Loads all `daily_predictions` rows for `target_date` that still lack a
   post-mortem. If none are pending (and `force` is false) it logs and returns
   an empty list.
2. Fetches the evening newsletter summary once via
   `fetch_evening_newsletter_summary(sb, target_date)`.
3. Iterates the pending predictions, resolving the ticker per prediction
   (`pred.get("ticker", "SPY")`) and fetching that ticker's regular-trading-hours
   bars through `fetch_rth_bars_for_date(ticker, target_date)`.
4. Calls `diagnose_daily_prediction(...)` for each prediction and persists the
   diagnosis back onto the prediction row.

### Per-Ticker RTH Bar Cache

A single post-mortem run can span multiple tickers (SPY and TLT predictions are
audited in the same batch). RTH bars are memoized in a local
`rth_bars_by_ticker: dict[str, list[dict]]` so each distinct ticker is fetched
at most once per run, while every prediction is still diagnosed against *its
own* ticker's tape. Previously the batch assumed a single ticker taken from the
first pending prediction, which silently graded TLT predictions against SPY
bars.

## Diagnosis

`diagnose_daily_prediction(prediction, rth_bars, close_newsletter, ...)` builds a
system prompt that frames the model as an elite quantitative post-mortem analyst
auditing an intraday forecast, then asks for a structured
`DailyPredictionDiagnosis`.

The audited asset is named explicitly in the prompt via an `asset_label`
derived from the prediction's ticker:

| Ticker | Label |
| :--- | :--- |
| `TLT` | `20+ Year Treasury Bond ETF (TLT)` |
| `SPY` | `S&P 500 (SPY)` |
| other | the raw ticker symbol |

This keeps the analyst anchored to the correct instrument instead of assuming
every forecast is an S&P 500 call.

### Anti-Hallucination Rules

The prompt enforces ground-truth-only reasoning: no invented macro excuses or
narratives. Every claimed driver must be citable from the verified evening
market brief or the hourly price tape.

### Output Shape

`DailyPredictionDiagnosis` carries:

- `category` — a `PostMortemCategory` (e.g. `ACCURATE_CAPTURE`)
- `was_predictable` — whether the move was knowable from available evidence
- `observed_driver` — the verified cause of the realized move
- `flawed_assumption` — what the prediction got wrong (`None` when accurate)
- `actionable_lesson` — the takeaway to feed forward

## Memory Feedback

When `was_predictable` is true, the lesson is written into agent memory via
`add_memory`. Unpredictable moves are recorded on the prediction row but are not
promoted into memory, so noise never becomes a learned rule.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-score-breakdown]]
- [[concepts/daily-postmortem-taxonomy]]
- [[concepts/memory-feedback]]
- [[concepts/daily-spy-live-trading]]
- [[concepts/daily-tlt-live-trading]]
