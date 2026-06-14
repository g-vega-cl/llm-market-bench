# Wiki Index

## Overview

- [[overview]] — High-level project synthesis

## Entities

- [[entities/global-background]] — Fixed ambient background with dot grid and glowing orbs for the full application
- [[entities/mcp-posthog]] — Local plugin wrapper for the hosted PostHog MCP server
- [[entities/shader-background]] — WebGL shader background component with 4 animated visual themes mapped to a PostHog A/B test
- [[entities/mcp-knowledge-rag]] — Local MCP server for semantic search (RAG) against external Supabase knowledge base via Gemini embeddings
- [[entities/academic-paper-seeding]] — Seeds top 10 empirical asset pricing papers into pgvector memory store for RAG grounding
- [[entities/autoresearch-arena]] — Web UI for browsing prompt experiment history and scoring methodology
- [[entities/design-system]] — Shared UI component library (primitives, patterns, layouts, design tokens)
- [[entities/cleanup]] — Database cleanup module for periodic maintenance
- [[entities/biome-lint-scripts]] — Batch-fix scripts for Biome lint rules (useButtonType, noSvgWithoutTitle)
- [[entities/biome-linter]] — TypeScript/JS linter and formatter (biome) for the web app and packages
- [[entities/wiki-linter]] — Structural and LLM-powered wiki quality assurance
- [[entities/ruff-linter]] — Python linter and formatter (ruff) for the engine
- [[entities/auto-wiki]] — Auto-wiki documentation generator (pre-commit LLM integration)
- [[entities/engine]] — Python data engine (pipeline, analysis, execution)
- [[entities/web-app]] — TanStack Start dashboard (React + TypeScript)
- [[entities/database]] — Supabase PostgreSQL schema (pgvector, RLS)
- [[entities/pipeline]] — Full daily pipeline from ingestion to feedback
- [[entities/autoresearch]] — Karpathy-style autonomous prompt improvement loop
- [[entities/macro-tracker]] — 23-ticker global macro regime monitoring
- [[entities/gemini]] — Project-level mandates, precedence directives, and command reference

## Concepts

- [[concepts/posthog-stealth-proxy]] — Same-origin reverse proxy architecture to bypass ad blockers for PostHog analytics
- [[concepts/system-heavy-prompt]] — System-Heavy architecture: System Prompt = rulebook, User Prompt = data injector
- [[concepts/type-safety]] — Strict TypeScript type safety with zero any usage
- [[concepts/tanstack-query]] — TanStack Query patterns, active/unused factories, and SSR-safe QueryClient setup
- [[concepts/model-anomalies]] - Catalog of observed LLM behavioral anomalies (empty responses, zero decisions)
- [[concepts/equal-weighted-returns]] — Per-agent percentage returns averaged equally regardless of portfolio size
- [[concepts/observability-standard]] — Traceback hardening and granular pipeline tracking for LLM audits
- [[concepts/project-linting]] — Code quality enforcement: Ruff (Python) + Biome (TypeScript) in pre-commit
- [[concepts/code-reference-validation]] — Deterministic codebase path validation and linter scope analysis
- [[concepts/test-coverage]] — Enforced coverage thresholds (70% engine / 40% web)
- [[concepts/ingestion]] — Newsletter scraping, economic calendar, government tracking
- [[concepts/reasoning]] — Parallel LLM analysis with tool-calling loops
- [[concepts/consensus]] — Semantic grouping, weighted voting, event promotion
- [[concepts/execution]] — Pre-market validation, Reg T checks, trade settlement
- [[concepts/alpaca-order-sync]] — Decoupled Alpaca order status sync (SUBMITTED → FILLED via daily cron)
- [[concepts/memory-feedback]] — Post-mortem, contrarian analysis, cause & effect
- [[concepts/agent-workflow]] — Mandatory Search/Plan/TDD sequence for all agents
- [[concepts/agents]] — Comprehensive role and tool breakdown for all 8 specialized agents
- [[concepts/state-ledger-injection]] — Aggregating historical thesis/decisions into the active prompt for context retention
- [[concepts/auto-research-prompt-improver]] — Weekly autonomous prompt iteration via meta-researcher LLM
- [[concepts/tool-enforcement]] — 4-layer hallucination prevention system
- [[concepts/rag-strategy]] — Tiered context injection and per-agent RAG
- [[concepts/minimax-portfolio]] — Simplified execution model & ±0.5% market order buffer for MiniMax-M3
- [[concepts/supabase-grant-convention]] — Explicit GRANTs required for PostgREST Data API access
- [[concepts/performance-auditing-strategy]] — Cloud-native edge performance auditing with Netlify Lighthouse budgets
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR decision frameworks, patterns, and live examples
- [[concepts/mcp-setup]] — Setup, configuration, plugin management, and caching details for Model Context Protocol (MCP) servers
- [[concepts/fundamental-analysis]] — Standardized fundamental key metrics to prevent filings context bloat




## Sources

- [[sources/project-overview-source]] — Multi-agent benchmarking platform goals
- [[sources/data-flow-source]] — The 6-phase daily pipeline lifecycle
- [[sources/tool-enforcement-source]] — 4-layer hallucination prevention
- [[sources/reg-t-calculations-source]] — Margin account formulas & guardrails
- [[sources/database-schema-source]] — Supabase table structures & pgvector RPCs
- [[sources/government-incentives-source]] — High-impact policy tracking criteria
- [[sources/market-heuristics-source]] — Trading patterns and mental models
- [[sources/semantic-overlap-source]] — Per-agent redundancy checking
- [[sources/engine-testing-source]] — Zero-warning policy & DI patterns
- [[sources/pnl-methodology-source]] — Weighted average cost basis logic
- [[sources/web-search-source]] — Provider-specific search config
- [[sources/correlation-matrix-source]] — Uncorrelated asset discovery
- [[sources/anomaly-detector-source]] — Static & dynamic code auditing
- [[sources/web-architecture-source]] — Vertical feature slicing with TanStack
- [[sources/web-design-system-source]] — "Bloomberg Terminal meets Wired" UI
- [[sources/web-portfolios-source]] — Active/Retired classification & D3 charts
- [[sources/web-query-patterns-source]] — Query options factory & SSR safety
- [[sources/web-testing-source]] — Vitest & RTL component colocation
- [[sources/web-deployment-source]] — Netlify serverless deployment

## Interactions

- [[interactions/wiki-proper-setup-audit]] — Audit of Karpathy-style wiki requirements
