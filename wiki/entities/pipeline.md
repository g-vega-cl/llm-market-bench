---
tags: [pipeline, engine, automation]
category: entity
---

# Pipeline

The daily automated pipeline that ingests financial news, runs parallel LLM analysis, builds consensus, executes trades, and provides feedback. It runs multiple times during US market hours on a cron schedule.

## Schedule

The pipeline is triggered by GitHub Actions with the following UTC cron expressions (hardcoded for EDT, UTC-4):

- **9:35 AM ET** → `35 13 * * 1-5`
- **11:35 AM ET** → `35 15 * * 1-5`
- **2:00 PM ET** → `0 18 * * 1-5`

GitHub Actions does not correctly handle DST when using the `timezone` field — it treats `America/New_York` as always UTC-5. To avoid schedule drift during summer months, the times are expressed directly in UTC for the EDT offset. During EST (winter), the pipeline will run one hour earlier in local time (8:35 AM, 10:35 AM, 1:00 PM EST). Because 8:35 AM EST is before market open, the first run will be automatically skipped.

## Phases

### 1. Ingestion
Fetch newsletters, economic calendar events, and government data. Runs the **De-Advertisement Agent** to sanitize incoming newsletter texts. See [[concepts/ingestion]].

### 2. Pre-Analysis
Market hours check, dust cleanup, and macro tracking across 23 tickers. No specialized agents run in this phase. See [[entities/macro-tracker]].

### 3. Analysis
Parallel LLM analysis with tool-calling loops. Runs 5 instances of the **Analysis Agent** (OpenAI, Anthropic, Gemini, DeepSeek, MiniMax) to generate proposed trades. Propose-phase validations run the **Verifier Agent** to double-check trades and the **Contrarian Agent** to run crowded-trade counter-actions. See [[concepts/reasoning]] and [[concepts/agent-workflow]].

### 4. Consensus
Semantic grouping of agent outputs, weighted voting, event promotion, and trend tracking. Runs the **Synthesis Agent** to consolidate proposed decisions into clean events and the **Relationship Agent** to map chronological/semantic links in the event chain graph. See [[concepts/consensus]].

### 5. Execution
Pre-market validation, Reg T checks, trade settlement, and attribution. No specialized agents run in this phase (simulated execution is programmatic). See [[concepts/execution]] and [[concepts/minimax-portfolio]].

### 6. Feedback
Post-mortem analysis, contrarian review, cause & effect tracking, and weekly auto-research prompt improvement. Runs the **Manager Agent** for multi-horizon post-mortems (generating lessons learned) and the **Cause & Effect Agent** for price-impact audits. Also triggers the weekly auto-research prompt improvement. See [[concepts/memory-feedback]] and [[entities/autoresearch]].

## Related

- [[entities/engine]]
- [[concepts/ingestion]]
- [[concepts/reasoning]]
- [[concepts/consensus]]
- [[concepts/execution]]
- [[concepts/memory-feedback]]
- [[entities/macro-tracker]]
- [[entities/autoresearch]]
