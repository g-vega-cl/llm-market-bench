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

2. **Hyper-Focused LLM Synthesizer & FMP Tools (`apps/engine/analysis/lin_agent.py`)**:
   - Powered by **DeepSeek Flash (`deepseek-v4-flash`)**.
   - Queries specialized LIN FMP fundamental tools: analyst consensus revenue estimates, ROIC (16.5%), Free Cash Flow yield (4.2%), and earnings surprises.
   - Ingests ChemEng domain context: semiconductor fab gas demand (Taiwan/US fab expansions), industrial PMIs, and long-term take-or-pay contract backlogs ($4.20B).

3. **Standalone Flow Task Runner (`apps/engine/tasks/lin_renko_task.py`)**:
   - CLI command: `./.venv/bin/python3 main.py lin-renko`.
   - Bypasses multi-stock consensus debate for fast-track execution.
   - Operates dedicated `$10,000` portfolio `lin-renko-agent-deepseek-flash` restricted strictly to `LIN` equity and cash.

4. **LIN Renko Autoresearcher (`apps/engine/autoresearch/lin_renko_autoresearch.py`)**:
   - Evaluates LIN trade win rates and drawdowns weekly, mutating context prompts for optimal execution.

## Frontend UI (`/renko`)

The interactive React dashboard route at `apps/web/src/routes/renko.tsx` renders:
- Interactive D3 Renko brick cascades with Y-axis price coordinate mapping.
- Visual 2-brick reversal threshold lines ($480.87).
- DeepSeek Flash prompt payload & ChemEng cognitive audit drawers.

## Related

- [[concepts/renko-atr-sizing]]
- [[entities/engine]]
- [[entities/web-app]]
- [[entities/autoresearch]]
