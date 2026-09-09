---
tags: [consensus, event-promotion, historical-parallel]
category: concept
---

# Consensus

Semantic grouping, weighted voting, event promotion, and structured historical parallel synthesis.

## Overview

The consensus engine aggregates model observations into coherent events, resolves conflicts via weighted voting, and promotes high-signal events to long-term memory. It now also synthesizes structured historical parallels from candidate precedents identified by models.

## Phases

### 1. Semantic Grouping

Events are grouped by semantic similarity using embeddings. Groups with sufficient cumulative weight proceed to synthesis.

### 2. Weighted Voting

Within each group, models vote on impact (bullish/bearish/neutral), confidence, and whether the event is ongoing or a future catalyst. Votes are weighted by model reliability.

### 3. Structured Historical Parallel Synthesis

When models or news cite historical precedents, the Arbiter (via `synthesize_event`) produces a structured `HistoricalParallelDetail` object:

- **title**: Concise name of the historical episode (e.g., "2024 Red Sea Tanker Disruptions")
- **timeframe**: Era or date window (e.g., "Jan - Mar 2024")
- **precedent**: What happened historically
- **market_reaction**: How asset prices, commodities, or sectors reacted
- **takeaway**: Actionable lesson or risk playbook for today
- **affected_assets**: List of relevant ticker symbols or asset classes

Candidate parallels from individual model observations are collected and passed to the LLM synthesizer via the `candidate_parallels` parameter. The synthesizer selects the single best parallel and enriches it with structured fields. If no parallel is identified, the field is null.

### 4. Memory Persistence

The structured historical parallel is stored in `metadata.historical_parallel` when the event is promoted to long-term memory. The memory content string includes a formatted tag like `[Historical Parallel: 2024 Red Sea Tanker Disruptions (Jan - Mar 2024)]`.

### 5. Event Promotion

Events meeting importance and confidence thresholds are promoted to long-term memory with full metadata, including the structured historical parallel, scenarios, and discovered assets.

## Related

- [[concepts/memory-feedback]]
- [[entities/engine]]
- [[concepts/rag-strategy]]
