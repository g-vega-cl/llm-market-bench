---
tags: [engine, diversification, correlation]
category: source
---

# Source: Correlation Matrix & Diversification

Synthesized from `raw/docs/engine/CORRELATION_MATRIX.md`.

## Takeaways

- **90-Day Window**: Computes Pearson and Spearman correlations over a rolling 90-day window for a diverse universe of ETFs.
- **SMA Smoothing**: Uses 5-day SMA at window endpoints to reduce noise from single-day volatility spikes.
- **Agent Discovery**: Provides the `find_uncorrelated_assets` tool, allowing agents to proactively find diversification opportunities.

## Related

- [[entities/engine]]
- [[concepts/reasoning]]
