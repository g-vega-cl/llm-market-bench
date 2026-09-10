---
tags: [concepts, calendar, scenario-analysis, trading, tools, predictor, time]
category: concept
---

# Forward Calendar & Scenario Analysis

Forward Calendar & Scenario Analysis is the architectural pattern that anchors trading and prediction agents in physical time and allows them to query forward-looking catalysts, probability-weighted scenarios, and empirical playbook lessons.

## The Core Problem: Headline Myopia & Temporal Drift

Autonomous LLM agents typically suffer from two distinct failure modes:
1. **Temporal Drift**: When models run without exact timestamps or session indicators, their internal training cutoff causes ambiguity about what year, month, or time of day it is.
2. **Headline Myopia**: Models react purely to completed past news rather than anticipating scheduled catalysts ("What will happen tomorrow? What will happen next week? How can I profit from that?").

## Architecture: Push Temporal Anchor, Pull Forward Intelligence

Per Principle 8 (Tool-First, Agency-Driven Architecture in [[concepts/agent-workflow]]):
- **Push Temporal Anchor (~25 tokens)**: We inject the physical clock directly into the prompt context via `apps/engine/core/time_utils.py` (`get_current_day_info`). This includes Eastern Time (`America/New_York`), UTC, market session phase (Pre-market 04:00-09:30, Regular 09:30-16:00, Post-market 16:00-20:00, Closed/Weekend), tomorrow's exact date, and next week's date range.
- **Pull Market Intelligence via Tool**: We do not push massive forward-calendar dumps. Instead, agents are provided with `get_calendar_scenario_analysis`, which they pull on demand during research.

## Tool: `get_calendar_scenario_analysis`

Implemented in `apps/engine/analysis/calendar_scenarios.py` and registered in `packages/config/tools.json` and `CANONICAL_TOOLS_REGISTRY`:

### Parameters
- `timeframe`: `"tomorrow"`, `"next_week"` (default), `"next_14_days"`, or `"all_upcoming"`.
- `ticker`: Optional symbol filter (e.g. `SPY`, `NVDA`).
- `min_importance`: Minimum importance score (default `5` for high-impact catalysts).
- `detail`: If true, returns complete multi-scenario partitions and conditional trading plans.
- `include_historical_memories`: If true, matches past lessons learned and historical parallels from `memories`.

### Output Structure
1. **Chronological Triggers**: Events scheduled for Tomorrow and Next Week with exact release times (ET), country, and impact rating.
2. **Scenario Partitioning & Probabilities**: Probability-weighted Bull, Base, and Bear cases synthesized from consensus debate.
3. **Actionable Trading Plans & Profit Mechanisms**: Concrete conditional instructions on how to profit from each outcome.
4. **Target / Discovered Assets**: Specific investable tickers identified for each scenario.
5. **Historical Playbook Precedents**: Empirical lessons from past reactions to similar catalysts.

## Applied Across Engine Pipelines

The pattern is integrated into the 3 core decision flows:
1. **Market Portfolios (`apps/engine/analysis/analyze.py`)**: Models receive exact time and market phase in `current_day_info`, pulling forward calendar scenarios to plan multi-day allocations and risk guardrails.
2. **Daily S&P Predictor (`apps/engine/tasks/daily_predictor.py`)**: Pre-market intraday SPY prediction arena incorporates exact timestamp and tomorrow's high-impact releases into the market briefing.
3. **Sector Predictor (`apps/engine/tasks/sector_predictor.py`)**: Multi-horizon sector forecasts (7d, 30d, 60d, 90d) receive explicit horizon windows and forward calendar context, preventing blind backward-looking extrapolation.

## Autoresearch Integration

In accordance with Principle 8, baseline prompts (`CORE_ANALYSIS_SYSTEM_PROMPT`) are never polluted with hardcoded forward-calendar rules. Instead, the Autoresearcher loop is equipped with the modular block `forward_calendar_scenario_anticipation` in `apps/engine/autoresearch/prompt_blocks.py`, allowing it to test forward-anticipation hypotheses autonomously.
