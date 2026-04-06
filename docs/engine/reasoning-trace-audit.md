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

## Web UI: Research Dashboard
A premium audit dashboard is available at `/reasoning` for visual exploration of these traces.

### Features
- **Categorization**: Filter traces by `INGESTION`, `VERIFICATION`, or `CONSENSUS`.
- **Human-Friendly Formatting**: Structured responses are automatically parsed into a tabbed interface, replacing large JSON blocks with readable cards and grids.
- **Cognitive Flow**: A color-coded view of the conversation history. For long histories, roles are grouped into tabs (System, User, Assistant, Tool) for focused auditing.
- **Deep Content Parsing**: Automatically extracts and pretty-prints JSON strings found within assistant messages.
- **Rich Visualization**:
  - **Tool Calls**: Clearly labeled blocks showing function names and arguments.
  - **Internal Thoughts**: Highlights "hidden" model reasoning (e.g., Gemini's `thought` parts).
  - **Decision Cards**: Trading signals and catalyst metadata displayed in high-contrast grids.
- **Fallback & Export**: A "RAW" tab allows for instant JSON inspection and one-click clipboard copying.

## Audit Findings: Prompt Size Discrepancy (Instructor Injection)

During an audit of the `llm_reasoning_logs` table, a significant discrepancy in system prompt size was observed between providers (e.g., DeepSeek vs. Gemini).

### The Root Cause
The difference is structural and related to how the `instructor` library handles Pydantic schema validation:

1.  **DeepSeek/OpenAI (JSON Mode)**: When using `instructor.Mode.JSON` or standard tools, the library generates a massive JSON Schema string from your Pydantic models. To guide the model, Instructor **appends this schema directly to the system message content**. Because the message list is mutable in Python, this mutation happened **in-place**.
2.  **Gemini (GENAI_TOOLS Mode)**: Google's SDK natively accepts schemas via a `response_schema` parameter in the API config. Instructor does not need to inject text into the prompt, so the system instruction remains clean.

### The Fix: Deep-Copy Data Isolation
To ensure that all reasoning logs perfectly reflect the authored prompts (without artificial Pydantic bloat), the engine now implements **Data Isolation Guardrails**.

Whenever a message history is passed to an Instructor `create()` call, it is wrapped in `copy.deepcopy()`. This ensures that any in-place mutations made by the library for API compliance are isolated from the original message history used for logging and audit trails.

```python
# Implementation in analysis.py / verification.py
create_args = {
    "messages": copy.deepcopy(messages),
    ...
}
```

This ensures that tracers and the `/reasoning` dashboard remain clean, comparable, and human-readable across all LLM providers.

## Implementation Details
Traces are captured asynchronously using the `core.llm.logger.log_reasoning_trace` utility. This ensures that logging overhead never crashes the main trading pipeline.

