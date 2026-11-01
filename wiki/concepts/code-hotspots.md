---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **200**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | 20 | 5 | 25.0% | 693 | 100 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 13 | 4 | 30.8% | 264 | 52 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 23 | 2 | 8.7% | 1758 | 46 | **HIGH** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 15 | 3 | 20.0% | 378 | 45 | **HIGH** |
| `apps/web/src/routes/__root.tsx` | 9 | 5 | 55.6% | 233 | 45 | **HIGH** |
| `apps/engine/tests/test_daily_predictor.py` | 10 | 4 | 40.0% | 763 | 40 | **HIGH** |
| `apps/engine/main.py` | 18 | 2 | 11.1% | 73 | 36 | **HIGH** |
| `apps/engine/tests/test_workflow_schedule.py` | 9 | 4 | 44.4% | 239 | 36 | **HIGH** |
| `apps/web/src/features/today/api/fetch-today-data.ts` | 7 | 4 | 57.1% | 460 | 28 | **MEDIUM** |
| `apps/web/src/features/today/api/fetch-today-data.test.ts` | 7 | 4 | 57.1% | 540 | 28 | **MEDIUM** |
| `apps/engine/tests/test_docker_archive_secrets.py` | 5 | 5 | 100.0% | 98 | 25 | **MEDIUM** |
| `apps/engine/tests/test_verify_skill.py` | 8 | 3 | 37.5% | 93 | 24 | **MEDIUM** |
| `apps/web/src/routes/-__root.test.tsx` | 7 | 3 | 42.9% | 352 | 21 | **MEDIUM** |
| `apps/engine/execution/daily_trading.py` | 7 | 3 | 42.9% | 304 | 21 | **MEDIUM** |
| `apps/engine/tasks/daily_autoresearch.py` | 10 | 2 | 20.0% | 735 | 20 | **MEDIUM** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 11 | 58% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 11 | 58% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 11 | 58% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 11 | 58% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 11 | 50% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 11 | 50% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 11 | 48% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 10 | 59% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/tests/test_tools_consistency.py` | 10 | 59% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/tests/test_tools_consistency.py` | 10 | 59% |
| `apps/engine/core/llm/tools.py` | `apps/engine/tests/test_tools_consistency.py` | 10 | 59% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 10 | 59% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/handlers/base.py` | 10 | 53% |
| `apps/engine/autoresearch/researcher.py` | `packages/config/tools.json` | 10 | 53% |
| `apps/engine/core/llm/handlers/base.py` | `packages/config/tools.json` | 10 | 53% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
