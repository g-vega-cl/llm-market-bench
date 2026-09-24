---
tags: [entity, macro, analysis, tools, precedent]
category: entity
---

# Historical Market Analogs Engine

`apps/engine/analysis/historical_analogs.py` — the **Historical Market Analog Research Engine**. It answers the recurring macro question *"how did markets react the last time XYZ happened?"* by pairing LLM-driven precedent identification with empirically verified cross-asset price returns, then synthesizing an asymmetric trading playbook.

## Why It Exists

Relying on an LLM's generative memory for historical market reactions invites hallucinated return numbers. Pure mechanical fits of past episodes skip the nuanced geopolitical/macro catalyst context. The engine decouples the two: the LLM extracts the *episode and its dates*, but the *numbers* come from verified market data.

## Hybrid Verification Pipeline

1. **Precedent identification** — ChatGPT Luna (`OPENAI_MODEL`, thinking mode via `reasoning_effort="medium"`) selects the single most structurally relevant episode (1970–present) and returns an ISO date window plus trigger, macro backdrop, and a relevance score.
2. **Empirical price tape** — `MarketDataManager.get_history` pulls end-of-day prices for the default cross-asset benchmarks (`SPY`, `QQQ`, `TLT`, `IEF`, `GLD`, `USO`, `UUP`, `BTCUSD`) plus any `focus_assets`, computes percentage returns, and classifies each as `GAINED`, `DROPPED`, or `FLAT`.
3. **Playbook synthesis** — The model deliberates over the real tape against today's macro environment and produces the four-pillar output: Precedent, empirical Tape, key Divergences today, and the actionable Playbook (core takeaway, long/outperform expression, hedge/fade expression, falsification trigger, predicted outcome).
4. **Vector memory persistence** — The finished report is embedded and written to Supabase `memories` with `memory_type="HISTORICAL_ANALOG"`, `importance_score=8`, and structured metadata, making it retrievable by later agents through `search_past_memories`.

## Key Functions

| Function | Role |
| --- | --- |
| `identify_historical_precedent` | LLM extraction of the best analog episode and date range |
| `fetch_empirical_market_tape` | Verified cross-asset return calculation across the episode window |
| `synthesize_analog_playbook` | Four-pillar playbook synthesis from tape + today's divergences |
| `format_analog_markdown` | Dense, token-efficient Markdown report (no ANSI escapes) |
| `persist_analog_memory` | Vector-embed and store the report in the `memories` table |
| `research_historical_market_analog` | End-to-end orchestration entry point |

Structured outputs use Pydantic models (`HistoricalPrecedentCandidate`, `AssetReturnTape`, `PlaybookSynthesis`, `HistoricalAnalogReport`), with the instructor `Mode.JSON` client so reasoning mode is preserved.

## Surfaces

- **Tool**: `research_historical_market_analog(situation, focus_assets=None, horizon="1m")` — registered in `packages/config/tools.json`, `core/llm/tools.py` (`CANONICAL_TOOLS_REGISTRY` + `execute_research_historical_market_analog_tool`), and dispatched in `core/llm/handlers/base.py`.
- **Autoresearch**: listed in `autoresearch/program.md` and exposed as the `historical_analog_benchmarking` prompt block in `autoresearch/prompt_blocks.py`.
- **CLI**: `python main.py analog --situation "..." [--assets TLT,GLD] [--horizon 1m]`.
- **Verification**: `apps/engine/scripts/dry_run_historical_analogs.py` runs the full live path against real APIs.

## Related

- [[concepts/historical-market-analogs]] — the conceptual framing of precedent benchmarking
- [[entities/tool-registry]] — tool registration and consistency enforcement
- [[entities/market-context-viewer]] — market data surfaces
- [[concepts/rag-strategy]] — vector memory and retrieval
- [[concepts/thinking-agents]] — reasoning-effort execution contracts
