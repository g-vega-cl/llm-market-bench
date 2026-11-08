---
tags: [trading, portfolio, intraday]
category: entity
---
# Intraday Portfolio

The intraday portfolio management system (`apps/engine/trading/intraday_portfolio.py`) handles persistent paper portfolio for the live intraday homepage trader. Key features include:

- **Target exposure**: 20% of total portfolio equity in SPY on BUY orders
- **Sell**: 100% liquidation of SPY position back to cash
- **Hold**: no position modification
- **Session gating**: real executions occur strictly during regular market hours (09:30 AM - 04:00 PM ET)
- **Dual execution**: records into Supabase ledger and mirrors to Alpaca paper account

The system enforces a strict 20% portfolio equity cap via `compute_intraday_trade_sizing()`, where BUY orders calculate the dollar deficit to reach 20% equity, and SELL orders liquidate 100% of currently held shares. Session gating ensures no trading occurs outside market hours.

## Related
- [[entities/live-agent-trader]] - the live trader console that uses this portfolio management
- [[concepts/zero-frontend-compute]] - pre-materialized calculations
- [[entities/engine]] - the data engine that powers the pipeline
