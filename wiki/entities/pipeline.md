---
tags: [pipeline, entity, engine, analysis]
category: entity
---

# Pipeline

Full daily pipeline from ingestion to feedback. The pipeline runs on a cron schedule during US market hours.

## Phases

1. **Ingestion** — fetch newsletters, economic calendar, government data.
2. **Pre-Analysis** — market hours check, dust cleanup, macro tracking (23 tickers across 6 categories).
3. **Decoupled Analysis** (two sequential passes):
   - **Pass 1: Macro Events Extraction** — all LLM models analyze newsletter chunks to extract macroeconomic events using `MacroEventsResponse`.
   - **Consensus** — semantic grouping and weighted voting on the extracted macro events to produce promoted consensus events.
   - **Pass 2: Trading Decisions** — LLM models receive newsletter summaries, portfolio context, and the synthesized consensus events context (`TradingDecisionsResponse`) to generate trading decisions.
4. **Execution** — validation, Reg T checks, trade settlement, attribution.
5. **Feedback** — post-mortem, contrarian analysis, cause & effect, and weekly auto-research prompt improvement.

## Related

- [[concepts/consensus]]
- [[concepts/ingestion]]
- [[entities/engine]]
