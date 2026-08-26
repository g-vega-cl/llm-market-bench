---
tags: [alpaca, audit, reconciliation, portfolio]
category: entity
---

# Alpaca Audit Reconciler

**Location**: `apps/engine/audit/alpaca_audit.py`
**CLI Command**: `python main.py audit-alpaca [--model <model_name>] [--days <N>] [--json]`

The **Alpaca Audit Reconciler** reconciles an agent's simulated Supabase portfolio performance against Alpaca brokerage execution, fill prices, slippage, and position state. It provides a comprehensive audit trail for verifying that simulated trades match real brokerage fills.

## Reconciliation Pipeline

1. **Performance Verification**: Compares frontend chart metrics (`portfolio_performance` snapshots) against mark-to-market trade calculations and Alpaca fills.
2. **Trade Matching & Slippage**: Matches each trade ID with Alpaca orders using `client_order_id = {agent_id}__{ticker}__{signal}__{trade_id}` format, calculating execution price slippage per trade.
3. **Position Reconciliation**: Compares Supabase holding quantities against reconstructed Alpaca share counts.
4. **Root-Cause Discrepancy Detection**: Surfaces skipped orders (`SKIPPED_NO_POSITION`), rejected orders, or timing lags.

## Terminal Report

The `render_terminal_report()` method produces a structured Unicode-box report with four sections:
- Executive Summary & Performance Verification
- Positions Reconciliation
- Recent Trades & Execution Slippage (last 10)
- Discrepancies & Root-Cause Anomalies

## CLI Usage

```sh
# Default audit for MiniMax-M3 over 7 days
python main.py audit-alpaca

# Audit a specific model with custom lookback
python main.py audit-alpaca --model claude-haiku-4-5 --days 30

# JSON output for programmatic consumption
python main.py audit-alpaca --model gpt-4o --days 14 --json
```

## Related

- [[concepts/alpaca-order-sync]]
- [[entities/engine]]
- [[entities/database]]
