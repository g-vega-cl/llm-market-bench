---
tags: [verifier, etf, valuation, dcf, prompt-engineering]
category: concept
---

# ETF & Index Fund Valuation Exemption

The verifier's standard intrinsic valuation step relies on `audit_financial_valuation`, which runs a server-side DCF (Discounted Cash Flow) and comparable peer multiple audit. That works for single stocks, but it cannot run against ETFs and index funds, which do not file standalone GAAP income or cash-flow statements.

## The Rule

The `VERIFIER_SYSTEM_PROMPT` explicitly exempts index, sector, and commodity ETFs (e.g. `SPY`, `QQQ`, `XLV`, `XLE`, `IWM`) from the single-stock DCF requirement. When `audit_financial_valuation` returns no key metrics for such a ticker, the verifier must **not** reject the trade solely on that basis. Instead it evaluates the ETF using:

- macroeconomic regime alignment
- moving average trend
- sector concentration

## Why It Matters

Without the exemption, buy proposals for ETFs were blocked because the verifier demanded single-stock DCF audits that cannot exist for funds. This caused portfolios such as `haiku-5-5` to fail to execute ETF trades even when the macro thesis was sound.

## Related

- [[concepts/verifier-bypass]] — the verifier SOP and its bypass tooling
- [[concepts/execution]] — pre-market validation, Reg T checks, trade settlement
