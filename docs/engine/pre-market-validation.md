# Pre-Market Validation (Hallucination Guardrails)

## Overview
The Pre-Market Validation layer is a critical safety filter in the AI Wall Street pipeline. It sits between the **LLM Analysis Phase** and the **Trade Attribution/Execution Phase**. Its purpose is to verify that AI-generated trade signals are based on real-world facts and meet minimum liquidity requirements.

## Why It Matters
LLMs, while powerful, can occasionally:
1. **Hallucinate Tickers**: Suggesting non-existent stock symbols (e.g., `XYZABC`).
2. **Hallucinate Prices**: Suggesting a "Buy AAPL at $50" when the current market price is $150.
3. **Target Illiquid Assets**: Suggesting trades for low-volume "penny stocks" that would be impossible to execute in a real portfolio without massive slippage.

## Guardrails Implementation

### 0. Guardrail 0: Market Hours
- **Logic**: Checks if the US stock market is currently open and not on a holiday.
- **Provider**: Uses Financial Modeling Prep (FMP) API with a time-based fallback (09:30-16:00 ET, Mon-Fri).
- **Action**: Reject trade if the market is closed.
- **File**: `MarketDataManager.is_market_open()` in `execution/market_data.py`.
- **Caching**: Implements a **class-level cache with 5-minute TTL** to avoid redundant API calls. The market status is fetched once per pipeline run and shared across all validation layers (ingestion guardrail, pre-trade validation, price update script). This reduces FMP API calls by ~99% during execution while maintaining holiday awareness.

### 1. Guardrail A: Ticker Existence
- **Logic**: Queries the Financial Provider (e.g., Financial Modeling Prep) to see if the ticker is active and tradable.
- **Action**: Reject trade if the ticker is not found.

### 2. Guardrail B: Price Banding
- **Logic**: Compares the AI's suggested price with the current live/delayed market price.
- **Limit**: **Max 5.0% deviation**.
- **Action**: Reject trade if the price difference is too large.

### 3. Guardrail C: Liquidity Check
- **Logic**: Checks the total Market Capitalization of the company.
- **Limit**: **Minimum $2 Billion**.
- **Action**: Reject trades for companies with insufficient market cap.

### 4. Guardrail D: Buying Power
- **Logic**: Compares the estimated trade cost against the agent's current Reg T Buying Power.
- **Action**: Reject trade if cost exceeds available buying power.

### 5. Guardrail E: Minimum Trade Value
- **Logic**: Verifies that the total value of the trade (Price * Quantity) meets a minimum threshold. This prevents small, insignificant trades that don't move the needle for the portfolio (e.g., buying 1 share for $100).
- **Limit**: **$1,000 USD** (1/10th of the default starting balance).
- **Action**: Reject trades below the threshold (waived for SELL orders if a sell tool is used).

### 6. Guardrail F: SMA Floor (Margin Compliance)
- **Logic**: Calculates the projected SMA after the trade (Current SMA - 57% of Cost).
- **Limit**: **Minimum 10% of Total Equity**.
- **Action**: Reject trades that would push the account too close to a Reg T violation.

### 7. Guardrail G: Hallucination & NaN Filter
- **Logic**: Inspects the ticker string for invalid characters, and verifies that the retrieved market price is not `NaN` or `None`.
- **Action**: Immediately reject the trade if the ticker format is invalid or if the data provider returns non-compliant `NaN` values. This ensures JSON compliance when saving decisions to the database.

### 8. Guardrail H: Price Backfill (LLM Laziness Buffer)
- **Logic**: If an LLM identifies a valid ticker but fails to provide a price in its JSON output (or returns 0), the engine automatically attempts to fetch the latest market price.
- **Action**: Backfills the `price` field in the `DecisionObject` before it reaches the final validation phase. This prevents "lazy" models from being rejected for missing data if their ticker intent was clear.

### 9. Guardrail I: Semantic Redundancy (Overtrading Prevention)
- **Logic**: Uses vector embeddings to compare the reasoning of a new trade signal against the reasonings of recently executed trades (last 24 hours) for the same ticker **and the same agent**.
- **Limit**: **Cosine Similarity > 0.90**.
- **Agent Isolation**: The semantic overlap check is **agent-specific**. For example, if CLAUDE recently traded NKE on earnings news, only CLAUDE will be blocked from making a similar NKE trade. Other agents (HAIKU, OpenAI, Gemini, etc.) can still trade NKE independently, as they maintain separate portfolios and decision contexts.
- **Action**: Reject the trade if it is based on the same sentiment or catalyst that **the same agent** has already acted upon. This prevents overtrading when the ingestion loop runs frequently, while allowing different agents to act on the same market opportunities independently.

### Market Data Manager & Caching
The engine now uses a centralized `MarketDataManager` that handles all ticker queries with a **cache-first** policy and a single configured market data provider.

- **Persistence**:
  - **Cache**: The latest price results are stored in the `market_data_cache` table in Supabase.
  - **History**: A permanent record of every price fetch is stored in the `price_history` table for historical analysis. The engine uses **Batch Upserts** to minimize database roundtrips when saving historical data.
- **Robustness**: 
  - **Retries**: The configured provider is attempted a configurable number of times (Default: 2) with backoff before falling back to the last known historical price.
  - **NaN Filter**: Automatically identifies and rejects `NaN` float values from providers, ensuring only valid numerical data is cached or used for validation.
- **TTL**: Cached data in `market_data_cache` is considered fresh for **2 seconds** (configurable).
- **Efficiency**: Reduces external API calls by $>90%$ for common tickers.
- **Files**: `apps/engine/execution/market_data.py`, `apps/engine/execution/providers/factory.py`.

### Anti-Rate Limiting (Throttling)
To prevent hitting API rate limits, the engine implements configurable throttling via `FINANCIAL_API_THROTTLE_SECONDS`. 

## Configuration
The following environment variables and constants control the validation behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_MARKET_CAP_BILLIONS` | `2.0` | Minimum company value to allow a trade. |
| `MAX_PRICE_DEVIATION_PCT` | `5.0` | Maximum % difference between AI and market price. |
| `MIN_TRADE_VALUE` | `1000.0` | Minimum purchase/sell value (waived for SELL via tools). |
| `FINANCIAL_PROVIDER` | `"fmp"` | Primary data provider. |
| `MARKET_DATA_RETRIES` | `2` | Number of attempts per provider. |
| `MARKET_DATA_CACHE_TTL_SECONDS` | `2` | Price cache duration (2 seconds). |
| `FINANCIAL_API_THROTTLE_SECONDS` | `2.0` | Delay between consecutive API calls (in seconds). |

## Pipeline Integration
Validation is now a **Three-Layer Process**:
1. **Active Tool**: Models call `get_stock_quote` during analysis to verify their own reasoning.
2. **Post-Analysis Backfill**: The engine (in `analyze.py`) backfills missing prices for valid tickers to handle LLM extraction failures.
3. **Market Guardrails**: The engine runs `validate_decision` in `main.py` to ensure ticker existence, liquidity, and price sanity.
4. **Second-Step Verification**: A skeptical "Verifier" agent (using the original provider's intelligence) audits every BUY/SELL signal using specialized tools to identify "priced in" news and failure modes.
5. **Hard Tool Enforcement**: The engine performs a mandatory server-side scan of the conversation history to confirm that required tools were actually executed. This scan is **robust to formatting variances**, normalizing tickers (stripping spaces, upper-casing) to ensure compliance.
6. **Reg T & Compliance**: Final margin and allocation checks before trade settlement.

If a trade is rejected, a `logger.warning` is triggered, and the trade is skipped.
