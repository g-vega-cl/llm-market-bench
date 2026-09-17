---
tags: [concept, llm, reasoning, thinking, tools, architecture]
category: concept
---

# Thinking Agents Architecture

The **Thinking Agents Architecture** defines how reasoning models operate across `llm-market-bench` pipelines without colliding with function-calling capabilities.

---

## 1. Why We Did Not Use Thinking Mode Before

In earlier iterations of the engine, extended thinking was disabled or suppressed across tool loops and extraction tasks due to four critical API protocol and behavioral blockers:

### A. Forced Tool Choice Collisions (400 Invalid Request)
Structured extraction libraries (such as Instructor with `Mode.TOOLS` or `Mode.ANTHROPIC_TOOLS`) defaulted to forcing function execution via `tool_choice={"type": "tool", "name": ...}`.
- **The Conflict**: Both Anthropic and other major API gateways explicitly reject requests when extended thinking is enabled alongside a forced `tool_choice`:
  ```text
  400 Invalid Request: tool_choice is not supported with extended thinking enabled.
  ```
- **Consequence**: When thinking was turned on, structured trade extraction immediately threw 400 errors, causing the engine to fall back to ungrounded heuristics or fail entirely.

### B. Tool Call Narration Hallucination (DeepSeek R1/Flash)
When reasoning models received tool declarations with thinking enabled in the prompt loop, they frequently described their intent to call tools in English prose inside the `<think>` reasoning block (e.g., *"Let me call `get_stock_quote` for NVDA to see the price..."*) rather than emitting the structured API `tool_calls` payload.
- **The Conflict**: The API returned zero function calls in the message object. The engine's tool loop saw no tools invoked, terminated prematurely, and the trade was rejected by HARD ENFORCEMENT rules.

### C. Discarded Multi-Turn Cryptographic Signatures (Anthropic)
Anthropic's Messages API enforces a strict state-preservation contract for extended thinking:
- If Turn 1 emits a `ThinkingBlock` with a cryptographic `signature`, **any subsequent turn in that conversation MUST echo the exact `ThinkingBlock` and `signature` back in the assistant history**.
- **The Conflict**: Early engine handlers stripped incoming message history down to basic `text` and `tool_use` blocks before calling Turn 2. When the engine fed back the tool results, Anthropic rejected Turn 2 with:
  ```text
  400 Invalid Request: Thinking blocks must be preserved in assistant messages when thinking is enabled.
  ```

### D. Assistant Prefill Prohibition and Empty Content
Extended thinking strictly prohibits assistant message prefill.
- When an agent completed its tool calls, the conversation often ended with an assistant message.
- If that assistant turn only contained internal thinking, stripping the block resulted in `content=""`.
- When passed to the final extraction step, Anthropic treated the trailing assistant turn as an empty prefill, resulting in `stop_reason="end_turn"`, zero output tokens, and `content=[]`. This caused Instructor to fail with `IndexError: list index out of range`.

### E. OpenAI `/v1/chat/completions` Function Tool Block
OpenAI's `/v1/chat/completions` API explicitly disallows `reasoning_effort != 'none'` whenever function tools or tool call messages are present in the conversation history:
```text
400 Invalid Request: Function tools with reasoning_effort are not supported for gpt-5.6-luna in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort to 'none'.
```

---

## 2. Why We Use Thinking Mode Now

We enabled thinking mode across all competing models because market reasoning requires deep, multi-step deliberation over messy quantitative data (valuation multiples, options open interest, macro inflection points, and catalyst dates). As demonstrated in live tests, thinking agents evaluate disconfirming evidence and reject bad trades with high conviction rather than chasing momentum.

We resolved each historical blocker through four architectural solutions:

### Solution 1: Decoupled Extraction Modes (`Mode.ANTHROPIC_JSON` & `Mode.MD_JSON`)
In `apps/engine/core/llm/clients.py`, we configured Anthropic and MiniMax clients to use `mode=instructor.Mode.ANTHROPIC_JSON`, and DeepSeek to use `mode=instructor.Mode.MD_JSON`.
- Structured extraction operates via JSON schema guidance in the prompt/system instruction rather than forcing `tool_choice`.
- Thinking budgets (1,024 to 2,048 tokens) now run freely during extraction without triggering 400 gateway errors.

### Solution 2: State-Preserving Multi-Turn Loops
In `apps/engine/core/llm/handlers/anthropic.py`, the assistant content accumulator explicitly preserves `content_block.type == "thinking"`, storing both `thinking` text and `signature`.
- The agent can think in Turn 1, call Tool A (`get_stock_quote`), receive the quote in Turn 2, think about the price, call Tool B (`get_options_sentiment`), and complete the analysis with full contextual awareness.

### Solution 3: Turn-Ending and Extraction Guarantees
In `apps/engine/core/llm/verification.py` and `apps/engine/core/llm/analysis.py`:
- Thinking blocks are preserved as `[Thinking: ...]` in flattened transcripts so downstream extraction models inherit the deliberation context.
- If the conversation ends with an `assistant` or `model` turn, the engine automatically appends an explicit `user` turn (`"Based on the preceding evaluation, extract and structure the final result..."`).
- For Anthropic, `system` content is extracted to the top-level `system` parameter rather than remaining in the `messages` array.
- This eliminates assistant prefill errors and guarantees non-empty structured completions.

### Solution 4: Targeted Per-Provider Allocation
Rather than applying a naive global toggle, thinking parameters are tailored to each provider's exact API contract:

| Model | Provider | Tool Loop Strategy | Extraction Strategy | Implementation |
| :--- | :--- | :--- | :--- | :--- |
| `claude-haiku-4-5` | Anthropic | Active (`budget_tokens: 2048`) with preserved signatures | Active (`budget_tokens: 1024-2048`) | `Mode.ANTHROPIC_JSON` in `clients.py`, signature loop in `handlers/anthropic.py` |
| `gemini-3.5-flash-lite` | Gemini | Active via `ThinkingConfig(thinking_budget=2048)` | Active (`thinking_budget=1024-2048`) | `types.Content` preservation in `handlers/gemini.py` |
| `deepseek-v4-flash` | DeepSeek | Suppressed during tool calls (prevents prose narration) | Active via `extra_body={"thinking": {"type": "enabled"}}` | Enabled in `daily_predictor`, `sector_predictor`, `verification`, `researcher` |
| `gpt-5.6-luna` | OpenAI | Suppressed (`reasoning_effort="none"`) | Suppressed (`reasoning_effort="none"`) | Adheres to `/v1/chat/completions` function tool gateway rules |
| `MiniMax-M3` | MiniMax | Standard execution via Anthropic format | Structured extraction | `Mode.ANTHROPIC_JSON` in `clients.py` |

---

## 3. Empirical Verification Results

Live end-to-end dry runs verified that thinking agents execute reliably:

1. **Anthropic (`claude-haiku-4-5`)**:
   - Executed multi-turn tool calling on NVDA (fetched quote, options sentiment, valuation multiples).
   - Preserved `thinking` blocks across turns and produced structured decision: `NVDA HOLD (conf: 72.0%)`.
2. **Gemini (`gemini-3.5-flash-lite`)**:
   - Executed tool loop with `ThinkingConfig` on AAPL and generated: `AAPL HOLD (conf: 65.0%)` citing elevated P/E multiples (34.1x) and DCF estimates.
3. **DeepSeek (`deepseek-v4-flash`)**:
   - Executed clean API tool calls on MSFT without narration hallucinations, followed by thinking extraction: `MSFT BUY (conf: 62.0%)`.
4. **Live Verification Pipeline**:
   - Evaluated a proposed SPY buy order using live market data tools (`get_price_history`, `get_options_sentiment`, `get_ticker_news`, `audit_financial_valuation`).
   - The verifier detected an extreme Put/Call ratio (4.47), news headwinds (strategist target cuts, oil volatility), and momentum exhaustion, rejecting the trade with high confidence: `status='REJECTED_VERIFICATION', confidence_score=88`.

---

## 4. Pipeline Flow Coverage

Thinking is unified across all autonomous decision and analytical pipelines in the engine:

1. **Daily Predictor (`tasks/daily_predictor.py`)**:
   - Predicts whether the target benchmark (SPY) will close higher or lower relative to the 9:30 AM open.
   - DeepSeek applies `extra_body={"thinking": {"type": "enabled"}}` to deliberate over overnight briefing newsletters, forward calendar catalysts, options derivatives, and macro barometers before emitting directional conviction.
   - Anthropic and Gemini are configured with explicit thinking budgets (`budget_tokens: 2048` and `thinking_budget: 2048`).
2. **Sector Predictor (`tasks/sector_predictor.py`)**:
   - Forecasts top sector, worst sector, and uncorrelated pairs across 7d, 30d, 60d, and 90d forecast horizons.
   - DeepSeek and Gemini apply thinking mode to deliberate over 90-day correlation matrices, asset returns, and high-impact calendar scenarios.
3. **Daily Researcher / Autoresearcher (`autoresearch/researcher.py`)**:
   - Karpathy-style autonomous loop analyzing post-mortem performance reports, verifier audit logs, and prompt blocks.
   - Anthropic (`budget_tokens: 4096`), Gemini (`thinking_budget: 4096`), and DeepSeek use extended thinking to evaluate trading failure modes and propose modular mutations.
4. **Primary Analysis Agents (`analysis.py`)**:
   - Executes multi-turn pull loops (`max_tool_steps = 5`) where models evaluate real-time quotes, technical momentum, and volatility surfaces before extracting final BUY/SELL/HOLD decisions.
5. **Trade Verification Agent (`verification.py`)**:
   - Audits proposed trade decisions against Tier 2 academic papers, valuation DCF models, options Put/Call distributions, and news sentiment with thinking deliberation.

---

## Related

- [[concepts/agents]] — Specialized multi-agent roles and interaction flow
- [[concepts/tool-first-agency]] — Tool-first, agency-driven architecture (Principle 8)
- [[concepts/reasoning]] — The 5 Whys, reasoning frameworks, and mental models
- [[entities/engine]] — Engine architecture and tool-calling infrastructure
