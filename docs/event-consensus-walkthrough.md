# Event Consensus Protocol Walkthrough

The **Event Consensus Protocol** is the mechanism that allows the engine to identify significant market themes across multiple LLM analyses and promote them to the **Global Timeline** (long-term memory).

## How It Works

The protocol runs in four distinct stages after the parallel LLM analysis is complete:

### 1. Semantic Grouping
Because different LLMs use different terminology (e.g., "Fed Hike" vs. "Interest Rate Increase"), the engine uses **Gemini Embeddings (`text-embedding-004`)** and **Cosine Similarity** (threshold > 0.85) to cluster events that signify the same real-world catalyst.

### 2. Consensus Determination
An event group only reaches "Consensus" if it is identified by at least **2 out of 4** distinct LLM models. This filters out hallucinations or niche observations from individual models.

### 3. Temporal Deduplication
To prevent "RAG noise" and redundant signals, the engine queries the `memories` table to check if a semantically similar event was already promoted in the last **48 hours**. If a match is found, the new event is discarded.

### 4. LLM Synthesis
For groups that reach consensus, a final "Analyst Pass" (via OpenAI GPT-4o-mini) is performed to:
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
| `source_ids` | List of newsletter chunk IDs that contributed to this consensus |
| `raw_name` | The original representative name from the first model in the cluster |

## Verification

You can verify the protocol is working by checking the engine logs:

```text
INFO: Consensus reached on semantic event group: 'Fed Rate Hike' (3 models)
INFO: Promoted synthesized consensus event: 'Fed Signals Tightening Bias'
```

Unit tests are located in `apps/engine/tests/test_consensus.py`.
