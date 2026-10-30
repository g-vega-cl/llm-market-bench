---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **90 days ago**, Total commits analyzed: **312**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | 37 | 10 | 27.0% | 693 | 370 | **CRITICAL** |
| `apps/engine/tests/test_workflow_schedule.py` | 26 | 12 | 46.2% | 239 | 312 | **CRITICAL** |
| `apps/engine/tests/test_daily_predictor.py` | 25 | 9 | 36.0% | 763 | 225 | **CRITICAL** |
| `apps/engine/main.py` | 33 | 6 | 18.2% | 73 | 198 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 28 | 7 | 25.0% | 264 | 196 | **CRITICAL** |
| `apps/engine/autoresearch/researcher.py` | 38 | 3 | 7.9% | 300 | 114 | **CRITICAL** |
| `apps/engine/execution/market_data.py` | 13 | 8 | 61.5% | 316 | 104 | **CRITICAL** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 19 | 5 | 26.3% | 784 | 95 | **HIGH** |
| `apps/engine/tests/test_evaluate_daily_predictions.py` | 14 | 6 | 42.9% | 410 | 84 | **HIGH** |
| `apps/engine/autoresearch/program.md` | 25 | 3 | 12.0% | 137 | 75 | **HIGH** |
| `apps/engine/tasks/evaluate_daily_predictions.py` | 15 | 5 | 33.3% | 290 | 75 | **HIGH** |
| `apps/engine/tasks/newsletter_generator.py` | 17 | 4 | 23.5% | 373 | 68 | **HIGH** |
| `apps/engine/core/config.py` | 32 | 2 | 6.2% | 214 | 64 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 31 | 2 | 6.5% | 1758 | 62 | **HIGH** |
| `apps/engine/tasks/daily_autoresearch.py` | 20 | 3 | 15.0% | 735 | 60 | **HIGH** |
| `apps/engine/tests/test_newsletter_generator.py` | 14 | 4 | 28.6% | 530 | 56 | **HIGH** |
| `apps/engine/core/llm/daily_predictor_prompts.py` | 14 | 4 | 28.6% | 249 | 56 | **HIGH** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 17 | 3 | 17.6% | 378 | 51 | **HIGH** |
| `apps/cron-dispatcher/wrangler.jsonc` | 12 | 4 | 33.3% | 15 | 48 | **HIGH** |
| `packages/config/tools.json` | 22 | 2 | 9.1% | 210 | 44 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | `apps/engine/tests/test_daily_predictor.py` | 19 | 76% |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 17 | 89% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 16 | 52% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 15 | 56% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 15 | 56% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 14 | 56% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 13 | 59% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 13 | 52% |
| `apps/engine/core/config.py` | `apps/engine/main.py` | 13 | 41% |
| `apps/engine/tasks/newsletter_generator.py` | `apps/engine/tests/test_newsletter_generator.py` | 12 | 86% |
| `apps/engine/tasks/daily_autoresearch.py` | `apps/engine/tests/test_daily_autoresearch.py` | 12 | 75% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 12 | 60% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 12 | 60% |
| `apps/engine/core/llm/tools.py` | `packages/config/tools.json` | 12 | 55% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/handlers/base.py` | 12 | 48% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
