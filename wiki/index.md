# Wiki Index

## Overview

- [[overview]] — High-level project synthesis

## Entities

- [[entities/massive-options]] — Auto-indexed page
- [[entities/tool-registry]] — Centralized canonical tool registry (packages/config/tools.json)
- [[entities/hotspots]] — Git churn forensics and code hotspot analyzer
- [[entities/investment-chat-gateway]] — Gated conversational agent with real-time memory and database access
- [[entities/chat-tools]] — Server-side tool definitions and handlers for the Investment Chat Gateway
- [[entities/investment-chat-gateway]] — Auto-indexed page
- [[entities/alpaca-audit]] — Alpaca portfolio reconciliation audit engine
- [[entities/daily-score-breakdown]] — Interactive score calculation and breakdown component for daily ratchet score auditability
- [[entities/lin-renko-agent]] — Auto-indexed page
- [[entities/generated-newsletters]] — Auto-generated daily market briefings with 6-minute read target (~1,200–1,500 words) and 5-section macro/sector/internals/trade/catalyst structure
- [[entities/cron-dispatcher]] — Cloudflare Worker edge cron dispatcher for GitHub Actions workflows
- [[entities/daily-predictor-backtest-arena]] — Web UI and engine backtest system for S&P 500 daily open-to-close predictions with prompt mutation
- [[entities/daily-market-predictor]] — Auto-indexed page
- [[entities/backtest-arena]] — Web UI for browsing backtest prompt experiments and mutation history
- [[entities/git-history]] — Automated Git history export to structured Markdown with QMD indexing
- [[entities/commit-msg-lint]] — Conventional Commits enforcement via pre-commit hook
- [[entities/ai-feeling-card]] — AI market sentiment card on the Today dashboard with buy/sell split, confidence bar, and stale detection
- [[entities/market-barometer-audit]] — S&P 500 Market Health Barometer audit page with constituent-level data browser
- [[entities/global-background]] — Fixed ambient background with dot grid and glowing orbs for the full application
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
- [[entities/sector-predictor-arena]] — Weekly top and worst sector predictions with S&P 500 alpha scoring and model arena dashboard
- [[entities/llm-leaderboard]] — LLM ranking and diagnostic screening system (composite scoring, verifier rates, and consistency metrics)
- [[entities/gemini]] — Project-level mandates, precedence directives, and command reference

## Concepts

- [[concepts/release-and-canary-deployments]] — Auto-indexed page
- [[concepts/hybrid-database-archival]] — Auto-indexed page
- [[concepts/code-hotspots]] — Auto-indexed page
- [[concepts/unslop-editing]] — Structured editing skill for removing AI pattern tells and injecting human voice
- [[concepts/wayfinder]] — Planning methodology for decomposing large work into tracked decision tickets
- [[concepts/system-portfolios]] — Auto-indexed page
- [[concepts/macroeconomic-data-fred]] — Auto-indexed page
- [[concepts/magnitude-calibration]] — Magnitude capture ratio and postmortem diagnosis for daily S&P prediction prompt evolution
- [[concepts/deepseek-web-search]] — Live web search tool integration for DeepSeek agents with DuckDuckGo/FMP hybrid backend
- [[concepts/worst-sector-scoring]] — Two-sided sector prediction, worst sector percentile scoring, and S&P 500 alpha bonus
- [[concepts/brier-score]] — Brier score calibration metric and autoresearch penalty
- [[concepts/renko-atr-sizing]] — Auto-indexed page
- [[concepts/modular-prompt-blocks]] — Reusable trading discipline and reasoning blocks dynamically toggled by the Auto-Researcher
- [[concepts/intraday-hit-metrics]] — Two-dimensional evaluation for daily predictions measuring intraday price target achievement
- [[concepts/thematic-rotation]] — Adjacent trade pattern, stranded-asset pivot, and AI intra-cycle rotation sequence (infra → hyperscalers)
- [[concepts/verifier-bypass]] — Configurable model-level bypass of the skeptical verification agent stage
- [[concepts/stochastic-cold-start]] — Randomized cold-start resets (2–5 week intervals) to escape local optima in prompt optimization
- [[concepts/multi-track-autoresearch]] — Parallel isolated prompt optimization tracks for distinct portfolio groups
- [[concepts/prompt-section-splitting]] — Visual decomposition of the trading prompt into frozen and mutable sections for the autoresearch arena
- [[concepts/git-history-tracking]] — Git history as the authoritative chronological record, replacing wiki log.md
- [[concepts/output-normalization]] — LLM output sanitization via Pydantic validators for signal/catalyst/impact/status resilience
- [[concepts/auditability]] — Philosophy and mechanisms of full calculation and data traceability
- [[concepts/posthog-stealth-proxy]] — Same-origin reverse proxy architecture to bypass ad blockers for PostHog analytics
- [[concepts/system-heavy-prompt]] — System-Heavy architecture: System Prompt = rulebook, User Prompt = data injector
- [[concepts/type-safety]] — Strict TypeScript type safety with zero any usage
- [[concepts/tanstack-query]] — TanStack Query patterns, active/unused factories, and SSR-safe QueryClient setup
- [[concepts/model-anomalies]] - Catalog of observed LLM behavioral anomalies (empty responses, zero decisions)
- [[concepts/market-anomalies]] — Catalog of empirical market anomalies, factors, and plumbing-driven price effects
- [[concepts/equal-weighted-returns]] — Per-agent percentage returns averaged equally regardless of portfolio size
- [[concepts/observability-standard]] — Traceback hardening and granular pipeline tracking for LLM audits
- [[concepts/project-linting]] — Code quality enforcement: Ruff (Python) + Biome (TypeScript) in pre-commit
- [[concepts/code-reference-validation]] — Deterministic codebase path validation and linter scope analysis
- [[concepts/test-coverage]] — Enforced coverage thresholds (70% engine / 40% web)
- [[concepts/ingestion]] — Newsletter scraping, economic calendar, government tracking
- [[concepts/reasoning]] — Parallel LLM analysis with the Reasoning Toolbox (5 Whys, MECE, IS/IS NOT, Ishikawa)
- [[concepts/consensus]] — Semantic grouping, weighted voting, event promotion
- [[concepts/execution]] — Pre-market validation, Reg T checks, trade settlement
- [[concepts/alpaca-order-sync]] — Decoupled Alpaca order status sync (SUBMITTED → FILLED via daily cron)
- [[concepts/memory-feedback]] — Post-mortem, contrarian analysis, cause & effect
- [[concepts/agent-workflow]] — Mandatory Search/Plan/TDD sequence for all agents
- [[concepts/visual-planning]] — Terminal-native visual planning using Unicode box-drawing, flowcharts, and tables
- [[concepts/agents]] — Comprehensive role and tool breakdown for all 8 specialized agents
- [[concepts/state-ledger-injection]] — Aggregating historical thesis/decisions into the active prompt for context retention
- [[concepts/auto-research-prompt-improver]] — Weekly autonomous prompt iteration via meta-researcher LLM
- [[concepts/tool-enforcement]] — 4-layer hallucination prevention system
- [[concepts/rag-strategy]] — Tiered context injection and per-agent RAG
- [[concepts/minimax-portfolio]] — Simplified execution model & ±0.5% market order buffer for MiniMax-M3
- [[concepts/supabase-grant-convention]] — Explicit GRANTs required for PostgREST Data API access
- [[concepts/supabase-redirect-whitelisting]] — Supabase OAuth redirect whitelisting rules and local dev proxy port configuration
- [[concepts/performance-auditing-strategy]] — Cloud-native edge performance auditing with Netlify Lighthouse budgets
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR decision frameworks, patterns, and live examples
- [[concepts/mcp-setup]] — Setup, configuration, plugin management, and caching details for Model Context Protocol (MCP) servers
- [[concepts/fundamental-analysis]] — Standardized fundamental metrics, company earnings tools, and S&P 500 Market Health Barometer
- [[concepts/market-feeling]] — LLM-driven daily and weekend market sentiment analysis grounded in newsletters, S&P 500 barometer, prediction markets, and ticker price swings
- [[concepts/temporal-sandboxing]] — Point-in-time database client wrapping, local cache redirection, and Alpaca order simulation




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
