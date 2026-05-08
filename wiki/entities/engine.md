---
tags: [engine, python, pipeline]
category: entity
---

# Engine

The Python data engine at `apps/engine/` is the core of the platform. It
orchestrates the entire daily pipeline: ingesting financial newsletters,
distributing them to LLMs for analysis, building consensus, validating and
executing trades, and running feedback loops.

## Key Subsystems

- **Ingestion** (`ingest/`) — Gmail API fetching, ad removal, calendar scraping
- **Analysis** (`analysis/`) — LLM orchestration, Discovery Agent, momentum tracking
- **LLM Handlers** (`core/llm/handlers/`) — provider-specific tool-calling with OpenAI, Anthropic, Gemini, DeepSeek
- **Execution** (`execution/`) — validation, Reg T checks, portfolio management
- **Memory** (`memory/`) — pgvector embeddings, RAG retrieval, deduplication
- **Attribution** (`attribution/`) — decision persistence and trade linking

## Design Principles

- **Provider-agnostic**: Each LLM provider has a dedicated handler that normalizes tool-calling idiosyncrasies
- **Cache-first**: Market data heavily cached to reduce API costs
- **Defense in depth**: Four layers of hallucination prevention (prompt, context, verification, isolation)
- **Deterministic state**: Source IDs are hash-based for idempotent UPSERTs

## Related

- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/ingestion]]
- [[concepts/reasoning]]
- [[concepts/execution]]
- [[concepts/tool-enforcement]]
