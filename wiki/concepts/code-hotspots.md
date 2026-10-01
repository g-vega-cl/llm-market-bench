---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **90 days ago**, Total commits analyzed: **269**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tests/test_workflow_schedule.py` | 25 | 13 | 52.0% | 209 | 325 | **CRITICAL** |
| `apps/engine/main.py` | 36 | 8 | 22.2% | 73 | 288 | **CRITICAL** |
| `apps/engine/tasks/daily_predictor.py` | 26 | 7 | 26.9% | 498 | 182 | **CRITICAL** |
| `apps/engine/tests/test_daily_predictor.py` | 21 | 8 | 38.1% | 612 | 168 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 25 | 6 | 24.0% | 161 | 150 | **CRITICAL** |
| `apps/engine/core/llm/analysis.py` | 17 | 8 | 47.1% | 281 | 136 | **CRITICAL** |
| `apps/engine/core/llm/tools.py` | 33 | 4 | 12.1% | 1652 | 132 | **CRITICAL** |
| `apps/engine/execution/market_data.py` | 12 | 9 | 75.0% | 319 | 108 | **CRITICAL** |
| `apps/engine/autoresearch/researcher.py` | 34 | 3 | 8.8% | 297 | 102 | **CRITICAL** |
| `apps/engine/core/config.py` | 33 | 3 | 9.1% | 212 | 99 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 18 | 5 | 27.8% | 673 | 90 | **HIGH** |
| `apps/engine/autoresearch/program.md` | 26 | 3 | 11.5% | 133 | 78 | **HIGH** |
| `apps/engine/tests/test_evaluate_daily_predictions.py` | 12 | 6 | 50.0% | 349 | 72 | **HIGH** |
| `apps/engine/tasks/evaluate_daily_predictions.py` | 12 | 5 | 41.7% | 276 | 60 | **HIGH** |
| `apps/web/src/config/how-it-works.json` | 12 | 5 | 41.7% | 109 | 60 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 19 | 3 | 15.8% | 735 | 57 | **HIGH** |
| `apps/engine/tests/test_autoresearch.py` | 10 | 5 | 50.0% | 1965 | 50 | **HIGH** |
| `apps/web/src/features/autoresearch/components/DailyScoreDisplay.tsx` | 9 | 5 | 55.6% | 91 | 45 | **HIGH** |
| `apps/cron-dispatcher/wrangler.jsonc` | 11 | 4 | 36.4% | 15 | 44 | **HIGH** |
| `apps/engine/core/llm/verification.py` | 10 | 4 | 40.0% | 394 | 40 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 18 | 69% |
| `apps/engine/tasks/daily_predictor.py` | `apps/engine/tests/test_daily_predictor.py` | 17 | 81% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 17 | 52% |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 16 | 89% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 16 | 62% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 16 | 62% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 15 | 58% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/handlers/base.py` | 14 | 54% |
| `apps/engine/core/config.py` | `apps/engine/main.py` | 14 | 42% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 13 | 72% |
| `apps/engine/tasks/daily_autoresearch.py` | `apps/engine/tests/test_daily_autoresearch.py` | 12 | 80% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 12 | 71% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 12 | 71% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 12 | 67% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/tests/test_tools_consistency.py` | 11 | 65% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
