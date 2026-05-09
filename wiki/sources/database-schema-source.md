---
tags: [database, schema, pgvector]
category: source
---

# Source: Database Schema Reference

Synthesized from `raw/docs/database-schema.md`.

## Takeaways

- **Single Source of Truth**: The Supabase PostgreSQL database is the definitive record for portfolios, trades, and memories.
- **Memory Graphing**: The `memories` table supports `parent_id` links and `relationship_type` (REVERSAL, UPDATE) to allow the LLM to track how narratives evolve over time.
- **Audit Trails**: Extensive logging in `llm_reasoning_logs` and `system_audits` enables research-grade reconstruction of every AI decision.
- **Vector Search**: Custom RPC functions (`match_memories`, `match_decisions`) handle semantic retrieval with per-agent scoping to prevent cross-model data leakage.

## Related

- [[entities/database]]
- [[concepts/memory-feedback]]
- [[concepts/rag-strategy]]
