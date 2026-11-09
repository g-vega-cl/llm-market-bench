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
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 17 | 5 | 29.4% | 254 | 85 | **HIGH** |
| `apps/web/src/routes/__root.tsx` | 12 | 7 | 58.3% | 239 | 84 | **HIGH** |
| `apps/engine/tasks/daily_predictor.py` | 19 | 4 | 21.1% | 678 | 76 | **HIGH** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 17 | 4 | 23.5% | 384 | 68 | **HIGH** |
| `apps/engine/trading/live_intraday_agent.py` | 13 | 4 | 30.8% | 450 | 52 | **HIGH** |
| `apps/engine/trading/test_live_intraday_agent.py` | 12 | 4 | 33.3% | 359 | 48 | **HIGH** |
| `apps/web/src/routes/-__root.test.tsx` | 9 | 5 | 55.6% | 393 | 45 | **HIGH** |
| `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 14 | 3 | 21.4% | 299 | 42 | **HIGH** |
| `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 10 | 4 | 40.0% | 219 | 40 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 19 | 2 | 10.5% | 1838 | 38 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.ts` | 8 | 4 | 50.0% | 460 | 32 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.test.ts` | 8 | 4 | 50.0% | 540 | 32 | **HIGH** |
| `apps/engine/tests/test_verify_skill.py` | 10 | 3 | 30.0% | 119 | 30 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 10 | 3 | 30.0% | 868 | 30 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 14 | 2 | 14.3% | 825 | 28 | **MEDIUM** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/test_live_intraday_agent.py` | 12 | 100% |
| `apps/web/src/features/home/components/LiveAgentConsole.test.tsx` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 9 | 100% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 9 | 56% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 9 | 56% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 9 | 56% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 9 | 56% |
| `apps/web/src/routes/-__root.test.tsx` | `apps/web/src/routes/__root.tsx` | 8 | 89% |
| `apps/free_llm_proxy/server.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 8 | 89% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/core/llm/tools.py` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 8 | 57% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/handlers/base.py` | 8 | 50% |
| `apps/engine/autoresearch/researcher.py` | `packages/config/tools.json` | 8 | 50% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
