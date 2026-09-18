---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **90 days ago**, Total commits analyzed: **254**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/main.py` | 27 | 10 | 37.0% | 977 | 270 | **CRITICAL** |
| `apps/engine/tests/test_workflow_schedule.py` | 22 | 12 | 54.5% | 184 | 264 | **CRITICAL** |
| `apps/engine/core/llm/analysis.py` | 19 | 10 | 52.6% | 1165 | 190 | **CRITICAL** |
| `apps/engine/tasks/daily_predictor.py` | 22 | 6 | 27.3% | 385 | 132 | **CRITICAL** |
| `apps/engine/tests/test_daily_predictor.py` | 18 | 7 | 38.9% | 502 | 126 | **CRITICAL** |
| `apps/engine/execution/market_data.py` | 12 | 9 | 75.0% | 749 | 108 | **CRITICAL** |
| `apps/engine/core/config.py` | 28 | 3 | 10.7% | 204 | 84 | **HIGH** |
| `apps/engine/autoresearch/researcher.py` | 27 | 3 | 11.1% | 295 | 81 | **HIGH** |
| `apps/engine/core/llm/verification.py` | 11 | 5 | 45.5% | 394 | 55 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 27 | 2 | 7.4% | 3404 | 54 | **HIGH** |
| `apps/web/src/config/how-it-works.json` | 10 | 5 | 50.0% | 104 | 50 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 15 | 3 | 20.0% | 1549 | 45 | **HIGH** |
| `apps/engine/tests/test_evaluate_daily_predictions.py` | 9 | 5 | 55.6% | 265 | 45 | **HIGH** |
| `apps/engine/autoresearch/prompt_store.py` | 9 | 5 | 55.6% | 320 | 45 | **HIGH** |
| `apps/engine/tests/test_autoresearch.py` | 11 | 4 | 36.4% | 1835 | 44 | **HIGH** |
| `apps/cron-dispatcher/wrangler.jsonc` | 11 | 4 | 36.4% | 15 | 44 | **HIGH** |
| `apps/engine/autoresearch/program.md` | 21 | 2 | 9.5% | 127 | 42 | **HIGH** |
| `apps/engine/core/llm/handlers/base.py` | 20 | 2 | 10.0% | 232 | 40 | **HIGH** |
| `apps/engine/tests/test_newsletter.py` | 10 | 4 | 40.0% | 452 | 40 | **HIGH** |
| `apps/engine/ingest/newsletter.py` | 8 | 5 | 62.5% | 512 | 40 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | `apps/engine/tests/test_daily_predictor.py` | 14 | 78% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 14 | 70% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 13 | 48% |
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/handlers/base.py` | 12 | 60% |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 11 | 92% |
| `apps/engine/autoresearch/program.md` | `apps/engine/autoresearch/researcher.py` | 11 | 52% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/tools.py` | 11 | 52% |
| `apps/engine/autoresearch/program.md` | `apps/engine/core/llm/handlers/base.py` | 10 | 50% |
| `apps/engine/tasks/daily_autoresearch.py` | `apps/engine/tests/test_daily_autoresearch.py` | 9 | 100% |
| `apps/cron-dispatcher/src/index.ts` | `apps/cron-dispatcher/wrangler.jsonc` | 9 | 82% |
| `apps/engine/core/config.py` | `apps/engine/main.py` | 9 | 33% |
| `apps/engine/tasks/newsletter_generator.py` | `apps/engine/tests/test_newsletter_generator.py` | 8 | 80% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_tools_consistency.py` | 8 | 67% |
| `apps/engine/autoresearch/program.md` | `packages/config/tools.json` | 8 | 67% |
| `apps/engine/tests/test_tools_consistency.py` | `packages/config/tools.json` | 8 | 67% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
