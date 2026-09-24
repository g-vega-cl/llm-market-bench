---
tags: [volume, rvol, market-data, execution, persistence]
category: concept
---

# Volume Context

Volume context is the volume-awareness layer the engine feeds to its volatility
and liquidity tooling. It answers a simple question — "is this session's
activity unusually heavy or light relative to recent history?" — producing the
relative-volume (RVOL) signal used when sizing positions, judging breakouts,
and scoring intraday setups.

## Relative Volume (RVOL)

RVOL compares a bar's volume against the average volume of the preceding
lookback window of EOD bars. Readings above 1 mean heavier-than-normal
participation, readings below 1 mean lighter-than-normal participation. Because
it is a ratio, it is only meaningful when volume is available for **both** the
current bar and the prior bars in the window.

## Storage: `price_history.volume`

Daily bars are served by `MarketDataManager.get_history`, which reads the
`price_history` table first and only falls back to a live provider fetch on a
cache miss. Volume is part of that stored bar: `price_history.volume` is a
`BIGINT` holding the daily share volume for the trading session (EOD bar),
defined by migration `20260924000000_add_volume_to_price_history.sql`.

Both retrieval paths carry volume end to end:

- **Cache hit** — the `SELECT` includes `volume`, and every returned bar dict
exposes it as an `int` (or `None` for legacy rows written before the column
existed).
- **Provider fetch** — the provider's per-bar `volume` is written into the
`price_history` upsert payload, so subsequent cache hits retain it.

With volume persisted and plumbed through, `compute_volume_context` and
`execute_volatility_metrics_tool` compute RVOL directly from the DB cache
instead of depending on live API fetches. When volume is missing from the
cache read/write path, those tools report "insufficient volume data" even
though the underlying history exists.

## Related

- [[entities/database]]
- [[entities/engine]]
- [[concepts/execution]]
- [[concepts/intraday-hit-metrics]]
