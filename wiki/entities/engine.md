---
tags: [engine, python, pipeline, analysis, execution]
category: entity
---

# Engine

The Python data engine that powers the LLM Market Bench pipeline: ingestion, analysis, consensus, execution, and feedback.

## Architecture

The engine is a modular monorepo under `apps/engine/` with these key modules:

- **analysis/**: Consensus, event synthesis, discovery
- **core/llm/**: LLM client wrappers, prompt factory, event synthesis with structured `HistoricalParallelDetail`
- **core/models/**: Pydantic models for events, trades, portfolios
- **execution/**: Trade validation, Reg T checks, settlement
- **ingestion/**: Newsletter scraping, economic calendar, government data

## Key Components

### Consensus & Synthesis

The `analysis/consensus.py` module groups model observations, resolves impact ties, and calls `synthesize_event` to produce a unified event summary. It now collects candidate historical parallels from individual model observations and passes them to the synthesizer. The synthesizer returns a structured `HistoricalParallelDetail` object (defined in `core/llm/events.py`) with fields: title, timeframe, precedent, market_reaction, takeaway, affected_assets.

### HistoricalParallelDetail Model

Introduced in `core/llm/events.py`, this Pydantic model enforces structured output from the LLM synthesizer:

```python
class HistoricalParallelDetail(BaseModel):
    title: str
    timeframe: str
    precedent: str
    market_reaction: str
    takeaway: str
    affected_assets: list[str]
```

The synthesizer prompt (`core/llm/prompts.py`) instructs the LLM to produce this structured object when a historical parallel is identified. The response is normalized to a dict and stored in memory metadata.

### Prompt Factory

The `PromptFactory.build_synthesis_messages` method now accepts a `candidate_parallels` parameter, which is formatted into the user prompt as a bullet list of candidate historical parallels identified by models.

### Forward Calendar & Scenario Analysis

The `analysis/calendar_scenarios.py` module and `core/time_utils.py` provide exact temporal anchoring (EDT/UTC, market session phase, tomorrow/next-week dates) and the `get_calendar_scenario_analysis` pull tool. It synthesizes probability-weighted scenario trees (Bull/Base/Bear), conditional trading plans, target assets, and historical precedent memory lessons across portfolio analysis, daily predictor, and sector predictor flows. See [[concepts/calendar-scenario-analysis]].

### Frontier Tech Supercycle Portfolio

The `execution/frontier_tech.py` and `tasks/frontier_tech_task.py` modules run monthly discovery, 5-point rubric qualification, and small-cap guardrail screening for the `sys-frontier-tech` portfolio. See [[entities/frontier-tech-portfolio]].

### Triple Barrier Method and Regime Probabilities

The `analytics/barrier_probabilities.py` module evaluates empirical Triple Barrier Method (López de Prado) touch frequencies conditional on prevailing volatility and trend regimes via the `get_barrier_touch_probabilities` pull tool. It computes historical win rates, stop-out rates, vertical expiration returns, and expected value net of 10 bps slippage. See [[concepts/triple-barrier-probabilities]].

### Real-Time Stock News

The `analysis/ticker_news.py` module fetches structured financial headlines, publisher sources, published timestamps, and article summaries for individual tickers via the `get_ticker_news` pull tool. Backed by FMP's stable stock news endpoint, it gives trading and predictor agents verified, noise-free company news on demand without brittle web scraping.

### Congress Trading Disclosures

The `apps/engine/tools/congress_tools.py` module and `apps/engine/scripts/update_congress_trades.py` pipeline ingest, normalize, and cache STOCK Act personal financial disclosures from the US Senate and House of Representatives. Agents query these transactions via the `get_congress_trades` pull tool to inspect politician buying and selling, trade amounts, and filing dates.

## Related

- [[entities/frontier-tech-portfolio]]
- [[concepts/consensus]]
- [[concepts/memory-feedback]]
- [[concepts/calendar-scenario-analysis]]
- [[concepts/triple-barrier-probabilities]]
- [[entities/pipeline]]
- [[concepts/rag-strategy]]
