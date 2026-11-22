---
tags: [recipes, recipe-builder, config, templates, strategy]
category: concept
---

# Starter Recipes

The canonical catalog of pre-built recipe templates lives in `packages/config/starter-recipes.json`. Each entry is a complete, runnable recipe definition (version, name, description, cadence, and one or more stages) that seeds the [[entities/recipe-studio]] / [[entities/recipe-playground]] builder so users can start from a coherent strategy instead of a blank canvas. Every recipe is compiled by the [[concepts/recipe-builder-compiler]] and executed by the [[concepts/recipe-portfolio-engine]].

## Recipe Anatomy

Every starter recipe shares the same JSON shape:

- `version` — schema/version tag (e.g. `2.0-push`)
- `name` — human-readable strategy name
- `description` — one-line summary of the edge
- `cadence` — how often the recipe runs (e.g. `3h`)
- `stages[]` — ordered stages, each with:
  - `selected_tools[]` — the tool allowlist the agent may call
  - `blocks[]` — context blocks of type `prompt`, `news`, `memories`, `technicals`, or `output_format`

### Block Types

- **`prompt`** — free-text instructions injected into the agent context.
- **`news`** — filters over the news feed (`contains` keywords, `recency_hours`).
- **`memories`** — filters over past memories (`contains`, `recency_hours`, `category`, `min_importance`).
- **`technicals`** — declarative screening rules (`metric`, `operator`, `target`).
- **`output_format`** — enforces the structured output contract.

## The `2.0-push` Recipe Family

The `2.0-push` recipes are deterministic, push-based templates: each one pre-compiles a fixed set of context blocks (news/memories/technicals) and a tool allowlist, so the agent operates on a reproducible, point-in-time snapshot rather than pulling everything on demand. They span the full spectrum from zero-injected-context screens to news-driven contrarian books.

### Zero / Minimal Context Recipes

- **Deep Value Snapback** — no news, no memories. Hunts deeply discounted names (RSI < 30, bottom 30% of 52-week range, P/E < 20) and reads the market-feeling barometer before buying the snapback. Tools: `get_key_metrics`, `get_technical_indicators`, `get_price_history`, `get_market_feeling`.
- **Cheap Tape Rotator** — no news, no memories. Rotates through cheap, cash-generative names (RSI < 45, price < VWAP, FCF > 0, P/E < 25). Tools: `get_key_metrics`, `get_technical_indicators`, `get_price_history`, `get_earnings_history`.

### Value / Quality Recipes

- **Value Pullback Rotator** — no live news feed; rotates into cash-generative value names on oversold pullbacks below VWAP (RSI < 40, price < VWAP, FCF > 0), using post-mortem memories of past reversals. Tools include `search_past_memories` and `get_stock_quote`.
- **Patient Compound Accumulator** — no news block; a slow, low-turnover accumulator buying durable compounders (P/E < 22, ROE > 12, MACD > 0) with `get_earnings_history` to verify multi-quarter compounding.
- **Quality Momentum Rotator** — no news block; rotates into high-ROE names near 52-week highs on above-average volume (ROE > 10, price_52w_pct > 60, RVOL > 1.1).

### Momentum / Re-Rating Recipes

- **Fundamental Momentum Scalper** — no news or memory blocks; a fast in-and-out book pairing a sub-35 multiple and ROE > 8 with positive MACD, checking `get_ticker_news` before each entry.
- **Multiple Re-Rating Rotator** — no news block; rides multiple expansion by buying names under 40x earnings being re-rated on volume near 52-week highs (MACD > 0, RVOL > 1.3, price_52w_pct > 60).

### News-Driven Recipes

- **Catalyst Hold Sleeve** — 72 hours of guidance/sector/policy news plus market-event memories; buys strong-ROE leaders near highs (MACD > 0, price_52w_pct > 75, ROE > 12) and holds the catalyst rather than flipping it.
- **Headline Panic Fader** — 24 hours of panic/downgrade/selloff headlines plus short-horizon post-mortems; buys oversold names below VWAP (RSI < 30, price_52w_pct < 35, price < VWAP) and fades the fear quickly.
- **Fast News Contrarian** — 24 hours of headline/cut/selloff news with 96 hours of post-mortems; a quick contrarian book buying overreactions in cash-generative names (RSI < 40, price < VWAP, FCF > 0).
- **Print Window Scalper** — 24 hours of earnings/beat/miss headlines with 72 hours of calendar memories; scalps the post-print window on heavy volume near 52-week highs (RVOL > 2, MACD > 0, price_52w_pct > 80).

## Related

- [[concepts/recipe-builder-compiler]] — compiles recipe JSON into runnable agent configs
- [[concepts/recipe-builder-usage]] — how users build and run recipes
- [[concepts/recipe-portfolio-engine]] — executes recipes as portfolios
- [[concepts/recipe-turbo-mode]] — accelerated recipe execution
- [[entities/recipe-studio]] — recipe authoring UI
- [[entities/recipe-playground]] — recipe experimentation surface
- [[concepts/modular-prompt-blocks]] — prompt block catalog
