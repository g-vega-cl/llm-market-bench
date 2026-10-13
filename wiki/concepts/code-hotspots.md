---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **191**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | 25 | 8 | 32.0% | 713 | 200 | **CRITICAL** |
| `apps/engine/tests/test_workflow_schedule.py` | 17 | 9 | 52.9% | 239 | 153 | **CRITICAL** |
| `apps/engine/tests/test_daily_predictor.py` | 14 | 8 | 57.1% | 705 | 112 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 19 | 5 | 26.3% | 261 | 95 | **HIGH** |
| `apps/engine/main.py` | 22 | 3 | 13.6% | 73 | 66 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 28 | 2 | 7.1% | 1758 | 56 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 13 | 4 | 30.8% | 784 | 52 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 16 | 3 | 18.8% | 735 | 48 | **HIGH** |
| `apps/engine/execution/market_data.py` | 8 | 6 | 75.0% | 319 | 48 | **HIGH** |
| `apps/engine/core/config.py` | 22 | 2 | 9.1% | 214 | 44 | **HIGH** |
| `apps/engine/autoresearch/program.md` | 22 | 2 | 9.1% | 137 | 44 | **HIGH** |
| `apps/engine/tasks/evaluate_daily_predictions.py` | 11 | 4 | 36.4% | 290 | 44 | **HIGH** |
| `packages/config/tools.json` | 21 | 2 | 9.5% | 210 | 42 | **HIGH** |
| `apps/engine/tests/test_evaluate_daily_predictions.py` | 9 | 4 | 44.4% | 410 | 36 | **HIGH** |
| `apps/engine/autoresearch/researcher.py` | 31 | 1 | 3.2% | 300 | 31 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 14 | 54% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 14 | 54% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 14 | 50% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 13 | 62% |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 12 | 92% |
| `apps/engine/tasks/daily_predictor.py` | `apps/engine/tests/test_daily_predictor.py` | 12 | 86% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 12 | 60% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 12 | 60% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 12 | 57% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 12 | 55% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 12 | 55% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/tests/test_tools_consistency.py` | 11 | 55% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/tests/test_tools_consistency.py` | 11 | 55% |
| `apps/engine/core/llm/tools.py` | `apps/engine/tests/test_tools_consistency.py` | 11 | 55% |
| `apps/engine/autoresearch/researcher.py` | `packages/config/tools.json` | 11 | 52% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
