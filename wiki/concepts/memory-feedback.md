---
tags: [memory, feedback, rag, learning]
category: concept
---

# Memory & Feedback Loops

Three feedback mechanisms that make the system improve over time.

## Manager Agent (Post-Mortem)

At configured intervals after trade execution (short, medium, long horizon):
1. Fetch current price for each traded ticker
2. Send original reasoning + actual outcome to LLM
3. Generate `LESSON_LEARNED` memories in pgvector
4. Future RAG retrievals include these lessons, preventing repeated mistakes

## Contrarian Agent

Runs after primary agents. Identifies crowded trades and missed risks. Executes
counter-trades in a dedicated portfolio. Uses fresh market prices
(`force_refresh=True`), not cached data.

## Cause & Effect Analysis

Periodic retrospective audit that:
1. Deduplicates against prior analyses
2. Identifies most-affected companies per event (Gemini)
3. Compares scenario analysis against actual price data
4. Creates a searchable playbook of what narratives actually moved markets

## Market Feeling

After each pipeline run, an LLM generates "How I'm feeling and why" sentiment
based on the day's trades, lessons, and market events. Displayed on Today
dashboard with confidence bar and direction badge.

## Memory Architecture

Decoupled vector storage: `memories` table for market context (MARKET_EVENT,
GOVERNMENT_INCENTIVE, LESSON_LEARNED, UNCROWDED_TRADE), `decisions` table for
past trade reasoning. Retrieval scoped: cross-agent for memories, per-agent for
decisions (prevents cross-contamination in verification).

## Related

- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/rag-strategy]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/autoresearch]]
