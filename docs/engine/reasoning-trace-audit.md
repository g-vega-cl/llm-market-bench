# Research Guide: Reasoning Trace Audit Trail

The Reasoning Trace system captures every LLM interaction in the pipeline, providing a granular look into the "Thinking Process" of the AI agents.

## Why it Exists
While the `decisions` table stores the final signal and reasoning, the `llm_reasoning_logs` table preserves the *raw* conversation history. This includes:
- **System Prompts**: The instructions given to the model.
- **Intermediate Tool Calls**: Fetching quotes, price history, or volatility metrics.
- **Tool Results**: The raw data returned by market providers.
- **Thought Traces**: Internal chain-of-thought (for models like Gemini and DeepSeek).

## Schema: `llm_reasoning_logs`

| Column | Type | Description |
| --- | --- | --- |
| `task_type` | TEXT | `INGESTION`, `VERIFICATION`, `CONSENSUS`, etc. |
| `model_name` | TEXT | e.g., `openai/gpt-4o`, `anthropic/claude-3-5-sonnet` |
| `prompt` | JSONB | Array of all messages in the conversation. |
| `response` | JSONB | The final structured output (e.g., `DecisionObject`). |
| `metadata` | JSONB | Tickers, source IDs, and contextual flags. |

## Research Examples

### 1. View Verifier Tool Usage
To see how often the Skeptical Verifier uses the `get_volatility_metrics` tool before making a decision:

```sql
SELECT 
  metadata->>'ticker' as ticker,
  prompt
FROM llm_reasoning_logs
WHERE task_type = 'VERIFICATION'
  AND prompt::text LIKE '%get_volatility_metrics%';
```

### 2. Analyze "Priced In" Logic
To compare the initial agent analysis with the verifier's second-step logic:

```sql
SELECT 
  metadata->>'ticker' as ticker,
  task_type,
  response->>'reasoning' as reasoning
FROM llm_reasoning_logs
WHERE metadata->>'ticker' = 'NVDA'
ORDER BY created_at ASC;
```

### 3. Trace Hallucinations
If a model generates a hallucinated ticker, you can inspect the `prompt` to see if the newsletter content itself was ambiguous or if the model failed during retrieval.

## Implementation Details
Traces are captured asynchronously using the `core.llm.logger.log_reasoning_trace` utility. This ensures that logging overhead never crashes the main trading pipeline.
