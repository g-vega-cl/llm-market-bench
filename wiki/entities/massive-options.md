---
tags: [options, market-data, massive, polygon, tools, derivatives, greeks]
category: entity
---

# Massive Options Integration

The **Massive Options Integration** connects the AI Wall Street Engine to **Massive.com** (formerly **Polygon.io**) options market data, equipping LLM trading agents and the [[entities/autoresearch]] pipeline with equity options sentiment, implied volatility (IV), Greeks, and near-the-money options chains.

## Overview & Dual-Tier Architecture

Massive.com provides consolidated OPRA equity options data. The engine implementation in `apps/engine/execution/providers/massive.py` automatically adapts between paid snapshot subscriptions and free tier access:

```mermaid
flowchart TD
    Agent[LLM Agent / Autoresearcher] --> Tool[get_options_sentiment / get_option_chain]
    Tool --> Client[MassiveOptionsClient]
    Client --> Cache[(options_data_cache)]

    Cache -- Cache Hit --> Return[Return Formatted Markdown]
    Cache -- Cache Miss --> Limiter[AsyncTokenBucketLimiter 5 req/min]

    Limiter --> SnapshotAPI[Massive /v3/snapshot/options]
    SnapshotAPI -- 200 OK (Paid Plan) --> ParseSnapshot[Parse Greeks, IV, OI, Quotes]
    SnapshotAPI -- 403 (Free Plan) --> FreeFallback[Free Tier Fallback Pipeline]

    FreeFallback --> RefAPI[/v3/reference/options/contracts]
    FreeFallback --> PrevBarAPI[/v2/aggs/ticker/O:.../prev]
    FreeFallback --> BlackScholes[Local Pure-Python Black-Scholes Engine]
    BlackScholes --> ComputeGreeks[Compute ATM IV, Delta, Gamma, Theta, Vega]

    ParseSnapshot --> Deriver[Calculate Put/Call Ratios, Max Pain, Skew]
    ComputeGreeks --> Deriver
    Deriver --> SaveCache[Upsert options_data_cache & Memory Cache]
    SaveCache --> Return
```

---

## Tools Exposed to Agents

Registered in `packages/config/tools.json` and canonicalized in `apps/engine/core/llm/tools.py`:

### 1. `get_options_sentiment`
* **Purpose**: Fast high-level options market sentiment snapshot (~150 tokens).
* **Parameters**:
  * `ticker` (string, required): e.g. `"AAPL"`, `"NVDA"`, `"SPY"`.
  * `expiration_date` (string, optional): Specific expiration (`"YYYY-MM-DD"`).
* **Metrics Provided**:
  * Put/Call Volume Ratio & Open Interest Ratio
  * Qualitative Bias: `BULLISH (Heavy call volume)`, `BEARISH`, or `NEUTRAL`
  * At-The-Money (ATM) Implied Volatility (IV)
  * 25-Delta Volatility Skew ($\text{IV}_{\text{Put}} - \text{IV}_{\text{Call}}$)
  * Max Pain Strike Price
  * Unusual Options Activity alerts ($\text{Volume} > 3 \times \text{OI}$)

### 2. `get_option_chain`
* **Purpose**: Compact near-the-money options board (~350–500 tokens).
* **Parameters**:
  * `ticker` (string, required): e.g. `"TSLA"`.
  * `expiration_date` (string, optional): Specific expiration date.
  * `contract_type` (string, optional): `"call"`, `"put"`, or `"all"`.
  * `strike_range_pct` (number, default: `10.0`): Bounds returned strikes to $\pm X\%$ of underlying price to avoid token blowups.
  * `min_dte` / `max_dte` (integer, optional): Bounds by Days to Expiration.
* **Fields Provided**: Expiration Date, Type, Strike, Bid, Ask, Last, Volume, Open Interest, Implied Volatility (IV), $\Delta$ (Delta), and $\Gamma$ (Gamma).

---

## Database Caching

* **Table**: `options_data_cache` (created via migration `20260901000000_create_options_data_cache.sql`).
* **Schema**:
  * `ticker TEXT PRIMARY KEY`
  * `metrics JSONB`
  * `contracts JSONB`
  * `fetched_at TIMESTAMPTZ DEFAULT NOW()`
* **TTL**: Configurable via `OPTIONS_CACHE_TTL_SECONDS` (default: 3,600s / 1 hour).
* **In-Memory Cache**: Process-level dictionary cache guarantees subsequent calls within the same turn or session execute in **0ms** without consuming API credits.

---

## Architectural Principle: Pure Pull-Based Data Access

A foundational design principle of the options data integration is **zero forced injection**:

1. **Pull-Based On-Demand Fetching**: Options data is **never hardcoded or pre-injected** into trading agent prompts, the S&P 500 Daily Predictor, or the Sector Predictor. 
2. **Autonomous Tool Selection**: All LLM trading models (DeepSeek, MiniMax, OpenAI, Anthropic, Gemini) and predictors are registered with canonical function calling declarations. The models independently assess their market thesis and determine whether and when to invoke `get_options_sentiment(ticker="...")` or `get_option_chain(ticker="...")`.
3. **Autoresearch Alpha Discovery**: In the [[entities/autoresearch]] loop, the meta-researcher is equipped with both options tools in its toolbox (`#27` and `#28` in `program.md`). It autonomously evaluates whether allocating options inspection tools to specific candidate agent variants improves trading performance and Brier calibration scores.
4. **Token & Rate Efficiency**: By allowing models to pull only the specific tickers and strikes they care about, the pipeline avoids token window bloat and respects API rate limits.

---

## Configuration

In `apps/engine/.env`:

```env
MASSIVE_API_KEY=your_api_key_here
MASSIVE_BASE_URL=https://api.polygon.io
OPTIONS_CACHE_TTL_SECONDS=3600
```

Also accepts `POLYGON_API_KEY` as a backwards-compatible fallback alias.

## Related

- [[entities/tool-registry]] — Canonical tools definition registry
- [[entities/autoresearch]] — Karpathy-style prompt improvement loop using options tools
- [[entities/database]] — Supabase schema and caching layers
- [[concepts/system-heavy-prompt]] — System-heavy and pull-based context injection design
