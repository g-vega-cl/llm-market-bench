---
tags: [earnings, pead, audit, dashboard, web]
category: entity
---

# Earnings Audit Page

The Earnings Audit dashboard at `/earnings-audit` is the TanStack Start frontend for earnings alpha data. It renders S&P 500 earnings alpha snapshots and sector bellwether signals from Supabase.

## Data Loading

The route `apps/web/src/routes/earnings-audit.tsx` uses a TanStack Start `createServerFn` to call both fetchers from `apps/web/src/features/earnings/api/fetch-earnings-audit.ts`:

- `fetchEarningsAlphaSnapshots()` — selects all rows from `earnings_alpha_snapshots` ordered by SUE score descending.
- `fetchSectorBellwethers()` — selects all rows from `sector_bellwether_signals` ordered by sector then market cap rank.

The page receives both datasets as props and falls back to empty arrays on error.

## Tabs & Filters

- **PEAD & SUE Leaderboard** — SUE score coloring (>= 2.0 emerald, < 0 rose), revenue surprise, Sloan accrual quality badges, and top-decile status; ticker/sector search and sector chips.
- **Sector Bellwether Radar** — Early Bellwether vs Downstream Peer badges, market cap rank, report status, and the active 14-day signal window.
- **Analyst Revision Momentum** — analyst consensus, coverage count, buy ratio, consensus target price, and implied upside.

Summary cards show total analyzed, top-decile SUE count, Sloan clean percentage, and active bellwethers.

## Related

- [[concepts/earnings-prediction-strategies]]
- [[entities/earnings-alpha]]
- [[entities/web-app]]
- [[entities/database]]
