---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **250**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/web/src/routes/__root.tsx` | 14 | 9 | 64.3% | 292 | 126 | **CRITICAL** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 19 | 6 | 31.6% | 400 | 114 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 18 | 5 | 27.8% | 254 | 90 | **HIGH** |
| `apps/engine/tasks/daily_predictor.py` | 21 | 4 | 19.0% | 674 | 84 | **HIGH** |
| `apps/web/src/routes/-__root.test.tsx` | 11 | 7 | 63.6% | 423 | 77 | **HIGH** |
| `apps/engine/tasks/newsletter_generator.py` | 12 | 5 | 41.7% | 421 | 60 | **HIGH** |
| `apps/engine/trading/live_intraday_agent.py` | 13 | 4 | 30.8% | 450 | 52 | **HIGH** |
| `apps/engine/trading/test_live_intraday_agent.py` | 12 | 4 | 33.3% | 359 | 48 | **HIGH** |
| `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 15 | 3 | 20.0% | 301 | 45 | **HIGH** |
| `apps/engine/tests/test_newsletter_generator.py` | 11 | 4 | 36.4% | 604 | 44 | **HIGH** |
| `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 10 | 4 | 40.0% | 219 | 40 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 19 | 2 | 10.5% | 1907 | 38 | **HIGH** |
| `apps/engine/tests/test_verify_skill.py` | 11 | 3 | 27.3% | 204 | 33 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 16 | 2 | 12.5% | 822 | 32 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.ts` | 8 | 4 | 50.0% | 460 | 32 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/test_live_intraday_agent.py` | 12 | 100% |
| `apps/web/src/routes/-__root.test.tsx` | `apps/web/src/routes/__root.tsx` | 10 | 91% |
| `apps/web/src/features/home/components/LiveAgentConsole.test.tsx` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 9 | 100% |
| `apps/engine/tasks/newsletter_generator.py` | `apps/engine/tests/test_newsletter_generator.py` | 9 | 82% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 9 | 56% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 9 | 56% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 9 | 56% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 9 | 56% |
| `apps/free_llm_proxy/server.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 8 | 89% |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.test.tsx` | `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 8 | 80% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/core/llm/tools.py` | `apps/engine/tests/test_tools_consistency.py` | 8 | 57% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 8 | 57% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
