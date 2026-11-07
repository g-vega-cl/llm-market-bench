---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **235**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | 21 | 5 | 23.8% | 661 | 105 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 17 | 5 | 29.4% | 245 | 85 | **HIGH** |
| `apps/web/src/routes/__root.tsx` | 11 | 6 | 54.5% | 239 | 66 | **HIGH** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 16 | 3 | 18.8% | 379 | 48 | **HIGH** |
| `apps/engine/trading/live_intraday_agent.py` | 12 | 4 | 33.3% | 434 | 48 | **HIGH** |
| `apps/engine/trading/test_live_intraday_agent.py` | 11 | 4 | 36.4% | 356 | 44 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 20 | 2 | 10.0% | 1758 | 40 | **HIGH** |
| `apps/engine/tests/test_daily_predictor.py` | 10 | 4 | 40.0% | 763 | 40 | **HIGH** |
| `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 13 | 3 | 23.1% | 295 | 39 | **HIGH** |
| `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 9 | 4 | 44.4% | 226 | 36 | **HIGH** |
| `apps/engine/tests/test_workflow_schedule.py` | 9 | 4 | 44.4% | 243 | 36 | **HIGH** |
| `apps/engine/main.py` | 17 | 2 | 11.8% | 73 | 34 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.ts` | 8 | 4 | 50.0% | 460 | 32 | **HIGH** |
| `apps/web/src/routes/-__root.test.tsx` | 8 | 4 | 50.0% | 372 | 32 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.test.ts` | 8 | 4 | 50.0% | 540 | 32 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/test_live_intraday_agent.py` | 11 | 100% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 10 | 59% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 10 | 59% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 10 | 59% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 10 | 59% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 9 | 60% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/tests/test_tools_consistency.py` | 9 | 60% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/tests/test_tools_consistency.py` | 9 | 60% |
| `apps/engine/core/llm/tools.py` | `apps/engine/tests/test_tools_consistency.py` | 9 | 60% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 9 | 60% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/handlers/base.py` | 9 | 53% |
| `apps/engine/autoresearch/researcher.py` | `packages/config/tools.json` | 9 | 53% |
| `apps/engine/core/llm/handlers/base.py` | `packages/config/tools.json` | 9 | 53% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 9 | 47% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 9 | 47% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
