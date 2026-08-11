---
tags: [pipeline, entity, engine, analysis]
category: entity
---

# Pipeline

Full daily pipeline from ingestion to feedback. The pipeline runs on a cron schedule during US market hours.

## Phase 1: Ingestion & Normalization
*   **Icon**: 📰
*   **Badge**: 3x Daily Trigger: US Market Hours
*   **Tags**: [FMP Cache, Gmail API, Ingestion]

Cloudflare Worker edge dispatcher fires the pipeline during US market hours (3 times daily: 9:35 AM ET, 11:35 AM ET, and 3:30 PM ET) to parse newsletter inputs.

*   Newsletter Ingestion: Scrapes newsletters, feeds, and economic data from Gmail and external APIs.
*   De-Advertisement: Gemini Flash filters out ads, noise, and sponsor blocks from incoming text.

## Phase 2: Pre-Analysis Setup
*   **Icon**: ⚙️
*   **Badge**: Market Hours Check
*   **Tags**: [Market Hours, Macro Tracker, Dust Cleanup]

Before LLM analysis, the engine validates market status and cleans up stale states.
*   FMP-Verified Market Hours: Checks NYSE/NASDAQ status with 5-minute TTL caching to verify they are open.
*   Dust Cleanup: Cleans dust positions (<10% equity) before analysis to prevent model confusion.
*   Global Macro Snapshot: Quotes 16 key assets for Risk-On/Risk-Off macro baseline.
*   Light Context Injection: Injects top-5 trending concepts, anomalies, and historical memories.

## Phase 3: Macro Event Extraction & Consensus
*   **Icon**: 🧩
*   **Badge**: Pass 1: Semantic Grouping
*   **Tags**: [MacroEventsResponse, pgvector, Cosine Clustering]

The first pass of LLM analysis extracts and clusters macroeconomic events.
*   Asynchronous Chunk Batching: Splits newsletter content into parallel batches of 20 chunks.
*   Semantic Grouping: Embeds and clusters events via pgvector cosine similarity.
*   Weighted Consensus: Promotes events based on cumulative model weight and voting.
*   Temporal Deduplication: Discards duplicate events within a recency window.
*   Relationship Analysis: Maps parent/child relationships in the event graph.

## Phase 4: Trading Decisions
*   **Icon**: 🤖
*   **Badge**: Pass 2: Trading Strategy
*   **Tags**: [TradingDecisionsResponse, PromptFactory, DiscoveryAgent]

The second pass receives newsletter summaries, portfolio context, and the synthesized macro events.
*   Parallel LLM Analysis: OpenAI, Claude, Gemini, DeepSeek, and MiniMax analyze context in parallel to propose trades.
*   PromptFactory: Builds semantically identical instructions for model comparability.
*   DiscoveryAgent: Loops up to 3 steps to identify investable assets based on macro consensus.
*   DeepSeek Thinking Mode: Preserves Chain-of-Thought reasoning for deep analysis.

## Phase 5: The Skeptical Verifier
*   **Icon**: 🔍
*   **Badge**: 4-Layer Audit
*   **Tags**: [Skeptical Agent, RAG Context, Tool Enforcement]

A dedicated Skeptical Agent intercepts and audits every BUY/SELL signal (except MiniMax).
*   4-Layer Enforcement: Strengthens prompts, injects portfolio truth, and verifies tool usage.
*   Hard Tool Enforcement: Verifies trading calculations are actual tool calls, not text claims.
*   Ownership Pre-Validation: Rejects SELL signals for unheld positions.
*   50% Confidence Penalty: Deducts confidence points for signals missing tool calls.

## Phase 6: Execution & Settlement
*   **Icon**: ⚖️
*   **Badge**: Reg T Compliance
*   **Tags**: [Reg T Margin, Atomic Settlement, Two-Phase Attribution]

Approved trades undergo strict margin, sizing, and pricing checks.
*   5.0% Price Banding: Rejects trades if the AI's execution price deviates >5% from the market price.
*   Reg T Margin Validation: Performs real-time margin and buying power checks.
*   10% Minimum Position Rule: Auto-upsizes buy orders and closes out small holdings.
*   Atomic Settlement: Commits changes to the ledger atomically to prevent ledger bugs.
*   Two-Phase Attribution Locking: Links decisions to executed trade IDs.
*   Alpaca Broker Mirroring: Submits limit orders to Alpaca paper-trading accounts.

## Phase 7: Learning & Feedback
*   **Icon**: 🧠
*   **Badge**: Adaptive Feedback Loop
*   **Tags**: [Manager Agent, Contrarian Agent, Cause & Effect]

The pipeline closes the loop by auditing historical results and updating system memories.
*   Manager Agent: Runs post-mortems at 5, 14, and 30 days to store lessons learned.
*   Contrarian Agent: Checks crowded trades and issues counter-positioning.
*   Cause & Effect Analysis: Audits retrospective price impact of AI trading signals.
*   Market Feeling: Runs sentiment analysis after execution to capture the daily market vibe.

## Related

- [[concepts/consensus]]
- [[concepts/ingestion]]
- [[entities/engine]]
