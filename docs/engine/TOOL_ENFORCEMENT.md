# Tool Enforcement & Hallucination Prevention

## Overview

Multi-layer verification system preventing LLM hallucinations related to tool usage and portfolio ownership. Price hallucination is eliminated by design via **pre-injected market data** — the system fetches and injects verified prices into every prompt before the LLM reasons, so the LLM never produces price fields.

## Problem Statement

Three categories of hallucinations observed in production:

1. **Tool Usage**: LLMs claim in text to have called tools without actually emitting a function-call block — "I'll call calculate_buy_quantity for NVDA... The quantity is 83, so I recommend BUY." (no `tool_use` block in the response).
2. **Ownership**: SELL signals for tickers not held in the agent's portfolio.

Price hallucination (category #3 historically) is now prevented by **Approach 3: Pre-Injected Prices** (see below).

## Price Hallucination Prevention: Pre-Injected Market Data

Instead of requiring the LLM to call `get_stock_quote` and transcribe a price into structured fields, the system pre-fetches all relevant prices before analysis and injects them as **VERIFIED MARKET DATA** directly into the prompt. The LLM:

- Receives current prices for held portfolio tickers, `$SYMB` tickers mentioned in news chunks, and major indices (SPY, QQQ, DIA, IWM)
- Never produces `price`, `limit_price`, or `price_source` fields in its structured output
- References the verified prices in its reasoning text
- Trades execute at the current market price at settlement time (server-authoritative execution)

### Why this approach

- **Eliminates the hallucination surface**: The LLM never touches a price number — it only reasons about prices already injected by the system
- **Provider-agnostic**: Works identically across OpenAI, Anthropic, Gemini, and DeepSeek
- **No audit needed**: Nothing to verify because the LLM doesn't produce price values
- **No false positives**: Structured-field audit approaches risk false positives from legitimate price mentions (targets, strike prices, historical prices)

### Staleness safeguard

After JIT price refresh at execution time, the system compares the current market price to the price that was injected into the prompt. If drift exceeds the configured threshold (see `core/config.py`), the trade is rejected as `REJECTED_STALE_QUOTE` — the LLM was reasoning with an outdated reference price.

### Implementation

**Key files:**

| File | Purpose |
|------|---------|
| `core/llm/analysis.py: _extract_tickers_from_chunks()` | Scans news chunks for `$SYMB` patterns, unions with portfolio tickers + major indices |
| `core/llm/prompts.py` | Prompt templates with `{market_data_block}` placeholder, no price field instructions |
| `core/llm/prompt_factory.py` | Injects market data block into analysis and contrarian messages |
| `core/models.py: injected_market_price` | System-set field used for staleness check (not LLM-produced) |
| `main.py` | Staleness check: rejects if JIT price drifts >2% from injected price |

## Layer 1: Pre-Prompt Strengthening

All models receive `CORE_ANALYSIS_SYSTEM_PROMPT` via `PromptFactory` (`apps/engine/core/llm/prompt_factory.py`). This ensures semantic consistency across providers while handling role mapping and instruction stripping adaptively.

Key requirements injected into the prompt:
- Prices are pre-injected as VERIFIED MARKET DATA — use them directly, do not fabricate numbers
- `calculate_buy_quantity` / `calculate_sell_quantity` mandatory for BUY/SELL
- Text claims without function calls = HALLUCINATION = automatic rejection
- Minimum-position-size rule is enforced server-side by the calculation tools
- Do NOT produce `price`, `limit_price`, or `price_source` fields in structured output

Few-shot examples show correct (tool_use block → decision with no price fields) vs incorrect (text-only claim) patterns.

## Layer 2: Prompt Context Enhancement

- **Portfolio Source of Truth**: "CRITICAL: This is the ONLY authoritative list of what you own. SELL signals for unheld tickers will be REJECTED."
- **Held Tickers Quick Reference**: Explicit list (e.g., "You currently hold: NVDA, TSLA")
- **Verified Market Data**: Pre-fetched current prices for relevant tickers injected before the LLM reasons

## Layer 3: Post-Analysis Verification

### History Scanning
After LLM analysis, the engine scans the actual conversation history for real function calls to `calculate_buy_quantity` and `calculate_sell_quantity`. Robust to formatting variances — normalizes whitespace and casing for tickers.

### Ownership Pre-Validation
SELL signals for unheld tickers are caught before reaching the verification layer and converted to HOLD with `REJECTED_OWNERSHIP` reasoning (preserves audit trail).

## Layer 4: Structured Output & Data Isolation

- Deep-copy isolation: `instructor` extraction copies messages so schema injection doesn't pollute audit logs
- Execution authority: The LLM specifies ticker + signal + allocation %; the system computes price, quantity, and limit price server-side at settlement time

## Provider-Specific Fixes

**DeepSeek (Thinking Mode):** Empty content with reasoning_content only → auto-retry with JSON prompt appended. Handler clears reasoning_content from non-tool-call messages. Applied in both the analysis pipeline (`core/llm/analysis.py`) and the verification pipeline (`core/llm/verification.py`) — detection, cleaning, and recovery are identical in both paths.

**Claude:** `max_tokens` raised from the SDK default to prevent mid-tool-call truncation. Current value: `core/llm/handlers/anthropic.py`.

**Gemini:** Multiple function calls in single response → `List[Model]` pattern in contrarian analysis, `Mode.GENAI_TOOLS` for instructor.

## Key Files

| File | Purpose |
|------|---------|
| `core/llm/prompt_factory.py` | Centralized prompt assembly with market data injection |
| `core/llm/prompts.py` | Static prompt templates (no price field instructions) |
| `core/llm/analysis.py` | Pre-fetch ticker extraction, history scanning for quantity tools |
| `core/llm/verification.py` | Verifier intelligence profiles |
| `core/models.py` | `injected_market_price` field for staleness checking |
| `main.py` | Staleness guard at execution time |
| `core/llm/handlers/deepseek.py` | Thinking mode + empty content handling |
| `core/llm/handlers/anthropic.py` | Whitespace filtering, max_tokens |
| `core/llm/handlers/gemini.py` | Multi-function-call handling |
