---
tags: [memory, rag, seeding, academic-papers]
category: entity
---

# Academic Paper Seeding

A curated seeding script (`seed_academic_papers.py`) that ingests curated empirical asset pricing and market anomaly papers into the pgvector memory store as high-importance `ACADEMIC_PAPER` memories. This foundational knowledge grounds LLM trading agents in established financial science, ensuring decisions are informed by decades of peer-reviewed research on factor premiums, behavioral anomalies, and market efficiency.

## Purpose

The script populates the vector store with structured summaries of seminal papers, each formatted as a rich text chunk containing the core thesis, underlying mechanism, practical application, and a concrete agent trading example. These memories are assigned an importance score of 10 (maximum) and are deduplicated via similarity checks, making them safe to re-run.

## Papers Included

Source of truth is `PAPERS` in `seed_academic_papers.py`. The dataset covers six pillars:

- **Factor Investing & Risk Premiums**: The Cross-Section of Expected Stock Returns (Fama & French, 1992), Common Risk Factors in the Returns on Stocks and Bonds (Fama & French, 1993), Value and Momentum Everywhere (Asness, Moskowitz & Pedersen, 2013), A Five-Factor Asset Pricing Model (Fama & French, 2015), Size Matters, If You Control Your Junk (Asness, Frazzini, Israel, Moskowitz & Pedersen, 2018)
- **Behavioral Finance & Market Anomalies**: Contrarian Investment, Extrapolation, and Risk (Lakonishok, Shleifer & Vishny, 1994), The Limits of Arbitrage (Shleifer & Vishny, 1995), A Model of Investor Sentiment (Barberis, Shleifer & Vishny, 1997), Does the Stock Market Overreact? (De Bondt & Thaler, 1985)
- **Anomalies and Empirical Evidence**: Returns to Buying Winners and Selling Losers (Jegadeesh & Titman, 1993), On Persistence in Mutual Fund Performance (Carhart, 1997), Do Stock Prices Fully Reflect Information in Accruals and Cash Flows? (Sloan, 1996)
- **Temporal & Calendar Anomalies**: The Overnight Return Anomaly (The Night Effect) (Lou, Polk & Skouras, 2019), The Turn-of-the-Month Effect (McConnell & Xu, 2008), The Pre-Holiday Liquidity Vacuum (Ariel, 1990), The January Effect (Rozeff & Kinney, 1976), The Weekend Effect / Monday Effect (French, 1980)
- **Information & Event-Driven Anomalies**: Post-Earnings-Announcement Drift (PEAD) (Bernard & Thomas, 1989), Pre-FOMC Announcement Drift (Lucca & Moench, 2015)
- **Structural & Plumbing Anomalies**: The Index Inclusion Effect (The Passive Squeeze) (Shleifer, 1986), Options Expiration Pinning (Max Pain) (Ni, Pearson & Poteshman, 2005), The Index Premium and Its Hidden Cost for Index Funds (Petajisto, 2011), Index Changes and Losses to Index Fund Investors (Chen, Noronha & Singal, 2006)

Each paper is stored with metadata (`source_type`, `citation`, `pillar`) for attribution and filtering.

## Integration with RAG

These memories are injected into the Tier 2 RAG (Verifier Path) via `retrieve_for_decision()`. Because they are `ACADEMIC_PAPER` memories with maximum importance, they reliably appear in the top results when the verifier queries for relevant academic principles. This complements the per-agent past decisions and shared market events already in the memory store.

## Seeding Process

- The script calls `add_memory()` for each paper with `check_similarity=True` and `similarity_threshold=0.95` to avoid duplicates.
- A companion test (`test_seed_academic_papers.py`) verifies that all papers are seeded with the correct parameters and formatting.

## Related

- [[concepts/rag-strategy]] — Tiered context injection and per-agent RAG
- [[entities/engine]] — Python data engine (memory store is part of the engine)
- [[entities/database]] — Supabase PostgreSQL with pgvector
