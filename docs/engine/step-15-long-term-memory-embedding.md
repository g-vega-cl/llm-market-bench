# Step 15: Long-term Memory Embedding (Walkthrough)

This document describes the implementation of the Long-term Memory Embedding layer, which ensures that both synthesized market events and individual trade reasoning are persisted in the vector store for future RAG retrieval.

## Overview

Previously, Step 15 focused on "Consolidated Reasoning" where multiple model outputs were merged and stored in the `memories` table. To keep the `memories` table strictly focused on **Global Macro Events**, we have decoupled the architecture. 

Individual trade reasoning is now stored and embedded directly within the `decisions` table. This allows the engine to preserve the unique perspective of each model while keeping the "Global Market Timeline" clean.

## Technical Implementation

### 1. Decoupled Vector Storage
The engine now utilizes two distinct sources for institutional memory:

| Source | Content Type | Vector Table | Label in RAG |
| --- | --- | --- | --- |
| **Market Events** | Macro catalysts, Geopolitics | `memories` | `[MARKET EVENT]` |
| **Trade Reasoning** | Specific stock justifications | `decisions` | `[PAST DECISION]` |

### 2. Implementation Flow

#### A. Trade Reasoning Attribution (Step 7/15)
When a model generates a trading decision (BUY/SELL), the `save_decision` service automatically generates an embedding for its `reasoning` text.
- **Provider**: Google Gemini (`text-embedding-004`)
- **Storage**: `decisions.embedding` (VECTOR 768)

#### B. Macro Events (Step 8)
Synthesized professional market events are still promoted to the `memories` table after consensus.
- **Content Format**: `MARKET EVENT: [Event Name] | IMPACT: [Impact] | SUMMARY: [Summary]`

### 3. Retrieval Optimization (Dual-Search)

During the RAG retrieval phase (Step 6), the `store.py` logic performs a parallel search:
1. It queries `match_memories` to find relevant macro environment history.
2. It queries `match_decisions` to find relevant past trades or logic that might inform the current ticker.

These are then combined and injected into the LLM prompt, giving the model a rich, multi-layered "memory" of both the world and its own previous actions.

## Pipeline logic update

We have **removed** the redundant synthesis step that used to merge reasonings into the `memories` table. This reduces LLM API costs and prevents "Vector Noise" in the macro timeline.

```python
# attribution/service.py
def save_decision(...):
    payload = {
        "reasoning": decision.reasoning,
        "embedding": get_embedding(decision.reasoning) # Direct embedding
    }
    client.table("decisions").upsert(payload)
```

## Verification

### Automated Testing
You can verify the combined retrieval logic by running the RAG test suite:
```bash
python3 tests/test_memory_rag.py
```
This test confirms that both `[MARKET EVENT]` and `[PAST DECISION]` entries are correctly retrieved and merged for a given query.
