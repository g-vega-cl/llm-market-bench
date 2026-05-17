---
tags: [execution, alpaca, sync, cron]
category: concept
---

# Alpaca Order Sync

How Alpaca paper-trading order status is synced back to the Supabase `trades` table.

## Architecture

The sync is **decoupled** from the engine run lifecycle — it runs as a daily GitHub Actions cron job, not inside the trading pipeline.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Engine trades   │────▶│  Alpaca Broker   │────▶│  Supabase trades │
│  portfolio.py    │     │  submit_order()  │     │  alpaca_status = │
│                  │     │                  │     │  "SUBMITTED"     │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                    ...hours pass...
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│  GitHub Actions  │────▶│  sync_alpaca_    │◀─────────────┘
│  Daily 4pm ET    │     │  orders.py       │
│                  │     │                  │
└─────────────────┘     │  For each pending │     ┌─────────────────┐
                        │  order:           │────▶│  Alpaca API     │
                        │  get_order_by_id()│     │  order.status   │
                        └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Supabase trades │
                        │  alpaca_status = │
                        │  "FILLED" (etc.) │
                        └─────────────────┘
```

## Status Lifecycle

| Status | Set By | Meaning |
|--------|--------|---------|
| `SUBMITTED` | `alpaca_broker.py` at order placement | Order placed in Alpaca, awaiting fill |
| `FILLED` | Sync script | Alpaca filled the order |
| `REJECTED` | Sync script | Alpaca rejected the order |
| `CANCELED` | Sync script | Order was cancelled |
| `EXPIRED` | Sync script | DAY order expired unfilled |
| `ERROR` | `alpaca_broker.py` on submission failure | Couldn't submit to Alpaca |
| `SKIPPED_NO_POSITION` | `alpaca_broker.py` SELL guardrail | Blocked — no shares held |

Before 2026-05-14, the initial status was `PENDING` instead of `SUBMITTED`. All legacy `PENDING` orders have reached terminal states and the sync script now only tracks `SUBMITTED` orders.

## Sync Script

**Location**: `apps/engine/scripts/sync_alpaca_orders.py`

Queries trades with `alpaca_status = 'SUBMITTED'` and `alpaca_order_id IS NOT NULL` from the last 24 hours. For each, calls `TradingClient.get_order_by_id()` and updates status when the order reaches a terminal state (filled, rejected, canceled, expired). Also sets `alpaca_filled_at` when filled.

**Rate limits**: Alpaca allows 200 requests/minute. The sync makes 1 API call per pending order — well within limits even on the busiest day.

## GitHub Actions

**Workflow**: `.github/workflows/sync-alpaca.yml`
- **Schedule**: Daily at 20:00 UTC (4pm ET, after market close) on weekdays
- **Manual**: `workflow_dispatch` for ad-hoc runs
- **Secrets required**: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`

## Why Decoupled?

The original design was "fire-and-forget" — Alpaca was treated as an audit mirror with no sync back, so `alpaca_status` stayed permanently at `PENDING`. An in-process polling approach (background asyncio tasks) was rejected because `asyncio.run()` cancels pending tasks when the main pipeline completes, making it unreliable.

A separate cron job is simpler, more reliable, and survives engine restarts.

## Related Files

- `apps/engine/execution/alpaca_broker.py` — Sets `SUBMITTED` at order placement
- `apps/engine/scripts/sync_alpaca_orders.py` — Standalone sync script
- `.github/workflows/sync-alpaca.yml` — Daily cron trigger
- `supabase/migrations/20260423000000_add_alpaca_columns_to_trades.sql` — Schema (original alpaca columns)
- `supabase/migrations/20260514000000_add_alpaca_filled_at_to_trades.sql` — Schema (alpaca_filled_at)
- `apps/web/src/features/portfolios/components/TradesTable.tsx` — Frontend badge display
