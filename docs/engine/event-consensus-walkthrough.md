# Event Consensus Protocol Walkthrough

The **Event Consensus Protocol** is the mechanism that allows the engine to identify significant market themes across multiple LLM analyses and promote them to the **Global Timeline** (long-term memory).

## How It Works

The protocol runs in four distinct stages after the parallel LLM analysis is complete:

### 1. Semantic Grouping
Because different LLMs use different terminology (e.g., "Fed Hike" vs. "Interest Rate Increase"), the engine uses **Gemini Embeddings (`text-embedding-004`)** and **Cosine Similarity** (threshold > 0.85) to cluster events that signify the same real-world catalyst.

### 2. Weighted Consensus Determination
An event group reaches "Consensus" based on the **Cumulative Model Weight** of the models that identified it. 

- **Weighting**: Each model (OpenAI, Claude, etc.) has a configured weight in `config.py` (Default: 1.0).
- **Threshold**: The cumulative weight must be $\ge 2.0$ for the event to be promoted.
- **Tie-Breaking**: When models disagree on the **Impact** (BULLISH vs. BEARISH), the system calculates a weighted majority rather than a simple vote count. This ensures more sophisticated models have a proportional influence on the final synthesized signal.

### 3. Temporal Deduplication
To prevent "RAG noise" and redundant signals, the engine queries the `memories` table to check if a semantically similar event was already promoted in the last **48 hours**. If a match is found, the new event is discarded.

### 4. Relationship Analysis & Memory Chains
For events that reach consensus, the engine performs a "Relationship Analysis" before promotion:
- **Ancestor Search**: Queries the `memories` table for semantically related past events (Similarity > 0.4).
- **LLM Relationship Check**: A fast LLM pass (`analyze_event_relationship`) determines if the new event is a `REVERSAL`, `RESOLUTION`, or `UPDATE` of any found ancestors.
- **Linking**: The new memory is linked via `parent_id`.
- **Auto-Resolution**: If the relationship is a `REVERSAL` or `RESOLUTION`, the ancestor is automatically marked as `RESOLVED`. This prevents outdated narratives from cluttering upcoming RAG analyses.

### 5. Memory Optimization & Future Event Tracking
After linking and resolution, the system applies two additional optimizations:

**A. Memory Status Filtering:**
- Memories marked as `RESOLVED` are excluded from future LLM context retrieval
- Only `ACTIVE` memories influence new analyses
- This keeps RAG context focused on current, relevant events

**B. Relevance Decay:**
- Each memory has a `relevance_score` (default: 1.0)
- Every 30 days, old memories have their score halved (1.0 → 0.5 → 0.25 → ...)
- The `match_memories` RPC multiplies similarity by `relevance_score`, reducing old information's impact
- Decay stops when score drops below 0.05

**C. Future Event Extraction:**
- During synthesis, the LLM checks for explicitly mentioned future dates
- Examples: "Q3 2026", "next summer", "November 20th", "by June"
- If found, saved to `future_events` table with:
  - `event_name`: The synthesized event name
  - `target_date`: The extracted timeframe
  - `description`: Event summary
  - `source_memory_id`: Link to the parent memory
- Enables proactive positioning for upcoming events like product releases, elections, or regulatory approvals

### 6. LLM Synthesis
A final "Analyst Pass" (via Google Gemini) is performed to:
- Create a professional, unified **Event Name** (max 5 words).
- Write a 1-sentence **Summary** capturing the catalyst and market implication.
- Consolidate reasoning from all contributing models.

## Data Schema & Storage

Consensus events are stored in the `memories` table with the following metadata:

| Field | Description |
| --- | --- |
| `type` | Set to `"consensus_event"` |
| `event_name` | The final synthesized professional name |
| `impact` | Majority vote impact (BULLISH/BEARISH/NEUTRAL) |
| `status` | `ACTIVE`, `RESOLVED`, or `SUPERSEDED` |
| `parent_id` | UUID of the linked ancestor memory |
| `relationship_type` | `REVERSAL`, `UPDATE`, `RESOLUTION`, or `GENERAL` |
| `source_ids` | List of newsletter chunk IDs that contributed to this consensus |
| `raw_name` | The original representative name from the first model in the cluster |
| `relevance_score` | Decay multiplier for context retrieval (default: 1.0, halves every 30 days) |

### Future Events Table

| Field | Description |
| --- | --- |
| `id` | UUID |
| `event_name` | The synthesized event name |
| `target_date` | Extracted future timeframe (e.g., "Q3 2026", "next summer") |
| `description` | Event summary |
| `source_memory_id` | Link to the parent memory in the `memories` table |

## Verification

You can verify the protocol is working by checking the engine logs:

```text
INFO: Consensus reached on semantic event group: 'Fed Rate Hike' (3 models)
INFO: Promoted synthesized consensus event: 'Fed Signals Tightening Bias'
```

Unit tests are located in `apps/engine/tests/test_consensus.py`.
