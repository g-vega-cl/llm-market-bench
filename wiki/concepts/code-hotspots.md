---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **184**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | 23 | 7 | 30.4% | 713 | 161 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 18 | 6 | 33.3% | 264 | 108 | **CRITICAL** |
| `apps/engine/tests/test_daily_predictor.py` | 13 | 7 | 53.8% | 748 | 91 | **HIGH** |
| `apps/engine/tests/test_workflow_schedule.py` | 15 | 6 | 40.0% | 239 | 90 | **CRITICAL** |
| `apps/engine/main.py` | 21 | 3 | 14.3% | 73 | 63 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 25 | 2 | 8.0% | 1758 | 50 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 15 | 3 | 20.0% | 735 | 45 | **HIGH** |
| `apps/engine/autoresearch/program.md` | 22 | 2 | 9.1% | 137 | 44 | **HIGH** |
| `apps/engine/tasks/evaluate_daily_predictions.py` | 11 | 4 | 36.4% | 290 | 44 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 11 | 4 | 36.4% | 784 | 44 | **HIGH** |
| `packages/config/tools.json` | 21 | 2 | 9.5% | 210 | 42 | **HIGH** |
| `apps/engine/core/config.py` | 20 | 2 | 10.0% | 214 | 40 | **HIGH** |
| `apps/engine/tests/test_evaluate_daily_predictions.py` | 9 | 4 | 44.4% | 410 | 36 | **HIGH** |
| `apps/engine/execution/market_data.py` | 6 | 5 | 83.3% | 320 | 30 | **HIGH** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 13 | 2 | 15.4% | 379 | 26 | **MEDIUM** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 13 | 62% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 12 | 60% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 12 | 60% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 12 | 57% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 12 | 55% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 12 | 55% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 12 | 50% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 12 | 50% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 12 | 48% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/tests/test_tools_consistency.py` | 11 | 55% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/tests/test_tools_consistency.py` | 11 | 55% |
| `apps/engine/core/llm/tools.py` | `apps/engine/tests/test_tools_consistency.py` | 11 | 55% |
| `apps/engine/autoresearch/researcher.py` | `packages/config/tools.json` | 11 | 52% |
| `apps/engine/core/llm/handlers/base.py` | `packages/config/tools.json` | 11 | 52% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/handlers/base.py` | 11 | 50% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
