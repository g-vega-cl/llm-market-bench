---
tags: [architecture, code-quality, metrics]
category: concept
---

# Code Hotspots & Architectural Friction

Living metrics generated from git history (Lookback window: **60 days ago**, Total commits analyzed: **182**).

## Top Hotspots

Files with high churn and high bug fix density represent code where changes frequently cause regressions.

| File | Churn | Bug Fixes | Fix Ratio | LOC | Hotspot Score | Risk Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/engine/tasks/daily_predictor.py` | 21 | 4 | 19.0% | 707 | 84 | **HIGH** |
| `apps/engine/tests/test_workflow_schedule.py` | 14 | 5 | 35.7% | 239 | 70 | **HIGH** |
| `apps/engine/main.py` | 20 | 3 | 15.0% | 73 | 60 | **HIGH** |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 14 | 4 | 28.6% | 264 | 56 | **HIGH** |
| `apps/engine/core/llm/tools.py` | 24 | 2 | 8.3% | 1758 | 48 | **HIGH** |
| `apps/engine/autoresearch/program.md` | 22 | 2 | 9.1% | 137 | 44 | **HIGH** |
| `packages/config/tools.json` | 21 | 2 | 9.5% | 210 | 42 | **HIGH** |
| `apps/engine/tests/test_daily_predictor.py` | 10 | 4 | 40.0% | 752 | 40 | **HIGH** |
| `apps/engine/tasks/evaluate_daily_predictions.py` | 10 | 4 | 40.0% | 290 | 40 | **HIGH** |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | 13 | 3 | 23.1% | 392 | 39 | **HIGH** |
| `apps/engine/tests/test_evaluate_daily_predictions.py` | 9 | 4 | 44.4% | 410 | 36 | **HIGH** |
| `apps/engine/scripts/update_prices.py` | 7 | 4 | 57.1% | 335 | 28 | **MEDIUM** |
| `apps/engine/tasks/daily_autoresearch.py` | 11 | 2 | 18.2% | 735 | 22 | **MEDIUM** |
| `apps/engine/execution/providers/massive.py` | 7 | 3 | 42.9% | 826 | 21 | **MEDIUM** |
| `apps/engine/tests/test_verify_skill.py` | 7 | 3 | 42.9% | 82 | 21 | **MEDIUM** |

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
| `apps/engine/autoresearch/researcher.py` | `apps/engine/core/llm/tools.py` | 12 | 50% |
| `apps/engine/core/llm/handlers/base.py` | `apps/engine/core/llm/tools.py` | 12 | 50% |
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
