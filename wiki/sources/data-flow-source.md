---
tags: [engine, pipeline, data-flow]
category: source
---

# Source: Data Flow & Pipeline Reference

Synthesized from `raw/docs/engine/data-flow.md`.

## Takeaways

- **6-Phase Lifecycle**: The pipeline moves from Ingestion $\to$ Pre-Analysis $\to$ Analysis $\to$ Consensus $\to$ Execution $\to$ Feedback.
- **Atomic Settlement**: Uses a "Commit at the End" pattern to ensure ledger integrity, preventing phantom cash deductions if database operations fail mid-run.
- **Context Management**: Employs a tiered context retrieval system. Analysis agents get a lightweight "top-5" memory summary, while Verifiers get a deep, targeted RAG search per trade.
- **Deduplication**: Robust idempotency via `source_id` (meta-based) and `chunk_hash` (content-based) prevents redundant processing of newsletter data.

## Related

- [[entities/pipeline]]
- [[entities/engine]]
- [[concepts/ingestion]]
- [[concepts/consensus]]
