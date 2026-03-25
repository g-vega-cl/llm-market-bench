# Tool Enforcement & Hallucination Prevention

**Last Updated**: 2026-03-24 (Updated 2026-03-24 PM: DeepSeek, Xiaomi, Claude, Gemini fixes)

## Overview

This document describes the multi-layer verification system implemented to prevent LLM hallucinations related to tool usage, price validation, and portfolio ownership.

## Problem Statement

Analysis of pipeline logs revealed critical categories of hallucinations and errors:

1. **Tool Usage Hallucinations**: LLMs claiming in text to have called tools without actual function calling
   - Example: "I'll call get_stock_quote for NVDA... The price is $120.50" (no tool_use block output)
   - Impact: 3+ rejected trades per run for Claude models

2. **Price Hallucinations**: LLMs estimating or fabricating prices without tool verification
   - Example: AI price $170.00 vs Market price $91.20 (86% deviation for PAYX)
   - Impact: 4+ rejected trades per run due to >5% deviation guardrails

3. **Ownership Hallucinations**: LLMs recommending SELL for tickers not in portfolio
   - Example: SELL signals for MU, LMT, F when agent held none of these tickers
   - Impact: 3+ rejected trades per run

4. **Provider-Specific Errors** (2026-03-24 PM):
   - **DeepSeek & Xiaomi**: Empty content with thinking mode enabled
   - **Claude**: Max tokens limit (16K output cutoff)
   - **Gemini**: Multiple function calls in single response

## Solution Architecture

The enforcement system operates at **four layers**:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Pre-Prompt Strengthening                           │
│ - Enhanced system prompts (Claude-specific)                 │
│ - Few-shot examples (correct vs incorrect)                  │
│ - Bold warnings about consequences                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Prompt Context Enhancement                         │
│ - Portfolio "Source of Truth" section                       │
│ - Held tickers quick reference list                         │
│ - Price validation requirements                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Post-Analysis Verification                         │
│ - History scanning for actual tool calls                    │
│ - Ownership pre-validation                                  │
│ - Confidence scoring penalties                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Structured Output Enforcement                      │
│ - price_source field declaration                            │
│ - Audit trail preservation                                  │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: Pre-Prompt Strengthening

### Claude-Specific System Prompt

Claude models receive an enhanced system prompt (`CLAUDE_ANALYSIS_SYSTEM_PROMPT`) with explicit requirements:

```python
CLAUDE_ANALYSIS_SYSTEM_PROMPT = """
=== CRITICAL TOOL USAGE REQUIREMENTS ===
1. BEFORE recommending ANY trade (BUY or SELL), you MUST call get_stock_quote(ticker) via function calling.
2. For SELL decisions, you MUST call a sell percentage tool (e.g., sell_50_percent) to calculate exact share quantity.
3. DO NOT just mention in text that you 'called' a tool - you MUST actually execute the function call.
4. Your trade will be AUTOMATICALLY REJECTED if the tool call is not found in your conversation history.
5. Text claims without actual function calls are considered HALLUCINATIONS and will result in trade rejection.

TOOL CALL FORMAT (Anthropic):
When you need to verify a stock, output a tool_use block like:
{"type": "tool_use", "id": "call_123", "name": "get_stock_quote", "input": {"ticker": "AAPL"}}

This is a HARD REQUIREMENT. No exceptions.
"""
```

### Few-Shot Examples

The user prompt includes correct vs incorrect examples:

```
### TOOL USAGE EXAMPLES (FEW-SHOT):

✅ CORRECT - Tool Call Before Trade Recommendation:
[Assistant outputs tool_use block]
{"type": "tool_use", "id": "call_abc123", "name": "get_stock_quote", "input": {"ticker": "NVDA"}}

[Tool returns: Ticker: NVDA, Current Price: $120.50, Market Cap: $2.97T]

[Assistant then outputs decision]
{
  "decisions": [{
    "ticker": "NVDA",
    "signal": "BUY",
    "price": 120.50,
    "reasoning": "After verifying the current price of $120.50 via get_stock_quote..."
  }]
}

❌ INCORRECT - Text Claim Without Actual Tool Call (WILL BE REJECTED):
"I'll call get_stock_quote for NVDA... The price is $120.50, so I recommend BUY."
[NO tool_use block was output - this is a HALLUCINATION]
```

## Layer 2: Prompt Context Enhancement

### Portfolio Source of Truth

The prompt now includes a clearly marked portfolio section:

```
=== YOUR CURRENT PORTFOLIO (SOURCE OF TRUTH) ===
**CRITICAL: This is the ONLY authoritative list of what you currently own.**
**Before recommending ANY SELL, verify the ticker appears in your positions below.**
**If a ticker is NOT listed, you DO NOT own it - SELL signals will be REJECTED.**

Cash Balance: $8,234.50
Total Equity: $12,456.78
Buying Power: $6,543.21

Current Positions:
- NVDA: 10 shares @ $115.00 (Curr: $120.50, P/L: $55.00 / 4.8%)
- TSLA: 5 shares @ $235.00 (Curr: $240.50, P/L: $27.50 / 2.3%)

=== HELD TICKERS QUICK REFERENCE ===
**You currently hold these tickers (for SELL validation): NVDA, TSLA**
**Any ticker NOT in this list CANNOT be sold.**
```

### Price Validation Requirements

```
=== PRICE VALIDATION REQUIREMENT ===
**CRITICAL: Always use the price returned by get_stock_quote for your decision.**
**DO NOT hallucinate or estimate prices - your trade will be rejected if the price deviates >5% from market.**
**The get_stock_quote tool MUST be called BEFORE your final decision - not after, not in text only.**
```

## Layer 3: Post-Analysis Verification

### History Scanning

After LLM analysis completes, the engine scans the actual conversation history:

```python
def _scan_history_for_tools(messages: list, ticker: str) -> dict:
    """Scans message history for tool calls related to a specific ticker.
    
    Returns:
        dict: {
            "quote_found": bool,      # get_stock_quote was called
            "sell_tool_found": bool   # sell_X_percent was called
        }
    """
    # Handles multiple provider formats:
    # - OpenAI/DeepSeek/Xiaomi: tool_calls array
    # - Anthropic: content list with tool_use blocks
    # - Gemini: parts array with function_call
```

**Key Feature**: Only counts ACTUAL function calls, not text claims.

### Confidence Scoring Penalty

Decisions without verified tool calls receive automatic confidence reduction:

```python
if not results["quote_found"]:
    logger.warning(
        "[%s/%s] HARD ENFORCEMENT: Agent recommended trade for %s "
        "without 'get_stock_quote' verification.",
        provider, model_name, decision.ticker
    )
    # Reduce confidence by 50%
    decision.confidence = int(decision.confidence * 0.5)
```

### Ownership Pre-Validation

Before decisions are returned, SELL signals are validated against held tickers:

```python
held_tickers = _extract_held_tickers(portfolio_context)
validated_decisions = []

for decision in final_resp.decisions:
    if decision.signal == "SELL" and decision.ticker.upper() not in held_tickers:
        logger.warning(
            "[%s/%s] PRE-ANALYSIS VALIDATION: SELL signal for %s rejected - "
            "ticker not in portfolio. Held: %s",
            provider, model_name, decision.ticker, held_tickers
        )
        # Convert to HOLD to preserve audit trail
        decision.signal = "HOLD"
        decision.reasoning = (
            f"REJECTED_OWNERSHIP: Attempted to sell {decision.ticker} "
            f"but ticker is not held. Original reasoning: {decision.reasoning[:200]}"
        )
    validated_decisions.append(decision)
```

**Design Decision**: Convert to HOLD instead of discarding to maintain complete audit trail.

## Layer 4: Structured Output Enforcement

### Price Source Declaration

The `DecisionObject` model now includes a `price_source` field:

```python
class DecisionObject(BaseModel):
    # ... other fields ...
    price_source: str | None = Field(
        None,
        description="REQUIRED: Must state 'get_stock_quote tool call' if price "
                    "was verified via tool, or 'hallucinated' if not."
    )
```

**Prompt Requirement**:
```
PRICE SOURCE REQUIREMENT:
- You MUST set 'price_source' to "get_stock_quote tool call" if you called the tool.
- If you did NOT call get_stock_quote, set 'price_source' to "hallucinated" (your trade will be rejected).
- This is a HARD REQUIREMENT for all BUY and SELL decisions.
```

## Implementation Files

| File | Changes |
|------|---------|
| `core/llm/prompts.py` | Added `CLAUDE_ANALYSIS_SYSTEM_PROMPT`, few-shot examples, enhanced portfolio/price sections |
| `core/llm/analysis.py` | Added `_extract_held_tickers()`, history scanning, confidence penalties, ownership validation, DeepSeek message preparation |
| `core/models.py` | Added `price_source` field to `DecisionObject` |
| `core/llm/handlers/deepseek.py` | Added `prepare_messages_for_instructor()`, `has_valid_content()` for thinking mode support |
| `core/llm/handlers/xiaomi.py` [NEW] | Added `prepare_messages_for_instructor()`, `has_valid_content()` for thinking mode support |
| `core/llm/handlers/anthropic.py` | Increased max_tokens from 8000 to 32000 |
| `core/llm/handlers/gemini.py` | Enhanced multi-function-call handling |
| `core/llm/clients.py` | Added `mode=instructor.Mode.GENAI_TOOLS` for Gemini |
| `analysis/contrarian.py` | Changed to `List[ContrarianAgentResponse]` for Gemini multi-block support |

## Provider-Specific Fixes (2026-03-24 PM)

### DeepSeek & Xiaomi: Empty Content with Thinking Mode

**Problem**: DeepSeek with thinking mode enabled returns `reasoning_content` but leaves `content` empty or whitespace-only, causing Instructor JSON extraction to fail.

**Error**:
```
Invalid JSON: EOF while parsing a value at line 1 column 47
```

**Solution** (`core/llm/handlers/deepseek.py` & `core/llm/handlers/xiaomi.py`):
1. Added `prepare_messages_for_instructor()` function:
   - Clears `reasoning_content` from messages without tool calls
   - Ensures content is not just whitespace
2. Added `has_valid_content()` function to detect empty responses
3. In `analysis.py`: Auto-appends JSON request prompt if content is empty:
   ```python
   messages.append({
       "role": "user",
       "content": "Output ONLY a valid JSON object with 'decisions' and 'macro_events' arrays..."
   })
   ```

---

### Claude: Max Tokens Limit

**Problem**: Claude Haiku 4.5 was hitting the 8000 token output limit, truncating responses mid-tool-call.

**Error**:
```
stop_reason='max_tokens', output_tokens=16000
```

**Solution** (`core/llm/handlers/anthropic.py` & `core/llm/analysis.py`):
- Increased `max_tokens` from 8000 → 32000 in both:
  - Tool execution loop (handlers/anthropic.py line 82)
  - Final Instructor extraction (analysis.py line 124)
- 32000 provides headroom while staying under Claude's 64K limit

---

### Gemini: Multiple Function Calls

**Problem**: Gemini returns multiple function calls in separate parts within a single response, causing Instructor to fail.

**Error**:
```
Instructor does not support multiple function calls, use List[Model] instead
```

**Solution** (Multiple files):

1. **Contrarian Analysis** (`analysis/contrarian.py`):
   - Changed `response_model=ContrarianAgentResponse` → `response_model=List[ContrarianAgentResponse]`
   - Updated aggregation to iterate through list of responses

2. **Gemini Client** (`core/llm/clients.py`):
   - Added `mode=instructor.Mode.GENAI_TOOLS` to `instructor.from_genai()`
   - This mode properly handles Gemini's function calling patterns
   - Note: `Mode.MISTRAL_TOOLS` is invalid for Gemini; valid modes are `GENAI_STRUCTURED_OUTPUTS` and `GENAI_TOOLS`

3. **Gemini Handler** (`core/llm/handlers/gemini.py`):
   - Enhanced to count and execute all function calls in a response
   - Ensures all tool calls are processed before breaking the loop

---

## Expected Impact

Based on log analysis from 2026-03-24 runs:

| Issue | Before | Expected After |
|-------|--------|----------------|
| Claude tool hallucinations | 3+ rejected trades/run | Eliminated |
| Ownership errors (MU, LMT, F) | 3 rejected trades/run | Caught pre-analysis |
| Price hallucinations (86% deviation) | 4+ rejected trades/run | Reduced via confidence penalties |
| DeepSeek empty content errors | Pipeline failures | Auto-retry with JSON prompt |
| Claude max_tokens truncation | 16K output cutoff | 32K headroom |
| Gemini / Xiaomi multi-call errors | Pipeline failures | List[Model] handling |
| Audit trail completeness | Partial | All rejections preserved |

## Testing

All enforcement logic is covered by existing test suite:

```bash
# Tool enforcement tests
python -m pytest tests/test_tool_enforcement.py -v

# Analysis logic tests
python -m pytest tests/test_analysis_logic.py -v

# Tool calling tests
python -m pytest tests/test_llm_tools.py tests/test_gemini_tools.py -v
```

**Test Coverage**:
- `test_scan_history_openai_format`: Verifies OpenAI tool call detection
- `test_scan_history_anthropic_format`: Verifies Anthropic tool call detection
- `test_scan_history_gemini_format`: Verifies Gemini tool call detection
- `test_analyze_with_provider_hard_enforcement`: Verifies sell_tool_called flag updates
- `test_analyze_with_provider_government_enforcement`: Verifies government incentive enforcement

## Future Enhancements

Potential improvements for future iterations:

1. **Real-Time Tool Interception**: Force tool calls before allowing trade recommendations (not just post-hoc verification)
2. **Multi-Ticker Validation**: Batch verify all tickers in a single history scan
3. **Confidence Threshold Routing**: Auto-reject decisions with confidence < 50 after penalty
4. **Provider-Specific Penalties**: Track hallucination rates per provider/model for routing optimization
