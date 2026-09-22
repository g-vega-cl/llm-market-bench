---
tags: [analytics, intraday, market-profile, tool]
category: entity
---

# Intraday Movement Profile

Deterministic quantitative session profile and hourly price-action tape matrix for regular trading hours (09:30–16:00 ET). Decomposes price action into OHLC, True Intraday Return, VWAP, Close Location Value (CLV), Initial Balance breakout, and session archetype — all computed server-side with zero LLM token cost.

## Location

`apps/engine/analytics/intraday_profile.py`

## Core Functions

- **`filter_regular_trading_hours(bars)`** — Strips pre-market and after-hours bars, returning only 09:30:00–16:00:00 ET sorted bars.
- **`calculate_intraday_metrics(rth_bars)`** — Computes session metrics and classifies archetype.
- **`build_hourly_tape_matrix(rth_bars)`** — Generates an ASCII table with time, open→close, hourly change %, volume (M), and a 10-slot range map `[L...O...C...H]`.
- **`format_intraday_movement_markdown(ticker, date_str, metrics, rth_bars)`** — Formats the full report as clean Markdown.
- **`get_intraday_movement_report(ticker, date_str, include_hourly_tape)`** — Async entry point that fetches hourly bars via `MarketDataManager`, filters RTH, computes metrics, and returns a dict with `ticker`, `date`, `metrics`, and `markdown`.

## Session Metrics

| Metric | Description |
|--------|-------------|
| `open`, `high`, `low`, `close` | OHLC of the regular session |
| `range`, `range_pct` | Absolute and percentage range vs open |
| `intraday_return_pct` | (Close − Open) / Open × 100 |
| `clv` | Close Location Value in [-1.0, +1.0] |
| `vwap` | Volume-Weighted Average Price |
| `ib_high`, `ib_low` | Initial Balance (09:30–10:30 ET) high/low |
| `ib_broken` | Whether price broke IB high, low, both, or neither |
| `archetype` | Classified session archetype (see below) |
| `bar_count` | Number of RTH bars used |

## Session Archetypes

- **TREND_DAY_UP** — Sustained bull momentum, high IB extension, close near session high (CLV > 0.6).
- **TREND_DAY_DOWN** — Sustained bear momentum, low IB extension, close near session low (CLV < -0.6).
- **MORNING_DIP_AND_RIP** — Early selloff below open/IB low, followed by strong reclaim closing green.
- **GAP_AND_CRAP** — Early surge above open/IB high, followed by rollover closing red.
- **RANGE_BOUND_CHURN** — Tight range within or near Initial Balance, close near midpoint.

## Integration

### Tool Registration

Registered as `get_intraday_movement_profile` in the canonical tool registry (`CANONICAL_TOOLS_REGISTRY` in `core/llm/tools.py`) and in `packages/config/tools.json`. The tool accepts optional parameters:
- `ticker` (default `"SPY"`)
- `date` (ISO format, `"latest_completed"`, or `"yesterday"`; defaults to `"latest_completed"`)
- `include_hourly_tape` (boolean, default `true`)

### Daily Predictor Context Injection

Automatically injected into the daily S&P predictor's pre-market context via `get_daily_market_context()` in `tasks/daily_predictor.py`. The prior session's intraday movement profile (without hourly tape) is appended to the technical indicators section, giving the LLM a zero-token-cost summary of how the previous regular session behaved.

### Autoresearch Program

Listed as tool #44 in `autoresearch/program.md` and included in the researcher's tool enumeration in `autoresearch/researcher.py`.

## Related

- [[entities/daily-market-predictor]] — consumes intraday profile as pre-injected context
- [[entities/tool-registry]] — canonical tool registration
- [[entities/engine]] — Python data engine
- [[concepts/zero-frontend-compute]] — all heavy computation pre-materialized in background pipelines
