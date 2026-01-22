# Pre-Market Validation (Hallucination Guardrails)

## Overview
The Pre-Market Validation layer is a critical safety filter in the AI Wall Street pipeline. It sits between the **LLM Analysis Phase** and the **Trade Attribution/Execution Phase**. Its purpose is to verify that AI-generated trade signals are based on real-world facts and meet minimum liquidity requirements.

## Why It Matters
LLMs, while powerful, can occasionally:
1. **Hallucinate Tickers**: Suggesting non-existent stock symbols (e.g., `XYZABC`).
2. **Hallucinate Prices**: Suggesting a "Buy AAPL at $50" when the current market price is $150.
3. **Target Illiquid Assets**: Suggesting trades for low-volume "penny stocks" that would be impossible to execute in a real portfolio without massive slippage.

## Guardrails Implementation

### 1. Guardrail A: Ticker Existence
- **Logic**: Queries the Financial Provider (e.g., Financial Modeling Prep) to see if the ticker is active and tradable.
- **Action**: Reject trade if the ticker is not found.

### 2. Guardrail B: Price Banding
- **Logic**: Compares the AI's suggested price with the current live/delayed market price.
- **Limit**: **Max 15% deviation**.
- **Action**: Reject trade if the price difference is too large.

### 3. Guardrail C: Liquidity Check
- **Logic**: Checks the total Market Capitalization of the company.
- **Limit**: **Minimum $2 Billion**.
- **Action**: Reject trades for companies with insufficient market cap.

### 4. Guardrail D: SMA Floor (Margin Compliance)
- **Logic**: Calculates the projected SMA after the trade (Current SMA - 57% of Cost).
- **Limit**: **Minimum 10% of Total Equity**.
- **Action**: Reject trades that would push the account too close to a Reg T violation.

### Market Data Manager & Caching
The engine now uses a centralized `MarketDataManager` that handles all ticker queries with a **cache-first** policy.

- **Persistence**: Results are stored in the `market_data_cache` table in Supabase.
- **TTL**: Cached data is considered fresh for **4 hours**.
- **Efficiency**: Reduces external API (yfinance/FMP) calls by $>90%$ for common tickers.
- **Files**: `apps/engine/execution/market_data.py`, `apps/engine/execution/providers/factory.py`.

### Anti-Rate Limiting (Throttling)
To prevent hitting API rate limits, the engine implements configurable throttling via `FINANCIAL_API_THROTTLE_SECONDS`. 

## Configuration
The following environment variables and constants control the validation behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_MARKET_CAP_BILLIONS` | `2.0` | Minimum company value to allow a trade. |
| `MAX_PRICE_DEVIATION_PCT` | `15.0` | Maximum % difference between AI and market price. |
| `FINANCIAL_PROVIDER` | `"yfinance"` | Which API implementation to use (`fmp` or `yfinance`). |
| `FINANCIAL_API_THROTTLE_SECONDS` | `2.0` | Delay between consecutive API calls (in seconds). |

## Pipeline Integration
Validation is now a **Two-Layer Process**:
1. **Active Tool**: Models call `get_stock_quote` during analysis to verify their own reasoning.
2. **Final Gauntlet**: The engine runs `validate_decision` in `main.py` before persistence to ensure no hallucinations slipped through.

If a trade is rejected, a `logger.warning` is triggered, and the trade is skipped.
