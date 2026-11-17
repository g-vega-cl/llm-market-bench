---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **278**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/web/src/routes/__root.tsx` | 17 | 10 | 58.8% | 347 | 170 | **CRITICAL** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 20 | 6 | 30.0% | 361 | 120 | **CRITICAL** |
| `apps/web/src/routes/-__root.test.tsx` | 14 | 8 | 57.1% | 523 | 112 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 19 | 5 | 26.3% | 341 | 95 | **HIGH** |
| `apps/engine/tasks/daily_predictor.py` | 18 | 4 | 22.2% | 674 | 72 | **HIGH** |
| `apps/engine/trading/live_intraday_agent.py` | 14 | 4 | 28.6% | 436 | 56 | **HIGH** |
| `apps/engine/trading/test_live_intraday_agent.py` | 13 | 4 | 30.8% | 328 | 52 | **HIGH** |
| `apps/engine/tasks/newsletter_generator.py` | 10 | 5 | 50.0% | 428 | 50 | **HIGH** |
| `apps/free_llm_proxy/tests/test_proxy.py` | 15 | 3 | 20.0% | 1448 | 45 | **HIGH** |
| `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 15 | 3 | 20.0% | 301 | 45 | **HIGH** |
| `apps/engine/tests/test_workflow_schedule.py` | 11 | 4 | 36.4% | 306 | 44 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 11 | 4 | 36.4% | 954 | 44 | **HIGH** |
| `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 10 | 4 | 40.0% | 219 | 40 | **HIGH** |
| `apps/free_llm_proxy/server.py` | 13 | 3 | 23.1% | 584 | 39 | **HIGH** |
| `apps/engine/trading/runner.py` | 13 | 3 | 23.1% | 463 | 39 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/web/src/routes/-__root.test.tsx` | `apps/web/src/routes/__root.tsx` | 13 | 93% |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/test_live_intraday_agent.py` | 12 | 92% |
| `apps/free_llm_proxy/server.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 11 | 85% |
| `apps/web/src/features/home/components/LiveAgentConsole.test.tsx` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 9 | 100% |
| `apps/free_llm_proxy/providers.json` | `apps/free_llm_proxy/tests/test_proxy.py` | 9 | 90% |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.test.tsx` | `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 9 | 82% |
| `apps/free_llm_proxy/providers.json` | `apps/free_llm_proxy/router.py` | 8 | 89% |
| `apps/free_llm_proxy/router.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 8 | 89% |
| `apps/engine/tasks/newsletter_generator.py` | `apps/engine/tests/test_newsletter_generator.py` | 8 | 89% |
| `apps/web/src/features/home/api/fetch-intraday-tape.test.ts` | `apps/web/src/features/home/api/fetch-intraday-tape.ts` | 7 | 100% |
| `apps/web/src/features/home/components/ConsoleQueueCard.test.tsx` | `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 7 | 100% |
| `apps/engine/trading/runner.py` | `apps/engine/trading/test_runner.py` | 7 | 100% |
| `apps/web/src/features/home/api/fetch-intraday-tape.ts` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 7 | 78% |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 7 | 64% |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/runner.py` | 7 | 54% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
