---
tags: [hallucination, audit, tools, verification]
category: concept
---

# Empirical Hallucination Audit & Validation

This document records the empirical audit of numerical hallucination across LLM Market Bench reasoning logs, comparing how early design assumptions were resolved by the four-layer tool enforcement architecture.

---

## Context: The Original Number Hallucination Problem

Early iterations of the trading pipeline asked language models to generate target execution prices, calculate exact share quantities, and propose limit prices directly in their structured JSON output.

This design caused recurring hallucinations:
- Models invented stale or fictional stock prices (e.g. estimating a stock at $150 when the real price was $220).
- Models failed basic arithmetic on portfolio sizing, proposing share quantities that exceeded available cash or violated margin requirements.
- Models asserted that trades were appropriately sized without running calculations against actual account equity.

---

## The Architectural Fix

Rather than relying on model arithmetic, the system moved calculations and price validation entirely to server-side code:

1. **Pre-Injected Prices (`VERIFIED MARKET DATA`):** The Python engine fetches real-time quotes before prompt assembly and injects them as verified facts.
2. **Calculation-Forward Tools:** Models are forbidden from guessing share quantities. They must call `calculate_buy_quantity(ticker, percentage)` and `calculate_sell_quantity(ticker, percentage)`, where Python evaluates cash, buying power, and the 10% portfolio equity floor.
3. **Output Isolation & Execution Authority:** The decision schema strips price and quantity generation. The model outputs only `ticker`, `signal`, and `allocation_percentage`. The engine computes limit prices and execution quantities dynamically at fill time.
4. **Verifier Second-Pass:** A separate verifier model evaluates portfolio concentration and quote drift (>2% drift triggers `REJECTED_STALE_QUOTE`).

---

## Production Audit (August 25 – September 1, 2026)

To test whether models still hallucinate numbers in qualitative text rationales (such as P/E ratios, standard deviations, or returns), an audit of 200 production reasoning logs from `llm_reasoning_logs` was conducted.

### Audit Pipeline

1. **Dataset:** 200 multi-turn logs across tasks (`INGESTION`, `CONSENSUS`, `MACRO_EXTRACTION`, `VERIFICATION`) and models (`deepseek-v4-pro`, `gpt-5.6-luna`, `gemini-3.5-flash-lite`, `MiniMax-M3`, `claude-haiku-4-5`).
2. **Number Extraction:** Regular expressions matched every dollar amount, percentage, valuation multiple, and scale unit across `reasoning`, `scenarios`, and `verification_reasoning` fields.
3. **Context Matching:** Every extracted number was matched against the full multi-turn prompt payload, including pre-injected market blocks, portfolio state, and live tool execution returns.

### Results

- **Ungrounded Numbers Found:** 0 out of 200 production logs.
- **Finding:** Every cited price, return percentage, valuation multiple, and statistical deviation was traced to either pre-injected context or a live tool return.

---

## Production Walkthrough Examples

### 1. DeepSeek v4 Pro (Task: Ingestion / Portfolio Evaluation)

- **LLM Reasoning Output:**
  > "MRK is a profitable winner (+17.1%) with a new blockbuster catalyst and cheap valuation (~14.9x forward P/E, 4.7% FCF yield). Deals were struck with 9 mid-sized drugmakers for voluntary Medicaid price cuts plus $19.6B in manufacturing commitments."
- **Grounding Audit:**
  - `+17.1%`: Found in injected `<CURRENT_PORTFOLIO_LEDGER>` unrealized gain field for MRK.
  - `9 mid-sized` and `$19.6B`: Injected in news batch from StockAnalysis briefing.
  - `14.9x`: DeepSeek executed tool `get_key_metrics(ticker="MRK")`, which returned `Forward P/E: 14.87`. The model rounded 14.87 to 14.9x.
  - `4.7%`: Returned by `get_key_metrics` as `Free Cash Flow Yield: 4.69%`. The model rounded 4.69% to 4.7%.

### 2. MiniMax-M3 (Task: Ingestion / Energy Trade Evaluation)

- **LLM Reasoning Output:**
  > "XOM sits at -1.36 standard deviations BELOW its 14-day mean ($156.71 vs $161.24 avg), having drifted down from $166.15 on Aug 20... SPR at 286.8M barrels, the lowest since 1982..."
- **Grounding Audit:**
  - `-1.36 standard deviations`, `$156.71`, `$161.24`, `$166.15`: Returned directly by tool call `get_volatility_metrics(ticker="XOM", days=14)`.
  - `286.8M barrels`, `1982`: Injected in prompt news context regarding energy reserves.

### 3. GPT-5.6 Luna (Task: Trade Verification on XLE)

- **LLM Verifier Output:**
  > "The proposed 76-share purchase would require approximately $4,899.72, or about 50.6% of stated total equity, creating excessive concentration for a probabilistic geopolitical catalyst." Status: `REJECTED_VERIFICATION`.
- **Grounding Audit:**
  - Proposed order in verifier input: `76` shares at `$64.47` price (`76 * 64.47 = $4,899.72`).
  - Total account equity in verifier input: `$9,680.12`.
  - Evaluated fraction: `$4,899.72 / $9,680.12 = 50.61%`.

---

## Conclusion & Status

The roadmap requirement to eliminate number hallucinations and implement calculation-forward tooling is fully satisfied by the four-layer enforcement system. Trade execution calculations are handled by deterministic Python code, while qualitative reasoning metrics are backed by tool calling and pre-injected data feeds.

---

## Related

- [[concepts/tool-enforcement]]
- [[concepts/auditability]]
- [[concepts/observability-standard]]
- [[entities/pipeline]]
