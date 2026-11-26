---
tags: [alpaca, audit, attestation, proof, trading]
category: concept
---

# External Order Attestation

Why the live trader mirrors every ledger trade to Alpaca, and how strong that evidence actually is.

## The point of Alpaca

The Supabase ledger is ours. We can edit it, backfill it, or rewrite history in it, so on its own it proves nothing about whether an order ever reached a venue. Alpaca is the outside party: an account we do not control the books of, where an order can be **cancelled but not edited**. When the ledger says "BUY 2 SPY at 11:28" and Alpaca holds a matching order tagged with the same `client_order_id`, a third party can verify the order was really sent at that time.

That is the whole job of the mirror. It is not bookkeeping, not risk management, and not a second source of truth.

## Division of responsibility

```text
[LLM decision] ─▶ ledger commit (cash, positions, P&L)  ← SOURCE OF TRUTH
                        │
                        └─▶ Alpaca paper order          ← ATTESTATION ONLY
                              client_order_id = live-spy-trader__SPY__BUY__<trade_id>
                              alpaca_order_id + alpaca_status → written back to trades
                              sync-alpaca.yml → FILLED / REJECTED every 15 min
```

- Sizing, cash, positions and leaderboard equity come from the ledger, never from Alpaca.
- A failed mirror never rolls back a ledger trade and is never retried: replaying a market order minutes later would create a fill at a price the book never recorded.
- The bridge between ledger and account starts with an exact, non-editable `client_order_id` (`<agent_id>__<ticker>__<signal>__<trade_id>`). Everything else hangs off it: `trades.alpaca_order_id`, `trades.alpaca_status`, and the reconciliation in `apps/engine/scripts/sync_alpaca_orders.py`.

## The invariant

Once `alpaca_order_id` / `alpaca_status` / `alpaca_submitted_at` are written on a trade row, application code does not rewrite them. The one exception is `alpaca_status` advancing through the reconciliation lifecycle (`SUBMITTED → FILLED | REJECTED | CANCELED | EXPIRED`), which reflects the broker's own state.

This is a documented invariant, **not enforced** by the database. Nothing stops an `UPDATE` from rewriting a mirrored order id, and the audit trail's integrity therefore depends on discipline rather than constraint. `NO_MIRROR` was written once, by hand, to mark the seven historical trades that ran while the mirror was silently failing.

## What this does not prove

- The account is **paper**. No clearing, no settlement, no counterparty — it evidences an API call, not a real execution.
- **We hold the API keys**, so we could cancel an order or open a second account; "un-editable" is a property of the order record, not of our conduct.
- It says nothing about whether the *decision* was sound, only that it was placed.

So: corroboration strong enough to settle "did the bot actually send this order?", not a compliance or legal record.

## Candidate: cryptographic ledger

A second, independent attestation layer is plausible: an append-only hash-chained log of `(trade_id, ticker, side, qty, price, client_order_id, submitted_at)`, where each entry commits to the previous one, and the daily Merkle root is anchored somewhere we cannot rewrite (a public chain, a timestamping service, or a counterparty's inbox).

It would earn its place only if two things become true: an outside party asks to verify fills without trusting us or Alpaca, and the atomic anchor (a 32-byte root per day) costs less than maintaining a second brokerage account. Until then it is a candidate, not a plan — and it would sit **beside** the ledger, never instead of it.

## Known debt

- **Ledger writes are not atomic.** `execute_intraday_portfolio_turn` inserts the trade, upserts the position, updates the portfolio and upserts the performance snapshot as four separate calls. A crash between them leaves cash and positions inconsistent, and a re-run creates a new trade id — hence a new `client_order_id` and a genuinely duplicated broker order. `execute_portfolio_trade` (RPC, `supabase/migrations/20261119050000_atomic_execute_portfolio_trade_rpc.sql`) exists for exactly this and is the intended fix; adopting it is a separate change.

## Related

- [[entities/alpaca-audit]] — reconciliation pipeline, `client_order_id` matching, discrepancy reporting
- [[entities/live-agent-trader]] — the ledger-first execution turn that emits the mirror
- [[concepts/alpaca-order-sync]] — the 15-minute status reconciler
