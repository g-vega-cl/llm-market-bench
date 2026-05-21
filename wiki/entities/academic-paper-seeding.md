---
tags: [memory, rag, seeding, academic-papers]
category: entity
---

# Academic Paper Seeding

A curated seeding script (`seed_academic_papers.py`) that ingests the top 10 empirical asset pricing papers into the pgvector memory store as high-importance `LESSON_LEARNED` memories. This foundational knowledge grounds LLM trading agents in established financial science, ensuring decisions are informed by decades of peer-reviewed research on factor premiums, behavioral anomalies, and market efficiency.

## Purpose

The script populates the vector store with structured summaries of seminal papers, each formatted as a rich text chunk containing the core thesis, underlying mechanism, practical application, and a concrete agent trading example. These memories are assigned an importance score of 10 (maximum) and are deduplicated via similarity checks, making them safe to re-run.

## Papers Included

The dataset covers three pillars:

- **Factor Investing & Risk Premiums**: Fama-French (1992, 1993), Asness, Moskowitz & Pedersen (2013)
- **Behavioral Finance & Market Anomalies**: Lakonishok, Shleifer & Vishny (1994), Shleifer & Vishny (1995), Barberis, Shleifer & Vishny (1997), De Bondt & Thaler (1985)
- **Anomalies and Empirical Evidence**: Jegadeesh & Titman (1993), Carhart (1997), Sloan (1996)

Each paper is stored with metadata (`source_type`, `citation`, `pillar`) for attribution and filtering.

## Integration with RAG

These memories are injected into the Tier 2 RAG (Verifier Path) via `retrieve_for_decision()`. Because they are `LESSON_LEARNED` with maximum importance, they reliably appear in the top results when the verifier queries for relevant academic principles. This complements the per-agent past decisions and shared market events already in the memory store.

## Seeding Process

- The script calls `add_memory()` for each paper with `check_similarity=True` and `similarity_threshold=0.95` to avoid duplicates.
- A companion test (`test_seed_academic_papers.py`) verifies that all papers are seeded with the correct parameters and formatting.

## Related

- [[concepts/rag-strategy]] — Tiered context injection and per-agent RAG
- [[entities/engine]] — Python data engine (memory store is part of the engine)
- [[entities/database]] — Supabase PostgreSQL with pgvector
