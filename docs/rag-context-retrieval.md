# Step 6: RAG Context Retrieval (Walkthrough)

This document describes the implementation of the RAG (Retrieval-Augmented Generation) context retrieval layer for the AI Wall Street engine.

## Overview

Before the LLMs (OpenAI, Claude, Gemini, DeepSeek) analyze the current day's financial news, the engine now queries a vector store for relevant past events, trades, and reasoning. This ensures that the AI's reasoning is consistent with its history and takes into account long-term market events.

## Technical Implementation

### 1. Vector Store (Supabase pgvector)
We use Supabase's `pgvector` extension to store and search embeddings.
- **Table**: `memories`
- **Columns**: `id`, `content` (text), `embedding` (vector), `metadata` (jsonb), `created_at`.
- **Search Algorithm**: Cosine similarity using an HNSW index.
- **RPC Function**: `match_memories` (handles the similarity search logic).

### 2. Embedding Model (Google Gemini)
We use Google's `text-embedding-004` model to generate 768-dimensional embeddings.
- **Provider**: Google Gemini API.
- **Module**: `apps/engine/memory/embeddings.py`.

### 3. Retrieval Logic
The retrieval logic is encapsulated in `apps/engine/memory/store.py`.
- **Function**: `retrieve_context(query_text, limit=3)`.
- **Logic**:
    1.  Embed the query text (current news chunk).
    2.  Call the `match_memories` RPC on Supabase.
    3.  Return a formatted string of the most relevant past events.

### 4. Pipeline Integration
The retrieval is integrated into the parallel analysis orchestrator.
- **Module**: `apps/engine/analyze.py`.
- **Change**: Added a call to `retrieve_context` for each news chunk before dispatching tasks to the LLM providers.
- **Prompt Injection**: In `apps/engine/core/llm.py`, the retrieved context is injected into the LLM prompt under a `### Historical Context` section.

## Verification

### Automated Integration Test
A verification script was created at `apps/engine/tests/test_memory_rag.py`. It performs the following steps:
1.  Seeds a test memory (e.g., "The Federal Reserve kept interest rates unchanged...").
2.  Queries the engine with a related question ("What did the Fed do recently?").
3.  Asserts that the correct memory is retrieved.

### Manual Verification
1.  Check logs for `Starting analysis tasks...` to see the context being passed.
2.  Verify that LLM reasoning strings in the `decisions` table acknowledge the historical context when relevant.
