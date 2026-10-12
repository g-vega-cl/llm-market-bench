---
tags: [autoresearch, data-integrity, point-in-time, lookahead, cache]
category: concept
---

# Zero-Lookahead Materialization

`build_cache_from_raw_db` in `apps/engine/local_autoresearch/cache_builder.py` compiles rows from the raw vault ([[entities/historical-downloader]]) into training/test days with a hard **point-in-time contract**: every feature fed to the model is strictly timestamped at or before **09:15 AM ET (13:15 UTC)** on the target date. No post-open information can leak into the prompt.

## Temporal Window

For target date `T`, with prior session `T-1`:

- Prior-session technical profile — the `T-1` EOD bar (fully realized by 16:00 ET `T-1`), plus computed CLV and VWAP.
- News / newsletters — inclusive window `[T-1 20:00 UTC, T 13:15 UTC]` (i.e. `T-1 16:00 ET` to `T 09:15 ET`).
- Pre-market quotes — the latest bar at or before `T 13:15 UTC`.
- Macro (FRED) — only observations dated on or before `T-1`.

The outcome fields (`open_price`, `close_price`, `actual_direction`, …) come from the `T` EOD bar and are used only for scoring, never as prompt input.

## Regime Vault Mode

When `is_regime_vault=True`, the pre-market quote and proxy-gap block is omitted entirely — the 09:30 open price is never surfaced, closing the door on leakage for historical days whose intraday tape is sparse. See [[concepts/regime-vault]].

## Compiled Day Shape

Each materialized day carries `economic_calendar` (formatted 10Y/2Y yields, 10Y-2Y spread, Fed Funds rate, jobless claims), a synthetic newsletter digest, multi-proxy pre-market gaps (`SPY`, `QQQ`, `IWM`, `TLT`), `options_sentiment` derived from prior CLV/range, and the prior-session `intraday_profile`.

## Related

- [[entities/local-autoresearch]] — the research loop that consumes the cache
- [[entities/historical-downloader]] — produces the raw rows materialized here
- [[concepts/regime-vault]] — the leak-free out-of-distribution variant
