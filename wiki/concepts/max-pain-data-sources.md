---
tags: [concept, max-pain, options, data-quality, alpaca, massive]
category: concept
---

# Max Pain Data Sources

Max Pain is the strike that minimizes total option-writer payout across **every** listed strike of one expiration, weighted by **open interest** (OI). It is only meaningful over the full chain with real OI.

## Why Massive free tier was wrong

The Massive (Polygon) free tier has no options snapshot. `MassiveOptionsClient._fetch_free_tier_contracts` ([[entities/massive-options]]) therefore samples **4 contracts** (ATM and 25-delta call/put) and uses previous-day *volume* as an OI stand-in. Max Pain over 4 contracts collapses onto the ATM strike (within about 0.05% of spot), which is noise: `sys-max-pain` never saw its 0.25%-2.5% discount and newsletters printed a meaningless strike.

## Current rule

- **Source of truth**: Alpaca `GET /v2/options/contracts` (`open_interest`, `open_interest_date`, OCC end-of-previous-day), module `apps/engine/execution/providers/alpaca_max_pain.py`. FMP exposes no options chain.
- **Free-tier Massive snapshots** (newsletter, macro options, options surface) get their `max_pain` replaced by the Alpaca value for the same expiration, tagged `max_pain_source`. When Alpaca is unavailable, `max_pain` is `None` (rendered N/A) rather than a fabricated strike.
- **Paid Massive snapshots** keep their own full-chain calculation.
- **Sanity guards**: fewer than 10 strikes with OI, or open interest older than 5 days (OCC lag is typically 2-3 days), returns no value. Cross-checked live on 2026-10-22: SPY 769 and QQQ 720 matched optioncharts.io.

## Related

- [[entities/max-pain-pinning]]
- [[concepts/max-pain-pinning]]
- [[entities/massive-options]]
- [[entities/macro-options]]
