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
- **FRED Macro Client** (`core/fred.py`) — Federal Reserve Economic Data time series client with Supabase database caching (`fred_series_cache`), alias maps across 4 indicator packs, and `get_macro_economic_series` tool integration (see [[concepts/macroeconomic-data-fred]])
- **LLM Handlers** (`core/llm/handlers/`) — provider-specific tool-calling with OpenAI, Anthropic, Gemini, DeepSeek, and MiniMax-M3 (via Anthropic SDK on MiniMax's Anthropic-compatible endpoint; see [[concepts/minimax-portfolio]])
- **LLM Client Factories** (`core/llm/clients.py`) — registry mapping each provider name to an `instructor`-wrapped SDK client. SDK choice is non-obvious and follows the upstream provider's compatible SDK:

  | Provider | Model | SDK | Reason |
  |---|---|---|---|
  | `openai` | GPT-4o / GPT-5.6 Luna | `AsyncOpenAI` | native (requires `reasoning_effort="none"` when using tool schemas on `/v1/chat/completions`) |
  | `anthropic` | Claude | `AsyncAnthropic` | native |
  | `deepseek` | DeepSeek | `AsyncOpenAI` | DeepSeek exposes an OpenAI-compatible API |
  | `gemini` | Gemini | `google.genai.Client` | native |
  | `minimax` | MiniMax-M3 | `AsyncAnthropic` | MiniMax exposes an Anthropic-compatible API; gives us native `tool_use` blocks + thinking control |

  `CLIENT_FACTORIES` is populated at import time, so tests must patch the dict (not the module-level factory functions) — see `tests/test_call_counts.py` for the established pattern.
- **Execution** (`execution/`) — validation, Reg T checks, portfolio management (and the simplified market-order pipeline for MiniMax)
- **Memory** (`memory/`) — pgvector embeddings, RAG retrieval, deduplication
- **Attribution** (`attribution/`) — decision persistence and trade linking
- **Auto-Research** (`autoresearch/`) — weekly autonomous prompt improvement via meta-researcher LLM (`prompt_store.py` handles PostgREST single-row query exceptions gracefully)

- **Prompt Factory** (`core/llm/prompt_factory.py`) — Centralized prompt assembly handling provider adaptations, web search instruction stripping, dynamic tool registration, and ledger injection.

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
- [[concepts/macroeconomic-data-fred]]
- [[entities/autoresearch]]
- [[sources/correlation-matrix-source]]
