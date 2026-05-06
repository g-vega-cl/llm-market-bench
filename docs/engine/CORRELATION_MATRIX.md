# Correlation Matrix & Uncorrelated Asset Discovery

Identifies uncorrelated asset pairs with positive 90-day momentum for portfolio diversification.

## Ticker Universe

Tracks ETFs across US sectors, US broad market, international developed/emerging, commodities, bonds, real assets, dollar, crypto, and volatility. The canonical list is defined in `apps/engine/analysis/correlation_matrix.py` — read it there to avoid drift.

## Methodology

- **Window**: 90 calendar days
- **Returns**: 5-day SMA at both endpoints (falls back to raw endpoints when < 10 data points)
- **Pearson**: Standard linear correlation, best for normally distributed returns
- **Spearman**: Rank-based correlation, robust to outliers and non-linear relationships

## Pipeline

Weekly cron (schedule: see `.github/workflows/correlation.yml`) runs `correlation_matrix.py`:
1. Fetch 90 days of EOD prices for the ticker universe from the market data provider
2. Compute daily returns, then Pearson + Spearman correlation
3. Store the full pairwise matrix to Supabase (`correlation_runs` + `correlation_data` tables)
4. Post-insert row-count verification ensures storage integrity

## Agent Tool

```
find_uncorrelated_assets(max_correlation=0.3, min_return=0.0, method="pearson")
```

Returns sorted pairs with correlations and 90-day returns.

## Frontend

`/market-overview` page displays an interactive heatmap (Pearson/Spearman toggle), a filterable uncorrelated pairs table, and a sector performance grid.

## Key Files

- `apps/engine/analysis/correlation_matrix.py` — Weekly computation script
- `.github/workflows/correlation.yml` — Cron trigger
- `apps/engine/tests/test_correlation_matrix.py` — Test suite
- `supabase/migrations/20260420000001_create_correlation_tables.sql` — DB schema
