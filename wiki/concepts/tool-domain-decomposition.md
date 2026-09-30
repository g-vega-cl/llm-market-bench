---
tags: [tools, architecture, refactor, dispatch, testing]
category: concept
---

# Tool Domain Decomposition

The engine's LLM tool implementations were originally a single 4,500-line monolith in `apps/engine/core/llm/tools.py`. They are now decomposed into focused domain modules under `apps/engine/tools/`, with `core/llm/tools.py` retained as a thin barrel that re-exports every handler for backward compatibility. This keeps each tool family small enough to reason about while preserving the existing import surface used by prompts, tests, and the dispatch layer.

## Domain Modules

Each module owns one coherent family of tools:

- `tools/market_data.py`: quotes, price history, intraday movement profiles, ticker news, and `compute_volume_context`
- `tools/prediction_markets.py`: Polymarket and Kalshi search and live odds
- `tools/portfolio.py`: position PnL, buy/sell sizing, portfolio ledger, system portfolios
- `tools/technicals_options.py`: volatility metrics, screeners, correlation, options sentiment/chains, vol surfaces, barrier touch probabilities
- `tools/macro.py`: global macro context, VIX/volatility regime details, FRED series, yield curve, economic releases
- `tools/earnings.py`: sector alternatives, related tickers, earnings history, PEAD candidates, revisions, bellwethers
- `tools/valuation.py`: key metrics, market health barometer, sector fundamentals, 5-year DCF audit
- `tools/news_memories.py`: newsletters, pgvector memory search, thematic flow persistence, market feeling, web search
- `tools/analyst_personas.py`: Warren Buffett/Munger audit, historical market analogs, future forces, thematic beneficiaries
- `tools/compliance.py`: verifier rejections, SOP inspection, thesis pillar tracking, catalyst radar, calendar scenarios, STOCK Act congress trades

`tools/__init__.py` exposes each module as a package attribute so `from tools import valuation` works.

## Barrel Re-Exports

`core/llm/tools.py` no longer contains execution handler bodies. It imports every handler from its domain module (using `as` aliases so linters treat them as intentional re-exports) and keeps the declarative tool schemas, provider adapters (`to_anthropic`, `to_gemini`), and the `CANONICAL_TOOLS_REGISTRY`. This means existing call sites and `unittest.mock.patch("core.llm.tools.execute_*_tool")` targets continue to resolve.

## O(1) Dispatch Table

`core/llm/handlers/base.py` replaces the long `if/elif` chain with two module-level structures:

- `TICKER_REQUIRED_TOOLS`: the set of tools that must receive a validated ticker argument
- `TOOL_DISPATCH_TABLE`: a dict mapping tool name to a callable `(ticker, args, model_name, kwargs) -> awaitable`

`_dispatch_tool` validates the ticker, looks up the handler, and returns `"Unknown tool"` when absent. Adding a tool is now a single table entry rather than a new branch.

## Compatibility Bridge for Mock Interception

Because handlers moved out of `core.llm.tools`, a naive `patch("core.llm.tools.get_supabase_client")` would no longer intercept calls made inside a domain module. `tools/_compat.py` solves this with proxy helpers (`get_supabase_client`, `get_async_supabase_client`, `get_embedding`, and a `MarketDataManager` proxy class) that resolve at call time to whichever of the barrel (`core.llm.tools`) or the upstream module (`core.db`, `memory.embeddings`, `execution.market_data`) is currently a `Mock`, falling back to the real implementation otherwise. Domain modules import these proxies instead of the concrete functions, so hermetic tests that patch the barrel keep working.

## Verification

`tests/test_tools_domain_decomposition.py` enforces the contract: it asserts each domain module exports its expected handlers, that the `core.llm.tools` barrel re-exports all handlers, and that patching `core.llm.tools.execute_stock_tool` still intercepts dispatch through `handlers.base.execute_tool`. `test_tools_consistency.py` continues to guard drift against `packages/config/tools.json`.

## Related

- [[entities/tool-registry]]: the canonical tool registry and drift-prevention tests
- [[concepts/vertical-slice-islands]]: the architectural rationale for splitting monoliths
- [[concepts/defensive-tool-dispatch]]: dispatch-layer error handling
- [[concepts/tool-enforcement]]: server-side confirmation that quantity tools were called
