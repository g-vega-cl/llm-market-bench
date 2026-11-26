---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **366**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/web/src/routes/__root.tsx` | 24 | 13 | 54.2% | 436 | 312 | **CRITICAL** |
| `apps/engine/recipes/test_worker.py` | 20 | 9 | 45.0% | 616 | 180 | **CRITICAL** |
| `apps/engine/recipes/worker.py` | 18 | 9 | 50.0% | 407 | 162 | **CRITICAL** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 20 | 8 | 40.0% | 331 | 160 | **CRITICAL** |
| `apps/web/src/routes/-__root.test.tsx` | 17 | 9 | 52.9% | 601 | 153 | **CRITICAL** |
| `apps/engine/trading/runner.py` | 20 | 6 | 30.0% | 601 | 120 | **CRITICAL** |
| `apps/free_llm_proxy/server.py` | 20 | 6 | 30.0% | 711 | 120 | **CRITICAL** |
| `apps/web/src/features/recipes/pages/RecipeStudioPage.tsx` | 22 | 5 | 22.7% | 401 | 110 | **CRITICAL** |
| `apps/engine/trading/test_live_intraday_agent.py` | 17 | 5 | 29.4% | 559 | 85 | **HIGH** |
| `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 17 | 5 | 29.4% | 304 | 85 | **HIGH** |
| `apps/web/src/routes/index.tsx` | 20 | 4 | 20.0% | 23 | 80 | **HIGH** |
| `apps/web/src/features/home/components/ConsoleQueueCard.tsx` | 13 | 6 | 46.2% | 226 | 78 | **HIGH** |
| `apps/engine/trading/live_intraday_agent.py` | 18 | 4 | 22.2% | 627 | 72 | **HIGH** |
| `apps/free_llm_proxy/tests/test_proxy.py` | 18 | 4 | 22.2% | 1895 | 72 | **HIGH** |
| `apps/engine/audit/portfolio_auditor.py` | 12 | 6 | 50.0% | 732 | 72 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/web/src/routes/-__root.test.tsx` | `apps/web/src/routes/__root.tsx` | 14 | 82% |
| `apps/engine/trading/live_intraday_agent.py` | `apps/engine/trading/test_live_intraday_agent.py` | 14 | 82% |
| `apps/free_llm_proxy/server.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 14 | 78% |
| `apps/free_llm_proxy/providers.json` | `apps/free_llm_proxy/tests/test_proxy.py` | 11 | 73% |
| `apps/free_llm_proxy/providers.json` | `apps/free_llm_proxy/server.py` | 10 | 67% |
| `apps/web/src/features/home/components/LiveAgentConsole.test.tsx` | `apps/web/src/features/home/components/LiveAgentConsole.tsx` | 9 | 100% |
| `apps/engine/trading/runner.py` | `apps/engine/trading/test_runner.py` | 9 | 90% |
| `apps/free_llm_proxy/providers.json` | `apps/free_llm_proxy/router.py` | 9 | 90% |
| `apps/free_llm_proxy/router.py` | `apps/free_llm_proxy/tests/test_proxy.py` | 9 | 90% |
| `apps/free_llm_proxy/README.md` | `apps/free_llm_proxy/providers.json` | 9 | 69% |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.test.tsx` | `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 9 | 64% |
| `apps/engine/tasks/newsletter_generator.py` | `apps/engine/tests/test_newsletter_generator.py` | 8 | 89% |
| `apps/free_llm_proxy/config.py` | `apps/free_llm_proxy/server.py` | 8 | 80% |
| `apps/free_llm_proxy/.env.example` | `apps/free_llm_proxy/README.md` | 8 | 73% |
| `apps/free_llm_proxy/.env.example` | `apps/free_llm_proxy/providers.json` | 8 | 73% |

## Team Health

Team forensics over the same scoped window (commits analyzed: **366**, months: **2**).

- **Bus factor**: `g-vega-cl` accounts for **100%** of human commits — **FRAGILE** (single-author risk when ≥ 60%).
- **Commit velocity trend** (12 months ago): **ACCELERATING** (last 3 months vs the 3 before, ±25% band).
- **Crisis cadence**: 1 revert/hotfix/emergency/rollback commits in 2 month(s) — **STABLE**.

### Contributors

| Author | Commits | Share of window commits |
| :--- | ---: | ---: |
| `g-vega-cl` | 366 | 100.0% |

### Commit Velocity

| Month | Commits | Trend |
| :--- | ---: | :--- |
| 2025-12 | 19 | ▇ |
| 2026-01 | 68 | ▇▇ |
| 2026-02 | 43 | ▇ |
| 2026-03 | 85 | ▇▇▇ |
| 2026-04 | 96 | ▇▇▇ |
| 2026-05 | 174 | ▇▇▇▇▇▇ |
| 2026-06 | 105 | ▇▇▇▇ |
| 2026-07 | 58 | ▇▇ |
| 2026-08 | 114 | ▇▇▇▇ |
| 2026-09 | 96 | ▇▇▇ |
| 2026-10 | 113 | ▇▇▇▇ |
| 2026-11 | 239 | ▇▇▇▇▇▇▇▇ |

### Crisis Cadence

| Commit | Kind | Subject |
| :--- | :--- | :--- |
| `684d1b5e` | revert | Revert "feat(home): playground homepage — five-block builder on /" |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
