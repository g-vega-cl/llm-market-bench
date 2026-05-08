---
tags: [source, correlation, diversification]
category: source
source: docs/engine/CORRELATION_MATRIX.md
---

# Source: Correlation Matrix & Uncorrelated Asset Discovery

Identifies uncorrelated asset pairs with positive 90-day momentum for
diversification.

Key details:

- Ticker universe: ETFs across US sectors, international, commodities, bonds, real assets, crypto, volatility
- Methodology: 90-day window, 5-day SMA endpoints, Pearson + Spearman
- Weekly cron stores pairwise matrix to `correlation_runs` + `correlation_data`
- Agent tool: `find_uncorrelated_assets(max_correlation, min_return, method)`
- Frontend heatmap with Pearson/Spearman toggle at `/market-overview`
