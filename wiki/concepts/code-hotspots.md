---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **241**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/web/src/routes/__root.tsx` | 13 | 8 | 61.5% | 241 | 104 | **CRITICAL** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 18 | 5 | 27.8% | 390 | 90 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 18 | 5 | 27.8% | 254 | 90 | **HIGH** |
| `apps/engine/tasks/daily_predictor.py` | 21 | 4 | 19.0% | 674 | 84 | **HIGH** |
| `apps/web/src/routes/-__root.test.tsx` | 10 | 6 | 60.0% | 401 | 60 | **HIGH** |
| `apps/engine/trading/live_intraday_agent.py` | 13 | 4 | 30.8% | 450 | 52 | **HIGH** |
| `apps/engine/trading/test_live_intraday_agent.py` | 12 | 4 | 33.3% | 359 | 48 | **HIGH** |
| `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 14 | 3 | 21.4% | 299 | 42 | **HIGH** |
| `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 10 | 4 | 40.0% | 219 | 40 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 19 | 2 | 10.5% | 1907 | 38 | **HIGH** |
| `apps/engine/tasks/newsletter_generator.py` | 9 | 4 | 44.4% | 379 | 36 | **HIGH** |
| `apps/engine/tests/test_verify_skill.py` | 11 | 3 | 27.3% | 161 | 33 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 16 | 2 | 12.5% | 822 | 32 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.ts` | 8 | 4 | 50.0% | 460 | 32 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.test.ts` | 8 | 4 | 50.0% | 540 | 32 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/test_live_intraday_agent.py` | 12 | 100% |
| `apps/web/src/features/home/components/LiveAgentConsole.test.tsx` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 9 | 100% |
| `apps/web/src/routes/-__root.test.tsx` | `apps/web/src/routes/__root.tsx` | 9 | 90% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 9 | 56% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 9 | 56% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 9 | 56% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 9 | 56% |
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
