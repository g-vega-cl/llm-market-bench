---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **196**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tests/test_workflow_schedule.py` | 20 | 9 | 45.0% | 239 | 180 | **CRITICAL** |
| `apps/engine/tasks/daily_predictor.py` | 25 | 7 | 28.0% | 663 | 175 | **CRITICAL** |
| `apps/engine/tests/test_daily_predictor.py` | 16 | 8 | 50.0% | 660 | 128 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 21 | 6 | 28.6% | 261 | 126 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 15 | 5 | 33.3% | 784 | 75 | **HIGH** |
| `apps/engine/main.py` | 24 | 3 | 12.5% | 73 | 72 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 28 | 2 | 7.1% | 1758 | 56 | **HIGH** |
| `apps/engine/execution/market_data.py` | 9 | 6 | 66.7% | 319 | 54 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 17 | 3 | 17.6% | 735 | 51 | **HIGH** |
| `apps/engine/core/config.py` | 24 | 2 | 8.3% | 214 | 48 | **HIGH** |
| `apps/engine/autoresearch/program.md` | 22 | 2 | 9.1% | 137 | 44 | **HIGH** |
| `packages/config/tools.json` | 21 | 2 | 9.5% | 210 | 42 | **HIGH** |
| `apps/engine/tasks/evaluate_daily_predictions.py` | 10 | 4 | 40.0% | 290 | 40 | **HIGH** |
| `apps/engine/tests/test_evaluate_daily_predictions.py` | 9 | 4 | 44.4% | 410 | 36 | **HIGH** |
| `apps/engine/autoresearch/researcher.py` | 31 | 1 | 3.2% | 300 | 31 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 14 | 93% |
| `apps/engine/tasks/daily_predictor.py` | `apps/engine/tests/test_daily_predictor.py` | 14 | 88% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 14 | 54% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 14 | 54% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 14 | 50% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 13 | 62% |
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
