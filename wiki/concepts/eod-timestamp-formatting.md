---
tags: [date, formatting, timezone, eod, macro, frontend]
category: concept
---

# EOD Timestamp Formatting

A convention for distinguishing End-Of-Day (EOD) daily price bars from intraday quotes when rendering timestamps in the dashboard. EOD bars are stored with a midnight UTC timestamp (`YYYY-MM-DDT00:00:00+00:00`) or as a date-only string (`YYYY-MM-DD`). Naively converting those to Eastern Time produces a misleading "8:00 PM ET" label, so the frontend detects them and renders a calendar-close label instead.

## The Problem

Daily bars sourced from the market data provider carry a midnight UTC timestamp. When formatted with a standard Eastern Time formatter, midnight UTC becomes 8:00 PM ET (the previous evening), which reads as an intraday update time. This made the Today page's Global Macro Regime section claim "Last updated 8:00 PM ET" even though the value was simply the prior session's close.

## Detection

`isMidnightUtcOrDateOnly` in `apps/web/src/utils/date.ts` classifies a timestamp:

- A string without a `T` separator is treated as date-only → EOD.
- A string matching `T00:00:00` (optionally with `.000`, `+00:00`, or `Z`) is treated as a midnight UTC EOD bar.
- Anything else is a genuine intraday timestamp.

## Formatting

When a timestamp is classified as EOD, `formatEODDateClose` renders it as `Mon DD Close` (e.g. `Oct 21 Close`). It parses the date portion, anchors it at noon UTC to avoid off-by-one day shifts, and formats the month/day in `America/New_York`.

Intraday timestamps continue to use `formatEasternTime` / `formatEasternDateTime`. `computeMacroLastUpdated` in `fetch-today-data.ts` compares the timestamp's Eastern calendar date against today's Eastern date to decide between a time-only and a date+time rendering.

## Consumers

- `computeMacroStatistics` / `buildMacroStat` in `apps/web/src/features/today/api/fetch-today-data.ts` — sets `formattedTime` only for non-EOD timestamps, leaving it `undefined` for EOD bars.
- `calculateMacroStats` in `apps/web/src/features/today/lib/macro-tickers.ts` — same guard when deriving per-ticker display times.
- `computeMacroLastUpdated` — returns `formatEODDateClose` for EOD bars and `null` for unparseable timestamps.

## Backend Alignment

The engine side (`apps/engine/scripts/update_prices.py`) complements this by prioritizing live quotes in `compute_ticker_macro_metrics`: when a live quote is available it records the current UTC timestamp in `market_data_cache` rather than copying the provider's midnight EOD bar. When falling back to historical data, a midnight/date-only `fetched_at` is replaced with the current time so the cache never stores a synthetic EOD timestamp for a live value.

## Related

- [[entities/macro-tracker]] — the Global Macro Regime tracker that surfaces these timestamps
- [[entities/web-app]] — the dashboard consuming the formatters
- [[concepts/zero-frontend-compute]] — display-layer formatting conventions
