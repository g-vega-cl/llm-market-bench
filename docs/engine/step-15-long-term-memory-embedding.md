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
Every time a model generates a trading decision (BUY/SELL/HOLD), its reasoning string is vectorized.
- **Content Format**: `DECISION REASONING: [Ticker] [Signal] | REASONING: [Full LLM Reasoning]`
- **Type**: `decision_reasoning`

### 3. Metadata Schema
Rich metadata is attached to each memory to enable filtered retrieval:

| Field | Description |
| --- | --- |
| `type` | `"consensus_event"` or `"decision_reasoning"` |
| `ticker` | The stock symbol (for reasoning) |
| `model_name` | The specific model that generated the thought (e.g., `gpt-4o`) |
| `source_id` | Foreign key to the original newsletter snapshot |
| `trade_id` | Foreign key to the executed trade record (if applicable) |
| `status` | `ACTIVE`, `RESOLVED`, or `SUPERSEDED` (for memory chains) |
| `relevance_score` | Decay multiplier (default: 1.0, halves every 30 days) |

## Pipeline Integration

The logic is integrated into `apps/engine/main.py` immediately after a decision is successfully saved to the attribution layer.

```python
# Create memory content
memory_content = f"DECISION REASONING: {d.ticker} {d.signal} | REASONING: {d.reasoning}"

# Vectorize and save to pgvector
add_memory(
    content=memory_content,
    metadata={
        "type": "decision_reasoning",
        "ticker": d.ticker,
        "model_name": d.model_name,
        "source_id": d.source_id,
        "trade_id": str(trade_id) if trade_id else None
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
