---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **90 days ago**, Total commits analyzed: **266**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/core/llm/analysis.py` | 22 | 14 | 63.6% | 1150 | 308 | **CRITICAL** |
| `apps/engine/main.py` | 20 | 9 | 45.0% | 911 | 180 | **CRITICAL** |
| `apps/engine/tests/test_workflow_schedule.py` | 17 | 10 | 58.8% | 131 | 170 | **CRITICAL** |
| `apps/engine/execution/market_data.py` | 15 | 9 | 60.0% | 643 | 135 | **CRITICAL** |
| `apps/engine/tasks/daily_predictor.py` | 16 | 5 | 31.2% | 320 | 80 | **HIGH** |
| `apps/engine/tests/test_daily_predictor.py` | 14 | 5 | 35.7% | 323 | 70 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 22 | 3 | 13.6% | 2242 | 66 | **HIGH** |
| `apps/engine/execution/providers/fmp.py` | 12 | 5 | 41.7% | 646 | 60 | **HIGH** |
| `apps/web/src/routes/__root.tsx` | 17 | 3 | 17.6% | 212 | 51 | **HIGH** |
| `apps/engine/core/llm/verification.py` | 9 | 5 | 55.6% | 378 | 45 | **HIGH** |
| `apps/web/src/features/autoresearch/components/DailyScoreDisplay.tsx` | 9 | 5 | 55.6% | 912 | 45 | **HIGH** |
| `apps/engine/autoresearch/prompt_store.py` | 9 | 5 | 55.6% | 320 | 45 | **HIGH** |
| `apps/cron-dispatcher/wrangler.jsonc` | 11 | 4 | 36.4% | 15 | 44 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 14 | 3 | 21.4% | 1471 | 42 | **HIGH** |
| `apps/engine/core/config.py` | 20 | 2 | 10.0% | 180 | 40 | **HIGH** |
| `apps/web/src/config/how-it-works.json` | 8 | 5 | 62.5% | 102 | 40 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | 12 | 3 | 25.0% | 383 | 36 | **HIGH** |
| `apps/engine/autoresearch/researcher.py` | 12 | 3 | 25.0% | 216 | 36 | **HIGH** |
| `apps/cron-dispatcher/src/index.ts` | 11 | 3 | 27.3% | 153 | 33 | **HIGH** |
| `apps/engine/tests/test_autoresearch.py` | 11 | 3 | 27.3% | 1811 | 33 | **HIGH** |

## Temporal Coupling (Co-churn)

Files that consistently change in the same commit indicate implicit architectural coupling.

| Primary File | Coupled File | Shared Commits | Coupling Strength |
| :--- | :--- | :---: | :---: |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx` | `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 11 | 92% |
| `apps/web/src/features/home/pages/HomePage.test.tsx` | `apps/web/src/features/home/pages/HomePage.tsx` | 11 | 92% |
| `apps/engine/tasks/daily_predictor.py` | `apps/engine/tests/test_daily_predictor.py` | 11 | 79% |
| `apps/cron-dispatcher/src/index.ts` | `apps/cron-dispatcher/wrangler.jsonc` | 9 | 82% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 8 | 67% |
| `apps/engine/tasks/daily_autoresearch.py` | `apps/engine/tests/test_daily_autoresearch.py` | 7 | 100% |
| `apps/web/src/features/today/components/NewsletterFeed.test.tsx` | `apps/web/src/features/today/components/NewsletterFeed.tsx` | 7 | 100% |
| `apps/web/src/features/autoresearch/components/DailyScoreDisplay.test.tsx` | `apps/web/src/features/autoresearch/components/DailyScoreDisplay.tsx` | 7 | 88% |
| `apps/engine/core/config.py` | `apps/engine/main.py` | 7 | 35% |
| `apps/engine/tasks/newsletter_generator.py` | `apps/engine/tests/test_newsletter_generator.py` | 6 | 86% |
| `apps/engine/scripts/update_market_barometer.py` | `apps/engine/tests/test_market_barometer.py` | 6 | 86% |
| `apps/engine/autoresearch/program.md` | `apps/engine/tests/test_autoresearch.py` | 6 | 67% |
| `apps/cron-dispatcher/src/index.ts` | `apps/engine/tests/test_workflow_schedule.py` | 6 | 55% |
| `apps/cron-dispatcher/wrangler.jsonc` | `apps/engine/tests/test_workflow_schedule.py` | 6 | 55% |
| `apps/web/src/features/memories/components/MemoryCard.test.tsx` | `apps/web/src/features/memories/components/MemoryCard.tsx` | 5 | 100% |

## Usage Guidelines for LLM Agents

When planning or modifying files listed in this report:
1. **CRITICAL / HIGH Risk Files**: Always write a reproduction test first. Check blast radius and avoid adding new procedural responsibilities.
2. **Coupled Files**: When editing one side of a temporal pair, inspect the coupled partner to ensure shared state, schemas, or tests stay in sync.
3. **Refactoring Priority**: Files with high fix ratios (>30%) are primary candidates for modularization.

## Related
* [[concepts/visual-planning]]
* [[overview]]
