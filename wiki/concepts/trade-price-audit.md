---
tags: [trades, audit, pricing, data-quality, annotations]
category: concept
---

# Trade Price Audit and Annotations

Benchify treats the trade ledger as immutable evidence. When a trade price is wrong, the fix is to **annotate** the row with an audit flag — never to rewrite the recorded price, quantity, cost, or P/L. This keeps historical performance reproducible and makes bad fills visible rather than silently correcting them.

## Full-Ledger Audit (2026-11-27)

A one-off reconciliation compared every trade against the canonical OHLC bars in `price_history`:

| Population | Count | Result |
| --- | --- | --- |
| Trades audited | 1,681 across 55 portfolios | `total_cost = price × quantity` on 1,681 / 1,681 |
| Same-session bar available | 1,508 | 1,467 fills inside `[low, high]` |
| Out-of-range fills | 5 | materially impossible prices, flagged |
| Slippage within ±0.5% | 36 | intentional model slippage, not flagged |
| No same-session bar | 173 | 98 non-trading-day fills flagged; 75 are price-history coverage gaps |

The 98 non-trading-day fills are 62 Sundays and 36 Thanksgiving 2026 fills. The 5 impossible fills are 3 `ANT` buys on 2026-11-19 at $83.0415 against a $92.72–$115.10 session range, one `XLF` buy and one `XLU` short on 2026-09-21; each recorded price matches a *later* session, which is why the fill is impossible on the stated execution date.

Apparent `total_equity` mismatches were **not** a defect: they are exactly the intentional open-short unrealized adjustments in `apps/engine/scripts/update_prices.py::_update_portfolio_metrics`. That code was left untouched.

## Trading-Day Guard

`is_us_trading_day()` in `apps/engine/trading/market_calendar.py` is the single source of truth for US equity sessions (NYSE/Nasdaq holidays plus weekends). It is enforced at the live execution entry points, not inside `Portfolio.execute_trade`, because the backtest engine deliberately trades on historical dates that may include irregular sessions:

- `apps/engine/execution/stock_picks_trading.py::run_picks_trade`
- `apps/engine/execution/sector_trading.py::run_sector_trade`
- `apps/engine/execution/daily_live_trading.py::execute_daily_moo_entries`
- `apps/engine/execution/daily_live_trading.py::execute_daily_close_exits`
- `apps/engine/execution/validation.py::validate_decision`

This closes the root cause: the old guard only rejected weekends, so Thanksgiving and other exchange holidays produced trades with no market bar.

## Session-Scoped Pricing

`resolve_entry_prices()` in `apps/engine/execution/session_prices.py` is now the entry-price source for `run_picks_trade` and `run_sector_trade`. A live session still uses the quote's `open_price`. A past `target_date` reads the session's `price_history` bar, keyed by `fetched_at::date` so execution and audit use the same date. Tickers without a bar are skipped instead of falling back to a live quote.

That closes the lookahead path behind the five impossible fills: four were picks/sector entries stamped with a past session but priced from whatever quote the backfill run fetched that day. Sector entry also read a nonexistent `open` attribute and silently fell back to `price`; it now uses `open_price`.

## Continuous Audit

`apps/engine/scripts/audit_trade_prices.py` reruns the reconciliation on the last 7 days and is piggybacked as a step in `.github/workflows/audit.yml`. It classifies each unannotated trade against its same-session bar and exits 1 on a new `NON_TRADING_DAY` or `PRICE_OUTSIDE_DAY_RANGE` violation.

Trade sessions use the America/New_York date, so an after-hours fill recorded at 02:36 UTC is matched to the prior ET session. Bar rows are fetched with pagination so a wider lookback cannot silently truncate the comparison set.

The out-of-range threshold is 0.6% of the session close, which covers 5 bps slippage per side plus rounding. Trades on trading days with no cached bar are reported as `NO_BAR` but do not fail the step; they are coverage gaps, not evidence of a bad fill. Rows that already carry an `audit_flag` are counted as annotated and never reported twice. The script only reports, it never annotates or rewrites ledger rows.

## Annotation Schema

Migration `supabase/migrations/20261127180000_annotate_trade_audit_flags.sql` adds two nullable columns to `trades`:

- `audit_flag` — constrained to `NON_TRADING_DAY` or `PRICE_OUTSIDE_DAY_RANGE`; `NULL` means the row passed the audit.
- `audit_note` — the evidence: execution date, recorded price, and the OHLC range that was violated.

The migration backfills exactly 103 rows (98 + 5). Generated types in `packages/database/supabase-types.ts` expose both fields; `fetchTrades` uses `select('*')`, so no explicit projection needed updating.

## Display

`apps/web/src/features/portfolios/components/TradesTable.tsx` renders a warning badge under the Alpaca status: `HOLIDAY` for `NON_TRADING_DAY` and `BAD_PRICE` for `PRICE_OUTSIDE_DAY_RANGE`. The note is the badge tooltip and remains available in the row data for deeper inspection. The badge never replaces the broker status — a flagged row is still a real ledger row with its original execution details.

## Invariants

- Audits are append-only metadata. Never restate a historical price, cost, or P/L.
- A flag is evidence-backed: there must be a concrete session-calendar or OHLC-range violation.
- Intentional model slippage within ±0.5% is not a bad trade.
- The guard blocks future bad fills at the orchestration boundary, not in legacy rows.

## Verification

- `./apps/engine/.venv/bin/python3 -m pytest apps/engine/trading/test_market_calendar.py apps/engine/execution/test_sector_trading_calendar.py apps/engine/execution/test_daily_live_trading.py`
- `cd apps/web && pnpm vitest run src/features/portfolios/components/TradesTable.test.tsx`
- PostgREST read probe: `GET /rest/v1/trades?select=id&audit_flag=not.is.null` must return 103 rows.

## Related

- [[concepts/backfilled-trades]]
- [[concepts/auditability]]
- [[concepts/atomic-trade-execution]]
- [[concepts/session-open-reconciliation]]
