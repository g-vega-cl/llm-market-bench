---
tags: [pipeline, data-flow, phases]
category: entity
---

# Pipeline

The daily pipeline runs on a cron schedule during US market hours (`.github/workflows/ingest.yml`). It executes in seven highly optimized, sequential phases:

## Phase 1: Ingestion & Normalization
*   **Icon**: 📰
*   **Badge**: Tripled Trigger: Multiple Daily Runs
*   **Tags**: [FMP Cache, Gmail API, Trading Economics]

GitHub Actions fires the pipeline at market open, midday, and afternoon. The engine enforces a Holiday-Aware Market Hours Check via FMP API (5-minute TTL caching) to skip execution outside 09:30-16:00 ET, weekends, or US holidays.
*   Scrapes unread emails from Gmail; removes ads via Gemini Flash
*   Economic Calendar ingestion from Trading Economics (bi-weekly)
*   Data snapshotting with idempotency keys (source_id, chunk_hash) to prevent duplicate ingestion
*   FMP Market Status Check with class-level caching to avoid redundant API calls
*   Dust Cleanup: Auto-sells negligible positions before analysis to keep LLMs focused on meaningful holdings

For more details on ingestion mechanics, see [[concepts/ingestion]].

## Phase 2: Pre-Analysis Setup
*   **Icon**: ⚙️
*   **Badge**: Holiday-Aware Hours Check
*   **Tags**: [FMP Cache, Global Macro Tracker, Risk-On/Risk-Off]

Before LLM analysis, the engine prepares context and validates market conditions. It performs a Holiday-Aware Market Hours Check via FMP API (5-min TTL caching) to ensure execution only during 09:30-16:00 ET on trading days.
*   Global Macro Snapshot: Real-time quotes for 16 curated assets (broad equities, international, commodities, yields) with σ-based regime detection (Risk-On/Risk-Off at 2σ threshold)
*   Portfolio Initialization: Initializes all agent portfolios, fetches current prices for all unique holdings in parallel
*   Light Context Injection: Retrieves top-5 highest-importance memories + trending concepts (~500 tokens) — no embedding calls in hot path
*   Calendar Strategy: Injects Turn of Month and Payday Anomaly context based on current date

## Phase 3: Parallel LLM Analysis
*   **Icon**: 🤖
*   **Badge**: PromptFactory & Tools
*   **Tags**: [PromptFactory, Web Search, Stock Screener, DiscoveryAgent]

Four LLMs analyze data in parallel using the PromptFactory for semantically identical instructions. Each receives the Global Macro Snapshot for Risk-On/Risk-Off awareness.
*   Asynchronous Chunk Batching: 20 chunks per LLM call to prevent token truncation
*   Web Search: Claude (`web_search_20250305`) and Gemini (`google_search`) with automatic citations
*   Stock Screener: `run_stock_screener` tool for liquidity-filtered asset discovery
*   DiscoveryAgent: Alpha Discovery via tool-calling loop (up to 3 steps) for "Investable Assets" mapping
*   DeepSeek Thinking Mode: CoT reasoning with `reasoning_content` preservation

For more details on reasoning flows, see [[concepts/reasoning]].

## Phase 4: Consensus & Synthesis
*   **Icon**: 🧩
*   **Badge**: Cosine Clustering
*   **Tags**: [pgvector, Alpha Discovery, Scenario Analysis, Trend Momentum]

After LLM analysis, events are clustered and promoted through Semantic Grouping (pgvector cosine similarity) → weighted consensus → event promotion. Promoted events trigger Alpha Discovery for "Investable Assets" mapping.
*   Semantic Grouping: Gemini embeddings cluster events by cosine similarity across all LLMs
*   Weighted Consensus: Cumulative model weight above threshold promotes events; impact (BULLISH/BEARISH) by weighted majority
*   Temporal Deduplication: New events checked against memories table within recency window; near-duplicates dropped
*   Relationship Analysis: Links parent events via `parent_id` as REVERSAL, RESOLUTION, or UPDATE; auto-marks ancestors as `RESOLVED`
*   Trend & Momentum: Concept velocity tracking (Intensity × Growth), PCA visualization, semantic merging of similar concepts
*   Scenario Analysis: Promoted events require at least two distinct outcomes with trading plans per outcome
*   Horizon Watch: Only high-importance events with future catalysts appear on dashboard

For more details, see [[concepts/consensus]].

## Phase 5: The Skeptical Verifier
*   **Icon**: 🔍
*   **Badge**: 4-Layer Audit
*   **Tags**: [4-Layer Enforcement, Hard Tool Enforcement, Ownership Validation, Strategic Audit]

A dedicated "Skeptical Agent" intercepts every Buy/Sell signal using the same intelligence profile as the original generator. It performs a 4-Layer Enforcement audit and retrieves targeted per-trade RAG context (up to 2k tokens, ranked by importance × similarity) from pgvector to validate against past decisions and lessons learned.
*   Layer 1: Pre-Prompt Strengthening (enhanced system prompts with few-shot examples)
*   Layer 2: Prompt Context Enhancement (portfolio source of truth, held tickers list)
*   Layer 3: History scanning for actual tool calls via native function calling
*   Layer 4: Structured output enforcement with `price_source` field declaration
*   Hard Tool Enforcement: `get_stock_quote`, `calculate_buy_quantity`, `calculate_sell_quantity` must be actual function calls — text claims are hallucinations
*   Ownership Pre-Validation: SELL signals for unheld tickers are rejected pre-analysis
*   50% Confidence Penalty: Decisions without verified tool calls receive automatic reduction
*   Strategic Reasoning Audit: Validates logical consistency of "sell X to fund Y" patterns
*   Calendar & Seasonal Strategies: Turn of Month, Payday Anomaly adherence checks

For more details on verification rules, see [[concepts/tool-enforcement]] and [[concepts/rag-strategy]].

## Phase 6: Execution & Settlement
*   **Icon**: ⚖️
*   **Badge**: Reg T Compliance
*   **Tags**: [Reg T Margin, Atomic Settlement, Two-Phase Attribution, Broker Mirroring]

Approved trades undergo strict guardrails. The engine executes trades with Atomic Settlement ("Commit at End" pattern) and links decisions to trades via Two-Phase Attribution Locking.
*   FMP-Verified Market Hours: Holiday-aware with 5-minute TTL caching
*   5.0% Price Banding: Rejects trades where AI price deviates >5% from market
*   Reg T Margin Validation: Buying power check with $1,000 absolute minimum for BUYs
*   10% Minimum Position Rule: Auto-upsize for BUYs; 100% sell for SELLS below floor
*   Atomic Settlement: Cash/positions update only if ledger entry succeeds — prevents "Phantom Deductions"
*   Two-Phase Attribution Locking: Decision (status=VALIDATED) → Trade → Decision (status=EXECUTED, trade_id)
*   Real-time P&L: SQL View calculates `(market_price - avg_cost) * quantity` on-the-fly
*   Immediate Consistency: Reg T metrics persisted immediately after every trade
*   Alpaca Broker Mirroring: Decoupled Alpaca order status sync (SUBMITTED → FILLED via daily cron)

For more details, see [[concepts/execution]].

## Phase 7: Learning & Feedback
*   **Icon**: 🧠
*   **Badge**: Adaptive Feedback Loop
*   **Tags**: [Manager Agent, Contrarian Agent, pgvector RAG, Cause & Effect]

The cycle completes. Specialized agents perform post-analysis while the system maintains long-term memory via pgvector RAG with Scenario Analysis for context awareness.
*   Manager Agent: Post-analysis at 5, 14, 30-day intervals; generates "Lessons Learned" stored as `LESSON_LEARNED` memories
*   Contrarian Agent: Identifies crowded trades and missed risks using `List[ContrarianAgentResponse]` for multi-block robustness
*   Government Tracking: Monthly audit of incentives/policies with strict compliance enforcement
*   Cause & Effect Analysis: Bi-weekly (Tuesdays & Fridays) with semantic deduplication (pgvector, 24h lookback, 0.90 similarity)
*   Dynamic Ticker Discovery: FMP API for sector proxies, ETFs, derivative play tickers
*   Long-term Memory: pgvector store with Scenario Analysis (multi-outcome + trading plans)
*   Semantic Deduplication: 24-hour lookback, >0.90 similarity threshold prevents duplicates

For more details on feedback, see [[concepts/memory-feedback]].

## Related

- [[entities/engine]]
- [[concepts/ingestion]]
- [[concepts/reasoning]]
- [[concepts/consensus]]
- [[concepts/execution]]
- [[concepts/memory-feedback]]
