---
tags: [analytics, statistics, volatility, newsletter, reference, regime]
category: concept
---

# Multi-Horizon Reference & Statistical Regime Matrix

A statistical context layer that grounds every nominal price, yield, or level quoted in a generated newsletter against its own history. Implemented in `apps/engine/analytics/market_reference.py`, it answers the question *"is this number high or low, and is the move unusual?"* instead of leaving readers with an unanchored figure like "UUP is at $29.12".

## Why It Exists

A bare price carries no information. `$29.12` on UUP is meaningless without knowing whether it sits at the 99th percentile of its 52-week range, how far it is from its 20/50/200-day moving averages, whether the move is a statistical outlier, and whether realized volatility is compressing or expanding. Without that framing, newsletter prose reads as a data dump and the model has no basis for judging whether a level is stretched or ordinary.

This module closes that gap by pre-computing a dense reference profile per asset and injecting it into the newsletter synthesis prompt.

## Horizons

Three nested lookback windows are computed from daily EOD price bars:

| Horizon | Window | Metrics |
| :--- | :---: | :--- |
| **Tactical** | 20 days | min/max range, percentile rank, 20-day return, 20-DMA and distance from it |
| **Intermediate** | 60 days | min/max range, percentile rank, 60-day return, 50-DMA and distance from it |
| **Structural** | 252 days (52 weeks) | min/max range, percentile rank, 52-week return, 200-DMA and distance from it, 52-week Z-score |

Percentile rank is computed as the share of bars in the window at or below the current price, expressed 0–100. The 50-DMA requires at least 30 bars and the 200-DMA at least 120 bars before they are emitted; otherwise the field stays `None` and renders as `N/A`.

## Volatility Regime

Realized volatility is annualized from daily log-adjacent returns (`stdev * sqrt(252) * 100`) over both the trailing 20 days and the full available year. The ratio of the two classifies the regime:

- **Expanding** — 20d vol > 1.3× the 1-year vol
- **Compressed** — 20d vol < 0.75× the 1-year vol
- **Normal** — anything in between

When only the 20-day figure is available, the regime degrades to a bare percentage string.

## Regime Tags

The 52-week percentile maps to a qualitative positioning label:

| Percentile | Tag |
| :--- | :--- |
| ≥ 90 | Near 52W High (Top Decile) |
| ≥ 75 | Elevated (Upper Quartile) |
| > 25 and < 75 | Mid-Range Consolidation |
| ≤ 25 | Depressed (Lower Quartile) |
| ≤ 10 | Near 52W Low (Bottom Decile) |

## Zero-Lookahead Guarantee

`compute_multi_horizon_reference()` accepts an optional `target_date`. Any bar whose date is greater than or equal to that date is excluded before any statistic is computed. This makes historical and backfill newsletter runs point-in-time correct — a newsletter generated for a past session can never see prices from that session or later.

Bars with missing, non-numeric, `NaN`, or non-positive prices are dropped. Fewer than 3 valid bars returns `None` rather than a fabricated profile.

## Single-Stock Extraction

`extract_mentioned_single_stocks()` scans newsletter subjects and bodies for `$TICKER` and `(TICKER)` patterns, counts occurrences, and returns the top-N most-mentioned symbols. Two exclusion sets prevent noise:

- **Macro and benchmark tickers** — `SPY`, `QQQ`, `IWM`, `TLT`, `GLD`, `USO`, `UUP`, `EURUSD`, `USDJPY`, `BTC`, `VIX`, and similar proxies are already covered by the macro core list and are never treated as single stocks.
- **Common word collisions** — `CEO`, `ETF`, `IPO`, `FED`, `CPI`, `GDP`, `BUY`, `SELL`, `AI`, `US`, and roughly 70 other acronyms and English words that would otherwise be misread as tickers.

## Newsletter Integration

`get_newsletter_reference_context()` is the async entry point used by [[entities/generated-newsletters]]. It:

1. Builds the target list from a macro core set (`UUP`, `EURUSD`, `USDJPY`, `SPY`, `QQQ`, `TLT`, `GLD`, `USO`) plus the extracted single stocks, deduplicated.
2. Fetches pre-market quotes and 252-day histories concurrently via `asyncio.gather` with `return_exceptions=True`, so a single failing ticker cannot abort the batch.
3. Computes a profile per ticker and formats a Markdown table plus a bulleted highlight list.

The output is injected into the DeepSeek Flash prompt as `reference_context` under the heading `### 📊 Multi-Horizon Reference & Statistical Regime Matrix`. The newsletter system prompt carries a matching **Historical Reference & Statistical Context Mandate** instructing the model to never state a level in isolation, to always cite 52-week percentile, moving-average distance, Z-score/regime tag, and volatility regime, and to reproduce the reference table inside the Catalyst Radar section.

Failures are non-fatal: any exception during gathering logs a warning and returns an empty string, so newsletter generation proceeds without the reference block.

## Rendering

Two formatters exist:

- `format_reference_table()` — a Markdown table with columns Asset, Price, 1D Move, 52W Range (%-tile), 60D Move, 20D Move (vs 20-DMA), Vol Regime, Regime Tag.
- `MultiHorizonReferenceProfile.to_inline_summary()` — a compact one-line string for prose injection, e.g. `**UUP**: $29.12 (+0.42% today) | 52W: [$27.10 – $29.40] (99%-tile, +2.1σ, Near 52W High (Top Decile)) | 20D: +3.4% (+1.8% vs 20-DMA) | Vol: Compressed (6.2% vs 1Y 8.9%)`.

## Related

- [[entities/generated-newsletters]] — the consumer that injects this matrix into the briefing prompt
- [[entities/engine]] — the Python data engine hosting the analytics package
- [[concepts/ingestion]] — upstream newsletter ingestion feeding the chunk scanner
- [[concepts/fundamental-analysis]] — sibling context-enrichment layer for valuation metrics
