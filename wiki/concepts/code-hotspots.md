---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **287**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/web/src/routes/__root.tsx` | 19 | 12 | 63.2% | 329 | 228 | **CRITICAL** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 21 | 7 | 33.3% | 357 | 147 | **CRITICAL** |
| `apps/web/src/routes/-__root.test.tsx` | 15 | 9 | 60.0% | 535 | 135 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 20 | 6 | 30.0% | 341 | 120 | **CRITICAL** |
| `apps/engine/trading/test_live_intraday_agent.py` | 15 | 5 | 33.3% | 452 | 75 | **HIGH** |
| `apps/engine/tasks/daily_predictor.py` | 18 | 4 | 22.2% | 674 | 72 | **HIGH** |
| `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 16 | 4 | 25.0% | 301 | 64 | **HIGH** |
| `apps/engine/trading/live_intraday_agent.py` | 16 | 4 | 25.0% | 501 | 64 | **HIGH** |
| `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 11 | 5 | 45.5% | 220 | 55 | **HIGH** |
| `apps/engine/tasks/newsletter_generator.py` | 10 | 5 | 50.0% | 428 | 50 | **HIGH** |
| `apps/free_llm_proxy/tests/test_proxy.py` | 16 | 3 | 18.8% | 1457 | 48 | **HIGH** |
| `apps/web/src/components/ui/DefaultCatchBoundary.tsx` | 8 | 6 | 75.0% | 201 | 48 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 11 | 4 | 36.4% | 956 | 44 | **HIGH** |
| `apps/engine/tests/test_workflow_schedule.py` | 11 | 4 | 36.4% | 306 | 44 | **HIGH** |
| `apps/free_llm_proxy/server.py` | 14 | 3 | 21.4% | 587 | 42 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/web/src/routes/-__root.test.tsx` | `apps/web/src/routes/__root.tsx` | 14 | 93% |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/test_live_intraday_agent.py` | 13 | 87% |
| `apps/free_llm_proxy/server.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 12 | 86% |
| `apps/free_llm_proxy/providers.json` | `apps/free_llm_proxy/tests/test_proxy.py` | 10 | 91% |
| `apps/web/src/features/home/components/LiveAgentConsole.test.tsx` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 9 | 100% |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.test.tsx` | `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 9 | 69% |
| `apps/free_llm_proxy/providers.json` | `apps/free_llm_proxy/router.py` | 8 | 89% |
| `apps/free_llm_proxy/router.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 8 | 89% |
| `apps/engine/tasks/newsletter_generator.py` | `apps/engine/tests/test_newsletter_generator.py` | 8 | 89% |
| `apps/web/src/features/home/api/fetch-intraday-tape.test.ts` | `apps/web/src/features/home/api/fetch-intraday-tape.ts` | 7 | 100% |
| `apps/web/src/features/home/components/ConsoleQueueCard.test.tsx` | `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 7 | 100% |
| `apps/engine/trading/runner.py` | `apps/engine/trading/test_runner.py` | 7 | 100% |
| `apps/free_llm_proxy/config.py` | `apps/free_llm_proxy/server.py` | 7 | 88% |
| `apps/free_llm_proxy/.env.example` | `apps/free_llm_proxy/tests/test_proxy.py` | 7 | 78% |
| `apps/web/src/features/home/api/fetch-intraday-tape.ts` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 7 | 78% |

## Team Health

Team forensics over the same scoped window (commits analyzed: **287**, months: **2**).

- **Bus factor**: `g-vega-cl` accounts for **100%** of human commits — **FRAGILE** (single-author risk when ≥ 60%).
- **Commit velocity trend** (12 months ago): **STEADY** (last 3 months vs the 3 before, ±25% band).
- **Crisis cadence**: 0 revert/hotfix/emergency/rollback commits in 2 month(s) — **STABLE**.

### Contributors

| Author | Commits | Share of window commits |
| :--- | ---: | ---: |
| `g-vega-cl` | 287 | 100.0% |

### Commit Velocity

| Month | Commits | Trend |
| :--- | ---: | :--- |
| 2025-12 | 19 | ▇ |
| 2026-01 | 68 | ▇▇▇ |
| 2026-02 | 43 | ▇▇ |
| 2026-03 | 85 | ▇▇▇▇ |
| 2026-04 | 96 | ▇▇▇▇ |
| 2026-05 | 174 | ▇▇▇▇▇▇▇▇ |
| 2026-06 | 105 | ▇▇▇▇▇ |
| 2026-07 | 58 | ▇▇▇ |
| 2026-08 | 114 | ▇▇▇▇▇ |
| 2026-09 | 96 | ▇▇▇▇ |
| 2026-10 | 113 | ▇▇▇▇▇ |
| 2026-11 | 125 | ▇▇▇▇▇▇ |

### Crisis Cadence

No revert, hotfix, emergency, or rollback commits in the window.

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
