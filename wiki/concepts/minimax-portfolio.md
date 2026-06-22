---
tags: [minimax, execution, concepts, margin, portfolio]
category: concept
---

# MiniMax-M3 Simple Portfolio

The MiniMax-M3 Simple Portfolio represents a high-velocity, low-friction execution path within the LLM Market Bench platform. Designed for the `MiniMax-M3` model provider, this portfolio demonstrates how a simplified order and verification structure can optimize responsiveness while maintaining strict risk controls.

## Design Rationale

Standard portfolios on the platform (OpenAI, Anthropic, Gemini, DeepSeek) are subjected to a rigorous **4-Layer Defense System** to prevent hallucinations, check semantic redundancies, verify against historical post-mortems, and validate stale market data. While highly robust, these checks add computational overhead and can sometimes prematurely block valid signals due to strict formatting rule sets.

The MiniMax portfolio implements a **Simplified Execution Pipeline**:

```mermaid
graph TD
    A[Newsletter Summaries] -->|MiniMax OpenAI Client| B[Standard Tool Call Loop]
    B -->|Instructor Mode| C[DecisionsResponse]
    C -->|Skip Verifier Checks| D[Reg T Compliance Guard]
    D -->|Passed| E[Market Order Execution]
    D -->|Failed| F[REJECTED_MARGIN]
    E -->|±0.5% Slippage Buffer| G[Portfolio Executed & Alpaca Mirror]
```

By removing intermediary check-and-balance steps (like the Verifier Agent), the MiniMax agent trades with raw cognitive output, operating in a simplified cash/ownership context while remaining firmly inside the system's margin constraints. However, it now participates in standard tool calling loops (like web searches, database RAG, and newsletter content fetching) just like standard models.

---

## Simplified Pipeline Comparison

| Verification Layer | Standard Portfolios | MiniMax Portfolio |
| :--- | :--- | :--- |
| **Layer 1: Pre-Prompt Strengthening** | ✅ Enforced | ✅ Enforced |
| **Layer 2: Context Enhancement** | ✅ Enforced | ✅ Enforced |
| **Layer 3: Post-Analysis Verification** | ✅ Enforced | ❌ Bypassed |
| **Layer 4: Structured Output Isolation** | ✅ Enforced | ✅ Enforced (via Instructor) |
| **Semantic Overlap & Redundancy** | ✅ Validated | ❌ Bypassed |
| **Stale Quote Drift (>2% Guardrail)** | ✅ Validated | ❌ Bypassed |
| **Reg T Margin / Buying Power Floor** | ✅ Enforced | ✅ Enforced |
| **Asset Ownership Stop (SELL)** | ✅ Enforced | ✅ Enforced |

---

## Market Order execution & ±0.5% Buffer

Rather than placing `DAY` limit orders directly at the JIT market price, the MiniMax execution engine utilizes **Market Orders** modeled with a **±0.5% execution slippage buffer** to ensure near-instantaneous execution during live simulation:

### 1. Engine Buy/Sell Offset
* **BUY Decisions**: The execution price is adjusted upward by `0.5%` to simulate buying at the ask price in a high-liquidity order book.
  $$\text{Price}_{\text{exec}} = \text{round}(\text{Price}_{\text{market}} \times 1.005, 2)$$
* **SELL Decisions**: The execution price is adjusted downward by `0.5%` to simulate selling at the bid price.
  $$\text{Price}_{\text{exec}} = \text{round}(\text{Price}_{\text{market}} \times 0.995, 2)$$

### 2. Alpaca Paper Mirroring
To maintain synchronization with real broker mechanics, the corresponding Alpaca paper trading limit orders are mirrored using the same `0.5%` offset applied on top of the calculated `exec_price`:
* **Alpaca BUY Limit**: $\text{round}(\text{Price}_{\text{exec}} \times 1.005, 2)$
* **Alpaca SELL Limit**: $\text{round}(\text{Price}_{\text{exec}} \times 0.995, 2)$

To prevent duplicate Alpaca submissions (since the shared `portfolio.execute_trade` method automatically schedules a default `0.5%` slippage mirror), the MiniMax pipeline passes `skip_alpaca_mirror=True` to `execute_trade`. This bypasses the standard mirroring flow, allowing the custom `0.5%` offset mirror to run cleanly inside `main.py` without duplicate `client_order_id` rejections.

---

## Retained Risk Guardrails

While the MiniMax portfolio bypasses post-analysis verifier checks and semantic validators, it remains 100% compliant with the underlying financial and asset-sanity boundaries of the system:

1. **Existence & Liquidity Checks**: The ticker must exist on Financial Modeling Prep (FMP) and have a market capitalization exceeding the platform's liquidity floor.
2. **Market Hours Compliance**: Orders can only be processed during active US market hours.
3. **Hard Ownership Stop**: SELL orders targeting assets that do not exist in the active `positions` ledger are immediately rejected (`REJECTED_OWNERSHIP`). Additionally, requested quantities exceeding the active position are automatically capped to the quantity currently held.
4. **Reg T Margin Validation**: The trade is evaluated JIT by `portfolio.validate_trade()` to ensure it does not breach initial margin requirements, maintenance margin thresholds, or SMA boundaries. If buying power is insufficient, the trade is rejected with `REJECTED_MARGIN`.

---

## Leaderboard Metrics Adjustment

Because MiniMax-M3 operates on a simplified execution pipeline bypassing the verifier and tool-scans (Layer 3), its **verifier approval rate metric is ignored** on the LLM Leaderboard (returning `NULL`).

Consequently, the calculation of its reasoning and composite scores is adjusted automatically at the database layer:
* **Reasoning Quality Score**: Set to $100\%$ of average self-reported confidence, omitting the verifier rate check.
* **Composite Leaderboard Score**: Weighted as:
  $$\text{Composite Score} = (0.5 \times \text{Performance Score}) + (0.3 \times \text{Average Confidence}) + (0.2 \times \text{Consistency Score})$$

See `[[entities/llm-leaderboard]]` for more details.

---

## Extraction and Parser Alignment

MiniMax-M3 is OpenAI API compatible and is fully integrated into the standard LLM tool execution loop using an Instructor-wrapped async OpenAI client. It leverages Instructor's structured tool-calling mode to guarantee that the primary Analysis Agent output conforms directly to the `DecisionsResponse` schema without requiring raw text JSON repair or extraction workarounds.

However, for auxiliary modules that use the raw MiniMax Text Chat API directly (e.g., the [[concepts/market-feeling]] generator), the following robustness logic is preserved in the underlying `MiniMaxClient` utility:
1. **Explicit Schema Enforcement:** The prompt template specifically instructs the model on the exact JSON schema fields to prevent validation errors at execution time.
2. **Conditional Unescaping & Escape Alignment:** The JSON repair helper (`_repair_json_string`) performs quote (`\"` to `"`) and backslash-escaped newline unescaping inside double-escaped strings to ensure JSON compatibility.
3. **Robust Scope Binding:** Fallback strategy lambdas bind repaired variables correctly to avoid closed-over variable references that could lead to evaluation failures.
4. **Raw Control Character Resiliency:** All `json.loads` calls in the MiniMax client and repair utilities use `strict=False` to tolerate unescaped control characters such as newlines or carriage returns in reasoning content.

---

## Safety and Censorship Failure Modes

Due to MiniMax being hosted by a Chinese provider with strict content moderation policies, the model is highly sensitive to geopolitical keywords (e.g. "Iran Deal", "Strait of Hormuz", "military conflicts").
* **Symptom**: The API returns a `200 OK` extremely rapidly (e.g. 2ms) but with a blank choice content or finish reason other than `stop`.
* **Observability & Logging**:
  - **Empty Content/Choices**: If the API returns a success status but contains empty choices or the final extracted content is blank, the engine logs a warning containing the full raw response for diagnostics.
  - **HTTP Status Errors**: If the MiniMax API returns a non-200 HTTP status code, `MiniMaxClient` catches the `httpx.HTTPStatusError`, extracts and logs the detailed response body (e.g., quota or authorization failure messages), and re-raises it.
  - **Business Logic Errors (`base_resp` or `error`)**: MiniMax sometimes returns `200 OK` but includes errors in the JSON body (under `base_resp` or `error` keys). `MiniMaxClient` parses these keys, logs the specific error message, and raises a `ValueError` to ensure visibility.

---

## Related Pages

* [[entities/engine]]
* [[concepts/execution]]
* [[concepts/tool-enforcement]]
* [[sources/reg-t-calculations-source]]
