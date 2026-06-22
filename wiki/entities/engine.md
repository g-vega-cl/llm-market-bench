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
- **Analysis** (`analysis/`) — LLM orchestration, Discovery Agent, momentum tracking, [[sources/correlation-matrix-source]]
- **Macro Tracker** (`core/macro_tracker.py`) — 23-ticker global regime monitoring (equities, intl, commodities, fixed income, FX/risk, crypto)
- **LLM Handlers** (`core/llm/handlers/`) — provider-specific tool-calling with OpenAI, Anthropic, Gemini, DeepSeek, and MiniMax-M3 (fully integrated into the standard tool-calling and Instructor pipeline)
- **Execution** (`execution/`) — validation, Reg T checks, portfolio management (and the simplified market-order pipeline for MiniMax)
- **Memory** (`memory/`) — pgvector embeddings, RAG retrieval, deduplication
- **Attribution** (`attribution/`) — decision persistence and trade linking
- **Auto-Research** (`autoresearch/`) — weekly autonomous prompt improvement via meta-researcher LLM

## Design Principles

- **Provider-agnostic**: Each LLM provider has a dedicated handler that normalizes tool-calling idiosyncrasies
- **Cache-first**: Market data heavily cached to reduce API costs
- **Defense in depth**: Four layers of hallucination prevention (prompt, context, verification, isolation) — bypassed for the MiniMax model to allow high-velocity raw cognitive output
- **Deterministic state**: Source IDs are hash-based for idempotent UPSERTs

## Related

- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/ingestion]]
- [[concepts/reasoning]]
- [[concepts/execution]]
- [[concepts/tool-enforcement]]
- [[concepts/minimax-portfolio]]
- [[concepts/memory-feedback]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/autoresearch]]
- [[sources/correlation-matrix-source]]
