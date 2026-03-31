# Agent-Specific Semantic Overlap

## Overview

This document describes the **Agent-Specific Semantic Overlap** feature, which ensures that the semantic redundancy check only applies within the same agent's portfolio, preventing false rejections when different agents independently identify the same trading opportunities.

## Problem Statement

Previously, the semantic overlap verification was comparing trades across ALL agents. This caused incorrect rejections when:

- **Agent A** (e.g., CLAUDE) made a trade on NKE with reasoning about earnings
- **Agent B** (e.g., HAIKU) was blocked from making the same NKE trade, even though it has a separate portfolio and decision context

This violated the multi-agent architecture principle where each agent should be able to act independently on market opportunities.

## Solution

The semantic overlap check now filters by `model_name` (agent identifier), ensuring that:

1. **Agent Isolation**: Each agent's trades are only compared against its own recent trades
2. **Independent Decision-Making**: Different agents can trade the same ticker based on similar reasoning
3. **Overtrading Prevention**: Individual agents are still prevented from making redundant trades

## Technical Implementation

### Changes Made

#### 1. `apps/engine/memory/store.py`

**`find_similar_decision()` function:**
```python
def find_similar_decision(
    ticker: str,
    content: str,
    threshold: float = 0.90,
    hours: int = 24,
    embedding: list[float] = None,
    model_name: Optional[str] = None  # NEW parameter
) -> Optional[dict]:
```

**`find_similar_vector()` function:**
```python
def find_similar_vector(
    table_name: str,
    content: str,
    threshold: float = 0.90,
    hours: int = 24,
    embedding: list[float] = None,
    status_filter: Optional[str] = None,
    ticker_filter: Optional[str] = None,
    model_name_filter: Optional[str] = None  # NEW parameter
) -> Optional[Any]:
    # ...
    if model_name_filter:
        query = query.filter("model_name", "eq", model_name_filter)
```

#### 2. `apps/engine/execution/validation.py`

**`validate_semantic_overlap()` function:**
```python
async def validate_semantic_overlap(
    ticker: str,
    reasoning: str,
    model_name: Optional[str] = None,  # NEW parameter
    threshold: float = 0.90
) -> Optional[str]:
    similar = find_similar_decision(
        ticker=ticker,
        content=reasoning,
        threshold=threshold,
        hours=24,
        model_name=model_name  # Pass agent identifier
    )
```

#### 3. `apps/engine/main.py`

**Pipeline integration:**
```python
# Semantic overlap check with agent isolation
overlap_reason = await validate_semantic_overlap(
    d.ticker,
    d.reasoning,
    model_name=d.model_name  # Pass the agent's model name
)
```

### Database Schema

The `decisions` table already includes the `model_name` column:

```sql
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    signal TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    reasoning TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,  -- Used for agent filtering
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    embedding VECTOR(768)
);
```

## Example Scenarios

### Scenario 1: Same Agent Redundancy (Blocked)

**CLAUDE's first trade:**
- Ticker: NKE
- Reasoning: "Nike earnings TOMORROW. Stock at 8-year lows, down 20% from highs."
- Status: EXECUTED

**CLAUDE's second trade (5 minutes later):**
- Ticker: NKE
- Reasoning: "Nike earnings coming up, stock looks cheap at current levels."
- Status: **REJECTED_REDUNDANCY** ✅ (similarity > 0.90)

### Scenario 2: Different Agent Independence (Allowed)

**CLAUDE's trade:**
- Ticker: NKE
- Reasoning: "Nike earnings TOMORROW. Stock at 8-year lows."
- Status: EXECUTED

**HAIKU's trade (same pipeline run):**
- Ticker: NKE
- Reasoning: "Nike earnings tomorrow, good entry point for value investors."
- Status: **VALIDATED** ✅ (different agent, no overlap check)

## Testing

### Unit Tests

Located in `apps/engine/tests/test_recent_trades_context.py`:

1. **`test_semantic_overlap_detection`**: Verifies basic similarity detection
2. **`test_semantic_overlap_agent_isolation`**: Verifies agent-specific filtering

Run tests:
```bash
cd apps/engine
source venv/bin/activate
python -m pytest tests/test_recent_trades_context.py -v
```

### Expected Output
```
test_semantic_overlap_detection PASSED
test_semantic_overlap_agent_isolation PASSED
```

## Configuration

The semantic overlap check uses the following parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threshold` | `0.90` | Cosine similarity threshold (0.0-1.0) |
| `hours` | `24` | Lookback window for recent trades |
| `model_name` | `None` | Agent identifier for filtering (NEW) |

## Impact

### Before
- ❌ HAIKU blocked from trading NKE because CLAUDE had a similar trade
- ❌ Reduced diversification in AI consensus
- ❌ False positives in redundancy detection

### After
- ✅ Each agent can independently trade the same ticker
- ✅ Maintains overtrading prevention per agent
- ✅ Preserves multi-agent architecture integrity
- ✅ Better consensus signal when multiple agents agree

## Related Documentation

- [Pre-Market Validation](./pre-market-validation.md) - Guardrail I: Semantic Redundancy
- [Step 15: Long-term Memory Embedding](./step-15-long-term-memory-embedding.md)
- [Overview](../Overview.md) - Trade Settlement & Ledgering

## Migration Notes

No database migrations required. The `model_name` column already exists in the `decisions` table.

### Backward Compatibility

The `model_name` parameter is **optional** (defaults to `None`). If not provided, the behavior falls back to the original cross-agent checking (for backward compatibility during transition).

**Recommendation**: Always pass `model_name` in production code to ensure agent-specific filtering.
