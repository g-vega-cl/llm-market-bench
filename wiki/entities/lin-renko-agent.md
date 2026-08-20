---
tags: [entity, agent, lin, renko, single-stock, deepseek]
category: entity
---

# LIN Renko Hyper-Focused Agent

The **LIN Renko Hyper-Focused Agent** is a single-stock quantitative trading agent designed specifically for **Linde plc (`LIN`)**. It combines ATR-based Renko brick technical trend indicators with specialized Chemical Engineering and Industrial Gas sector domain context.

## Architecture

The agent is implemented in `apps/engine/analysis/lin_agent.py` and `apps/engine/tasks/lin_renko_task.py` and consists of four primary components:

1. **Renko Brick Engine (`apps/engine/analysis/renko.py`)**:
   - Processes 2-year daily FMP price streams (500 bars) into 211 discrete Renko bricks.
   - Uses locked 14-day ATR box sizing ($4.87/brick) to eliminate sideways channel noise.
   - Enforces 2-brick reversal logic to confirm trend direction shifts.

2. **Hyper-Focused LLM Synthesizer & Web Search Tools (`apps/engine/analysis/lin_agent.py`)**:
   - Powered by **DeepSeek Flash (`deepseek-v4-flash`)**.
   - Queries specialized LIN FMP fundamental tools: analyst consensus revenue estimates, ROIC (16.5%), Free Cash Flow yield (4.2%), and earnings surprises.
   - Accesses live `web_search` function tool loop to query real-time semiconductor fab gas demand catalysts and press releases.
   - Ingests ChemEng domain context: semiconductor fab gas demand (Taiwan/US fab expansions), industrial PMIs, and long-term take-or-pay contract backlogs ($4.20B).

3. **Isolated Portfolio Flow & Pipeline Hook (`apps/engine/tasks/lin_renko_task.py`)**:
   - CLI command: `./.venv/bin/python3 main.py lin-renko`.
   - Automated Ingestion Hook: Runs automatically post-consensus in `apps/engine/main.py` (`run_ingest()`).
   - Operates dedicated `$10,000` portfolio `lin-renko-agent-deepseek-flash` restricted strictly to `LIN` equity and cash.
   - Target Position Rebalancing: Computes total portfolio equity (`cash_balance + held_equity`) and sizes orders toward target allocation ($\le 25\%$ equity cap). Repeated `BUY_LONG` signals are idempotent and only buy delta shares ($\Delta = \text{target\_shares} - \text{held\_shares}$), preventing redundant 1-share churn when target allocation is already satisfied.
   - Single-Stock Guard: Enforces strict ticker validation (`symbol == "LIN"`) and executes BUY_LONG / EXIT_LONG order allocations.
   - Isolation: Excluded from `/portfolios` benchmark view; exclusively monitored via `/renko`.

4. **LIN Renko Autoresearcher (`apps/engine/autoresearch/lin_renko_autoresearch.py`)**:
   - Evaluates LIN trade win rates and drawdowns weekly, mutating context prompts for optimal execution.
   - DeepSeek AutoResearcher tracks have access to `web_search` in their selectable toolboxes.

## Frontend UI (`/renko`)

The interactive React dashboard route at `apps/web/src/routes/renko.tsx` renders:
- Interactive Renko brick cascades with Y-axis price coordinate mapping and ATR brick metrics.
- Visual 2-brick reversal threshold trigger alerts ($480.87).
- DeepSeek Flash prompt payload & ChemEng cognitive audit drawers.
- **Dedicated LIN Renko Portfolio & Ledger Section**:
  - Live metric tiles: Total Equity, Cash Balance, LIN Equity Value, and Total Return %.
  - Performance Chart with interactive Benchmark Selector (comparing against SPY, QQQ, LIN, etc.).
  - Active Positions Table tracking LIN allocation, shares, cost basis, unrealized PnL, and agent reasoning.
  - Recent Trades Audit Table detailing executed BUY/EXIT orders, quantities, prices, and timestamped decision rationale.

## Related

- [[concepts/renko-atr-sizing]]
- [[entities/engine]]
- [[entities/web-app]]
- [[entities/autoresearch]]
- [[entities/pipeline]]

