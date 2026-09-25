---
tags: [metrics, portfolios, web, performance]
category: concept
---

# Daily Move

A per-portfolio metric that reports the most recent day-over-day percentage
change in total equity. It gives viewers an at-a-glance sense of how a portfolio
performed in the latest recorded session, without needing to read the full
equity curve.

## Calculation

The metric is derived directly from the portfolio's `portfolio_performance`
history series. It compares the two most recent snapshots:

```
todayPct = (last.total_equity - prev.total_equity) / prev.total_equity * 100
```

- `last` is the newest snapshot (highest date) in the series
- `prev` is the one immediately before it
- If fewer than two snapshots exist, no value is produced and the metric is
  hidden
- If `prev` equity is zero, the percentage falls back to `0` rather than
  dividing by zero

Because it is computed from persisted equity history rather than live quotes, it
aligns exactly with the values already shown in the portfolio performance charts
and stays consistent across surfaces.

## Where It Appears

### Portfolio Detail Page

A `Daily Move` metric tile sits alongside `Total Equity` and `Cash` (see
[[entities/web-app]]). Its icon is `📈` for gains and `📉` for losses, and the
value is formatted with a leading `+` for non-negative changes (e.g. `+1.00%`,
`-1.50%`). The tile is only rendered when at least two history points exist.

### Portfolios Page

Each active portfolio card shows a compact badge with the same percentage — a
`success` color scheme for gains, `danger` for losses. Retired portfolios do not
show the badge. The values are pulled from the comparison performance dataset
(`fetchAllActivePortfolioPerformance`) and indexed by portfolio id, so cards do
not need to fetch history individually.

## Related

- [[entities/web-app]] — the frontend surfaces that render this metric
- [[concepts/system-portfolios]] — system portfolios are included in the
  portfolio universe and display the same daily move indicators
- [[entities/database]] — `portfolio_performance` is the backing table
