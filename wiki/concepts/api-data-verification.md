---
tags: [architecture, api, testing, validation, market-data]
category: concept
---

# API Integration & Data Sanity Verification

Protocol and standards for integrating external market data and LLM APIs to guarantee data plausibility, prevent silent errors, and handle multi-tier API subscription constraints gracefully.

## Purpose

External financial APIs (e.g. Polygon/Massive, FMP, FRED, Alpaca) exhibit differing subscription entitlements, rate limit behaviors, and response structures across endpoints. When integrating new APIs or fallback pipelines, relying solely on HTTP 200 checks or schema presence without validating physical and financial plausibility leads to severe model hallucinations and degraded quantitative predictions.

---

## The 4 Pillars of API Data Sanity

```
+-------------------------------------------------------------------------+
|                  API INTEGRATION SANITY CHECKLIST                       |
+-------------------------------------------------------------------------+
|  1. HTTP Status Audit     | Explicitly handle 401/403 tiers & 429 limits|
|  2. Domain Bounds Check   | Validate values fall within financial bounds|
|  3. Spot Price Alignment  | Ground derivative calculations in real spot |
|  4. Distribution Balance  | Verify symmetric data (e.g. Calls & Puts)   |
+-------------------------------------------------------------------------+
```

### 1. HTTP Status & Subscription Tier Auditing
- **Zero Unhandled HTTP Errors**: API integrations must never silently swallow `403 Forbidden` / `401 Unauthorized` responses or treat them as empty data.
- **Explicit Fallback Pipelines**: When paid endpoints (e.g. Massive Options Snapshots) return `403 NOT_AUTHORIZED` on Free Tier accounts, the client must automatically route to supported free-tier endpoints (e.g. reference contracts + previous day EOD bars) with local pricing engines (Black-Scholes).
- **Proactive Rate Limiting & Backoff**: Free-tier endpoints frequently enforce strict limits (e.g. 5 requests per minute). Integrations must use asynchronous token bucket limiters (`AsyncTokenBucketLimiter`) with automatic backoff retry to avoid cascading `429 Too Many Requests` dropouts.

### 2. Domain & Bounds Validation
Calculated or parsed market data must be sanity-checked against standard financial bounds:
- **Implied Volatility (IV)**: Index ATM IV (e.g. SPY) typically ranges between $8\%$ and $80\%$. An IV of $500\%$ indicates boundary search failure or incorrect spot price inputs.
- **Put/Call Ratios**: A volume or open interest ratio of $0.0$ on major index ETFs like SPY indicates query truncation (e.g. sorting returning only calls) rather than genuine zero put activity.
- **Pricing & Yields**: Bond yields, commodity prices, and ETF quotes must reflect current market scale (e.g. validating positive prices and expected order of magnitude).

### 3. Spot Price Alignment
Derivative metrics (Greeks, moneyness, implied volatility, Max Pain) must always be calculated against the underlying asset's true spot price:
- Never approximate spot price as the average of returned strike prices.
- Resolve real-time or previous close spot quotes via `MarketDataManager().get_quote(ticker)` prior to running Black-Scholes solvers.

### 4. Distribution Balance in Filtered Queries
When paginating or querying options contracts from endpoints that sort alphabetically (`"contract_type": "call"` before `"put"`):
- Never query with generic limits (e.g. `limit=100`) expecting balanced results.
- Issue discrete queries for `contract_type="call"` and `contract_type="put"` bounded near the spot price (`strike_price.gte` and `strike_price.lte`).

---

## Lessons Learned: Massive.com Options Integration

During the initial deployment of the [[entities/massive-options]] pipeline, two subtle integration traps were diagnosed and resolved:

1. **Alphabetic Sort Trap**: Querying `/v3/reference/options/contracts` with `limit=100` without filtering by `contract_type` returned 100 calls and 0 puts, skewing the Put/Call ratio to `0.0`. Fixed by querying calls and puts separately within $\pm 4\%$ of the spot price.
2. **Missing Spot Reference Trap**: Calculating Black-Scholes IV without passing the true SPY spot price ($761.78) caused deep ITM calls to be priced against an estimated strike average ($640.00), resulting in an artificial $500\%$ IV ceiling hit. Fixed by auto-resolving spot quotes in `get_options_snapshot`.

---

## Related

- [[entities/massive-options]] — Massive.com options data provider and Black-Scholes solver
- [[entities/engine]] — Engine backend architecture and market data execution
- [[concepts/observability-standard]] — Logging and traceback observability guidelines
- [[entities/daily-market-predictor]] — Daily S&P 500 prediction pipeline
