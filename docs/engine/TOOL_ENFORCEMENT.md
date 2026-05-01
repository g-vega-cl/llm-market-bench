# Tool Enforcement & Hallucination Prevention

## Overview

Four-layer verification system preventing LLM hallucinations related to tool usage, price validation, and portfolio ownership.

## Problem Statement

Three categories of hallucinations observed in production:
1. **Tool Usage**: LLMs claim in text to have called tools without actually emitting a function-call block — "I'll call get_stock_quote for NVDA... The price is $120.50" (no `tool_use` block in the response).
2. **Price**: LLMs fabricate prices that diverge from the live market beyond the configured deviation band.
3. **Ownership**: SELL signals for tickers not held in the agent's portfolio.

## Layer 1: Pre-Prompt Strengthening

All models receive `CORE_ANALYSIS_SYSTEM_PROMPT` via `PromptFactory` (`apps/engine/core/llm/prompt_factory.py`). This ensures semantic consistency across providers while handling role mapping and instruction stripping adaptively.

Key requirements injected into the prompt:
- `get_stock_quote` must be called before ANY trade recommendation
- `calculate_buy_quantity` / `calculate_sell_quantity` mandatory for BUY/SELL
- Text claims without function calls = HALLUCINATION = automatic rejection
- Minimum-position-size rule is enforced server-side by the calculation tools

Few-shot examples show correct (tool_use block → price → decision) vs incorrect (text-only claim) patterns.

## Layer 2: Prompt Context Enhancement

- **Portfolio Source of Truth**: "CRITICAL: This is the ONLY authoritative list of what you own. SELL signals for unheld tickers will be REJECTED."
- **Held Tickers Quick Reference**: Explicit list (e.g., "You currently hold: NVDA, TSLA")
- **Price Validation**: "Always use the price returned by get_stock_quote. DO NOT hallucinate prices."

## Layer 3: Post-Analysis Verification

### History Scanning
After LLM analysis, the engine scans the actual conversation history for real function calls. Robust to formatting variances — normalizes whitespace and casing for tickers.

### Confidence Penalty
Decisions without verified tool calls have their confidence reduced by a fixed factor (constant in `core/llm/analysis.py`).

### Ownership Pre-Validation
SELL signals for unheld tickers are caught before reaching the verification layer and converted to HOLD with `REJECTED_OWNERSHIP` reasoning (preserves audit trail).

## Layer 4: Structured Output & Data Isolation

- `DecisionObject.price_source` field declares tool provenance ("get_stock_quote tool call" or "hallucinated")
- Deep-copy isolation: `instructor` extraction copies messages so schema injection doesn't pollute audit logs

## Provider-Specific Fixes

**DeepSeek (Thinking Mode):** Empty content with reasoning_content only → auto-retry with JSON prompt appended. Handler clears reasoning_content from non-tool-call messages.

**Claude:** `max_tokens` raised from the SDK default to prevent mid-tool-call truncation. Current value: `core/llm/handlers/anthropic.py`.

**Gemini:** Multiple function calls in single response → `List[Model]` pattern in contrarian analysis, `Mode.GENAI_TOOLS` for instructor.

## Key Files

| File | Purpose |
|------|---------|
| `core/llm/prompt_factory.py` | Centralized prompt assembly |
| `core/llm/prompts.py` | Static prompt templates |
| `core/llm/analysis.py` | Integrated verification + history scanning |
| `core/llm/verification.py` | Verifier intelligence profiles |
| `core/llm/handlers/deepseek.py` | Thinking mode + empty content handling |
| `core/llm/handlers/anthropic.py` | Whitepsace filtering, max_tokens |
| `core/llm/handlers/gemini.py` | Multi-function-call handling |
