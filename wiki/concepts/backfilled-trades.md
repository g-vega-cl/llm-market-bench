---
tags: [trades, reconciliation, alpaca, auditability, auto-heal]
category: concept
---

# Backfilled Trades

A **backfilled trade** is a trade record that was reconstructed after the fact rather than executed live against Alpaca. Backfilled trades are marked with `alpaca_status = "BACKFILLED"` so that the audit trail never conflates a post-market reconciliation with a real broker execution.

## Why They Exist

Systematic portfolios (Daily SPY, weekly Sector Strategies) are supposed to trade on a fixed schedule. If a scheduled execution is missed — a failed workflow run, a transient error, or a gap in the pipeline — the portfolio's cash, equity, and position state drift out of sync with the predictions it is meant to be trading. The [[entities/portfolio-auditor]] detects these gaps and, in `--fix` mode, reconstructs the missing trades from canonical historical session prints (the OHLC prices stored on the prediction) using the standard model slippage.

## Distinguishing Backfilled From Live

- Live executions carry a real `alpaca_status` (`FILLED`, `PENDING`, `SUBMITTED`, etc.) and an `alpaca_order_id`.
- Backfilled trades carry `alpaca_status = "BACKFILLED"` and no Alpaca order id.

The dashboard's `TradesTable` renders `BACKFILLED` as a distinct accent-colored badge with the tooltip *"Reconstructed post-market via historical session bars"*, and — unlike other statuses — it is **not** a link to the Alpaca order page, since no broker order exists.

## Auditability

Backfilling preserves the [[concepts/auditability]] tenet: a reconstructed trade is still traceable to the prediction and session prices it was derived from, and its provenance is explicit in the status field. Nothing is silently invented — the reconstruction reuses the same execution functions and slippage model as live trading.

## Related

- [[entities/portfolio-auditor]]
- [[concepts/system-portfolios]]
- [[concepts/alpaca-order-sync]]
- [[concepts/auditability]]
