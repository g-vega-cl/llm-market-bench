# Step 15: Long-term Memory Embedding (Walkthrough)

This document describes the implementation of the Long-term Memory Embedding layer, which ensures that both synthesized market events and individual trade reasoning are persisted in the vector store for future RAG retrieval.

## Overview

While Step 7 and Step 12 focus on the "Audit Trail" (News → Decision → Trade), Step 15 focuses on "Institutional Memory." By vectorizing the reasoning behind every decision, the engine allows AI models to "remember" their past logic when analyzing new newsletters, ensuring consistency across trading sessions.

## Technical Implementation

### 1. Unified Vector Store
All memories are stored in the same Supabase `pgvector` table used for news retrieval.
- **Table**: `memories`
- **Embedding Model**: Google Gemini (`text-embedding-004`)
- **Dimensions**: 768

### 2. Dual-Layer Embedding
The engine performs embeddings at two distinct points in the pipeline:

#### A. Consensus Events (Step 8 Logic)
When two or more models reach consensus on a macro event, a synthesized professional summary is generated and embedded.
- **Content Format**: `MARKET EVENT: [Event Name] | IMPACT: [Impact] | SUMMARY: [Summary]`
- **Type**: `consensus_event`

#### B. Trade Reasoning (Step 15 Logic)
When one or more models generate a trading decision (BUY/SELL), the engine groups them by ticker and signal. A single **Consensus Reasoning** block is synthesized from the contributing models and embedded. This prevents vector noise from near-identical entries.
- **Content Format**: `DECISION REASONING: [Ticker] [Signal] | CONSENSUS REASONING: [Synthesized Summary]`
- **Type**: `decision_reasoning`

### 3. Metadata Schema
Rich metadata is attached to each memory to enable filtered retrieval:

| Field | Description |
| --- | --- |
| `type` | `"consensus_event"` or `"decision_reasoning"` |
| `ticker` | The stock symbol (for reasoning) |
| `models_involved` | List of models that contributed to this consensus (e.g., `["openai_gpt-4o", "claude-3-5-sonnet"]`) |
| `source_ids` | List of original newsletter chunk IDs |
| `status` | `ACTIVE`, `RESOLVED`, or `SUPERSEDED` (for memory chains) |
| `relevance_score` | Decay multiplier (default: 1.0, halves every 30 days) |

## Pipeline Integration

The logic is integrated into `apps/engine/main.py`. It collects all actionable decisions, calls `process_decision_consensus`, and saves the result to `memories`.

```python
# Collect actionable decisions during the main loop
actionable_decisions.append(d)

# After all models finish:
consolidated_reasonings = await process_decision_consensus(actionable_decisions)
for cr in consolidated_reasonings:
    add_memory(
        content=f"DECISION REASONING: {cr['ticker']} {cr['signal']} | CONSENSUS REASONING: {cr['reasoning']}",
        metadata={
            "type": "decision_reasoning",
            "ticker": cr['ticker'],
            "signal": cr['signal'],
            "models_involved": cr['models_involved'],
            "source_ids": cr['source_ids']
        }
    )
```

## Verification & Retrieval

### Automated Testing
You can verify that reasoning is correctly being "remembered" by running:
```bash
python3 tests/verify_step_15.py
```

### Retrieval Pattern
During the next day's run, Step 6 (Context Retrieval) uses the same `text-embedding-004` model to query the `memories` table. Because the embeddings are consistent, today's reasoning becomes tonight's "Historical Context" for the LLM.

### Memory Optimization
The retrieval system includes two optimization mechanisms:
1. **Status Filtering**: Only `ACTIVE` memories are retrieved. Memories marked as `RESOLVED` are excluded from LLM context.
2. **Relevance Decay**: The `match_memories` RPC multiplies similarity scores by `relevance_score`, which decays by 50% every 30 days. This ensures old information has diminishing impact over time.
