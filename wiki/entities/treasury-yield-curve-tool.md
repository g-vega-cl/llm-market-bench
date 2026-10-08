---
tags: [entity, tools, macro, treasury, fixed-income]
category: entity
---

# Treasury Yield Curve Tool

`get_treasury_yield_curve` (`execute_get_treasury_yield_curve_tool` in `apps/engine/tools/macro.py`) is a no-argument, read-only canonical tool that fetches live US Treasury benchmark yields across the curve from FRED and renders a compact markdown snapshot.

## Output

For each tenor the tool reports the latest yield and the 1-day change in basis points, then derives key curve spreads:

| Tenor | FRED Series |
| :--- | :--- |
| 3-Month | `DGS3MO` |
| 2-Year | `DGS2` |
| 5-Year | `DGS5` |
| 10-Year | `DGS10` |
| 30-Year | `DGS30` |

- **10Y - 2Y spread** (with an Inverted / Normal regime label; falls back to `T10Y2Y` when only the spread series is available)
- **10Y - 3M spread**
- **30Y - 10Y (long-end slope)**

Observations are pulled concurrently via `asyncio.gather` over `fetch_fred_series_observations`.

## Wiring

- Registered in `CANONICAL_TOOLS_REGISTRY` and dispatched through `TOOL_DISPATCH_TABLE` in `core/llm/handlers/base.py`.
- Declared in `packages/config/tools.json` alongside the other canonical tool descriptors.
- The FRED alias map in `core/fred.py` was expanded with `treasury_3m`, `treasury_5y`, and `treasury_30y` in addition to the existing `treasury_2y` and `treasury_10y`.

This tool is the primary data source for the [[entities/bond-predictor]] and is available to autonomous analysis agents that reason about duration and rate risk. See [[entities/tool-registry]] for the full tool lineup.

## Related

- [[entities/bond-predictor]]
- [[entities/tool-registry]]
- [[concepts/macroeconomic-data-fred]]
