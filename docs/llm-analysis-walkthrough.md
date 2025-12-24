# Walkthrough: Step 5 - Parallel LLM Analysis

The Parallel LLM Analysis engine orchestrates the evaluation of financial news using four independent LLMs (OpenAI, Claude, Gemini, and DeepSeek) to generate structured trading signals.

## 1. Technical Architecture

The engine uses **Instructor** in combination with **Pydantic** to enforce a strict JSON schema for all LLM outputs. This ensures that the downstream execution engine receives predictable, validated data.

### **Provider SDKs**
To ensure maximum feature coverage and performance, the system uses the official native SDKs for each provider:

| Provider | SDK / Client | Model Default |
| --- | --- | --- |
| **OpenAI** | `openai` | `gpt-4-turbo-preview` |
| **Anthropic** | `anthropic` | `claude-3-5-sonnet-20240620` |
| **Gemini** | `google-generativeai` | `gemini-1.5-pro` |
| **DeepSeek** | `openai` (official) | `deepseek-chat` |

## 2. Configuration & Model Selection

Model versions can be configured via environment variables in `apps/engine/.env`. This allows for easy testing of newer models (e.g., `gemini-2.5-flash` or `gpt-5-mini`) without code changes.

```bash
# Configuration Example
OPENAI_MODEL="gpt-5-mini"
ANTHROPIC_MODEL="claude-haiku-4-5"
GEMINI_MODEL="gemini-3-flash-preview"
DEEPSEEK_MODEL="deepseek-reasoner"
```

## 3. The Decision Data Model

Every LLM must return a `DecisionObject` matching this schema:

```python
class DecisionObject(BaseModel):
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: int  # Range: 0-100
    reasoning: str   # Qualitative explanation
    ticker: str      # Stock Symbol
    source_id: str   # Link to the raw news chunk
```

## 4. Parallel Orchestration

The system uses `asyncio.gather` to query all enabled models concurrently for every newsletter chunk.

1.  **Ingestion**: News chunks are fetched from Gmail.
2.  **Dispatch**: Each chunk is sent to all 4 LLMs in parallel.
3.  **Validation**: Pydantic validates the response; malformed outputs are caught.
4.  **Aggregation**: Valid decisions are collected for the next phase (Consensus).

## 5. Verification

The logic is verified using a mocked test suite:
- **Command**: `pytest apps/engine/tests/test_analysis_logic.py`
- **Scope**: Validates schema enforcement, confidence range checks, and parallel task orchestration.

## 6. How to Run

To execute the pipeline (Ingestion -> Snapshot -> Analysis):

```bash
python apps/engine/main.py ingest
```

The engine will log the generated decisions from each model as they complete.
