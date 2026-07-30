---
tags: [project, overview, synthesis]
category: synthesis
---

# LLM Market Bench

A fully transparent live arena where LLMs debate, trade, and compete.
Multiple times daily during US market hours, they parse financial newsletters,
debate events, and rebalance portfolios — with meta-agents reviewing consensus
afterward.

## Architecture

The platform is a monorepo with three layers:

- **Python Data Engine** (`apps/engine/`) — the pipeline that ingests news,
  runs LLM analysis, builds consensus, validates trades, and executes them
- **TanStack Start Dashboard** (`apps/web/`) — React/TypeScript frontend for
  real-time portfolio data, trade audit trails, and LLM cognitive synthesis
- **Supabase PostgreSQL** — the database layer with pgvector for semantic
  search, RLS for security, and migrations for schema management

## Pipeline Overview

The daily pipeline runs on a cron schedule during US market hours in six phases:

1. **Ingestion** — fetch newsletters, economic calendar, government data
2. **Pre-Analysis** — market hours check, dust cleanup, macro tracking (23 tickers across 6 categories: equities, international, commodities, fixed income, FX/risk, crypto)
3. **Analysis** — parallel LLM analysis with tool-calling loops (and raw JSON parsing for MiniMax)
4. **Consensus** — semantic grouping, event promotion, trend tracking
5. **Execution** — validation, Reg T checks, trade settlement, attribution (including standard limit orders and a simplified market order pipeline for MiniMax with ±0.5% buffer)
6. **Feedback** — post-mortem, contrarian analysis, cause & effect, and
   weekly auto-research prompt improvement

See [[entities/pipeline]] for the full walkthrough.

## Core Tenets

- **Information Auditability**: Every piece of data, metric, trade, and portfolio state is fully auditable. If someone asks "How was this calculated?" or "Where did this come from?", they can trace it directly to raw source inputs, LLM outputs, tool execution history, or specific mathematical formulas. See [[concepts/auditability]].

## Key Design Decisions

- **Pre-injected market data**: Prices are fetched and injected into prompts
  before the LLM reasons, eliminating price hallucination entirely
- **Tiered context**: Analysis agents get lightweight context; the verifier gets
  targeted per-trade RAG scoped to the same agent's past decisions
- **Atomic settlement**: "Commit at the End" pattern prevents phantom deductions
- **4-layer tool enforcement**: Server-side conversation scanning confirms
  quantity tools were actually called via native function calling (bypassed for the simplified MiniMax model pipeline)

- **Auto-research loop**: A meta-researcher LLM evaluates weekly live trading
  performance and iteratively improves the trading prompt, following Karpathy's
  autonomous research pattern

## Related

- [[entities/engine]]
- [[entities/web-app]]
- [[entities/database]]
- [[entities/pipeline]]
- [[concepts/tool-enforcement]]
- [[concepts/minimax-portfolio]]
- [[concepts/rag-strategy]]
