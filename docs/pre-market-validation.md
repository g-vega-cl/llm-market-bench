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
- **Limit**: **Max 10% deviation**.
- **Action**: Reject trade if the price difference is too large.

### 3. Guardrail C: Liquidity Check
- **Logic**: Checks the total Market Capitalization of the company.
- **Limit**: **Minimum $2 Billion**.
- **Action**: Reject trades for companies with insufficient market cap.

### Modular Provider Interface
The system uses a plug-and-play architecture. The `FinancialProvider` abstract base class allows us to swap API providers (e.g., from FMP to Polygon or Alpha Vantage) without rewriting the core validation logic.

- **Interface**: `apps/engine/execution/providers/base.py`
- **FMP Implementation**: `apps/engine/execution/providers/fmp.py`
- **Optimization**: Uses the `/stable/quote` endpoint which consolidates price and market cap into a **single API call**, reducing latency and quota usage.

### Anti-Rate Limiting (Throttling)
To prevent hitting API rate limits during bulk analysis, the engine implements configurable throttling via `FINANCIAL_API_THROTTLE_SECONDS`. 

## Configuration
The following environment variables and constants control the validation behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_MARKET_CAP_BILLIONS` | `2.0` | Minimum company value to allow a trade. |
| `MAX_PRICE_DEVIATION_PCT` | `10.0` | Maximum % difference between AI and market price. |
| `FINANCIAL_PROVIDER` | `"fmp"` | Which API implementation to use. |
| `FINANCIAL_API_THROTTLE_SECONDS` | `0.0` | Delay between consecutive API calls (in seconds). |

## Pipeline Integration
Integrated in `apps/engine/main.py`. If a trade is rejected, a `logger.warning` is triggered, and the trade is skipped before it ever hits the database or the broker.
