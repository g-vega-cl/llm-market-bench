---
tags: [analysis, llm, tools, multi-provider]
category: concept
---

# Reasoning & Analysis

Parallel LLM analysis with tool-calling loops across four providers.

## Batch Strategy

News chunks are split into batches to avoid output-token truncation and "Lost
in the Middle." Each batch gets full portfolio summary + market data + context.
All batches run in parallel via `asyncio.gather`.

## Provider Handlers

Each provider has a dedicated handler at `core/llm/handlers/`:

- **OpenAI** — Standard tool loop
- **Anthropic** — XML-like tool blocks, server-side web search, max_tokens bump
- **Gemini** — `List[Model]` for multi-function-call, Google Search grounding
- **DeepSeek** — Thinking mode with `reasoning_content` preservation

## Available Tools

| Tool | Purpose |
|------|---------|
| `get_stock_quote` | Verify ticker existence and price |
| `get_price_history` | Check if news is "priced in" |
| `calculate_buy_quantity` | Exact shares from % of buying power |
| `calculate_sell_quantity` | Exact shares from % of position |
| `web_search` | Real-time news verification |
| `run_stock_screener` | Find investable assets |
| `find_uncorrelated_assets` | Diversification pairs |

## Discovery Agent

A specialized agent that identifies relevant assets for each market theme before
main analysis. Uses `run_stock_screener` + optional web search, capped at a
configurable max candidates.

## Structured Extraction

Instructor + Pydantic enforces strict JSON schema. 3-attempt retry loop with
corrective prompting. JSON repair handles double-encoded strings, extra quotes,
embedded JSON.

## Related

- [[entities/pipeline]]
- [[entities/engine]]
- [[concepts/consensus]]
- [[concepts/tool-enforcement]]
- [[concepts/rag-strategy]]
