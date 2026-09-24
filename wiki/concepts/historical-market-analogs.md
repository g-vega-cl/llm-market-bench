---
tags: [macro, tools, analogs, precedent, playbook, reasoning]
category: concept
---

# Historical Market Analogs & Precedent Benchmarking

The **Historical Market Analog Research Engine** (`research_historical_market_analog`) is an analytical tool and reasoning capability designed to answer: *"How did markets react the last time a similar situation occurred, what rallied, what didn't, and how can we profit from it now?"*

---

## 1. Core Architecture: The Hybrid Verification Pipeline

Relying exclusively on generative LLM memory for historical market reactions frequently introduces hallucinated return numbers (e.g. claiming an asset dropped 15% when it actually dropped 4%). Conversely, pure mechanical quantitative screening fails to capture nuanced geopolitical and macroeconomic catalysts (such as currency interventions, shipping route disruptions, or bank runs).

The engine solves this through a decoupled **Hybrid Verification Pipeline**:

```text
 [Market Setup Query] ──▶ [LLM Episode Extraction (ChatGPT Luna + Thinking)]
                                         │
                                         ▼
                            [Empirical Price Tape Fetch]
                         (SPY, QQQ, TLT, IEF, GLD, USO, UUP, BTC)
                                         │
                                         ▼
                            [4-Pillar Playbook Synthesis]
                         (ChatGPT Luna + Medium Thinking)
                                         │
                                         ├────────────────────────┐
                                         ▼                        ▼
                                [Lean Markdown Report]  [Vector Memory Store]
                               (Zero ANSI Escapes)     (Supabase HISTORICAL_ANALOG)
```

1. **Precedent Identification**: Uses `gpt-5.6-luna` (configured via `OPENAI_MODEL` in `packages/config/models.json`) with `reasoning_effort="medium"` to identify the single most relevant historical episode from 1970–present and extract its exact ISO 8601 date window (`start_date`, `end_date`).
2. **Empirical Price Tape Extraction**: The engine's `MarketDataManager` queries verified end-of-day price histories for core cross-asset benchmarks (`SPY`, `QQQ`, `TLT`, `IEF`, `GLD`, `USO`, `UUP`, `BTCUSD`) plus any user-specified `focus_assets`, computing precise percentage returns and classifying reaction statuses (`GAINED`, `DROPPED`, `FLAT`).
3. **4-Pillar Playbook Synthesis**: The model deliberates over the empirical reaction tape against today's macro environment, extracting key structural divergences (e.g. Fed cutting vs hiking, valuation levels) and synthesizing asymmetric long/short expressions and explicit falsification triggers.
4. **Vector Memory Persistence**: Each completed research report is vector-embedded and persisted into Supabase `memories` under `memory_type="HISTORICAL_ANALOG"`, enabling immediate retrieval by future trading agents via `search_past_memories`.

---

## 2. Tool Interface Contract

Declared in `packages/config/tools.json` and registered in `apps/engine/core/llm/tools.py`:

```json
{
  "name": "research_historical_market_analog",
  "description": "Researches historical market precedent episodes, cross-asset reaction tapes (stocks, bonds, gold, crypto, dollar), and actionable profit playbooks"
}
```

### Signature
```python
async def research_historical_market_analog(
    situation: str,
    focus_assets: list[str] | None = None,
    horizon: str = "1m",
) -> str:
    ...
```

---

## 3. Related

- [[entities/tool-registry]] — Centralized tool registry in `packages/config/tools.json`
- [[concepts/tool-first-agency]] — Principle 8 Tool-First, Agency-Driven Architecture
- [[concepts/thinking-agents]] — Thinking mode execution contracts and reasoning effort allocation
- [[concepts/rag-strategy]] — Vector retrieval and memory persistence
