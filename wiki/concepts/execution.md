---
tags: [execution, trading, validation, settlement]
category: concept
---

# Execution

The execution phase handles pre-market validation, Reg T checks, trade settlement, and attribution. It ensures that all trades are valid, margin-compliant, and properly recorded.

## Pre-Market Validation

Before any trade is executed, the system validates market conditions and fetches live pre-market quotes. This is handled by `MarketDataManager.get_premarket_quote()`.

### Aftermarket Quote Provider

`get_premarket_quote()` now uses a two-tier approach:
1. **Primary**: If the data provider exposes a `get_aftermarket_quote(ticker)` method, it is called first. This returns a dedicated aftermarket quote with `price`, `bid`, `ask`, and `volume`.
2. **Fallback**: If the provider method is unavailable, returns `None`, or raises an exception, the standard quote from `get_quote()` is used.

The pre-market price is then compared to the previous close to compute the overnight gap percentage. When a dedicated aftermarket quote is available, the prior session's regular close is taken from `quote.price` (since `/quote` has not yet rolled over to today during pre-market); in fallback scenarios without aftermarket data, `quote.previous_close` or historical bar data is used.

### Concurrent Proxy Fetching

For the daily predictor's market context, pre-market quotes for macro proxies (QQQ, DIA, IWM, IEF, GLD, USO, UUP) are fetched concurrently using `asyncio.gather`. Partial failures are handled gracefully — failed proxies are skipped without breaking the entire context. This ensures robustness against transient API failures.

## Reg T Checks

Regulation T margin requirements are enforced before trade settlement. The system checks that the portfolio has sufficient buying power and that the trade does not exceed margin limits. See [[sources/reg-t-calculations-source]] for detailed formulas.

## Trade Settlement

Trades are settled using the "Commit at the End" pattern to prevent phantom deductions. Orders are placed via Alpaca's API, and order status is synced asynchronously via [[concepts/alpaca-order-sync]].

## Related

- [[entities/engine]]
- [[entities/daily-market-predictor]]
- [[concepts/alpaca-order-sync]]
- [[sources/reg-t-calculations-source]]
