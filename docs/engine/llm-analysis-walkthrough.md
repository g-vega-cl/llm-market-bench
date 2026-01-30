# Walkthrough: Step 5 - Parallel LLM Analysis

The Parallel LLM Analysis engine orchestrates the evaluation of financial news using four independent LLMs (OpenAI, Claude, Gemini, and DeepSeek) to generate structured trading signals.

## 1. Technical Architecture

The engine uses **Instructor** in combination with **Pydantic** to enforce a strict JSON schema for all LLM outputs. This ensures that the downstream execution engine receives predictable, validated data.

### **Provider SDKs**
To ensure maximum feature coverage and performance, the system uses the official native SDKs for each provider:

| Provider | SDK / Client | Model Default |
| --- | --- | --- |
| **OpenAI** | `openai` | `gpt-5-mini` |
| **Anthropic** | `anthropic` | `claude-haiku-4-5` |
| **Gemini** | `google-genai` | `gemini-3-flash-preview` |
| **DeepSeek** | `openai` (official) | `deepseek-reasoner` |

### **Active Tool Calling**
Models now actively call multiple tools to verify market data and context *before* committing to a trade:
- **`get_stock_quote`**: Verifies ticker existence, real-time pricing, and liquidity.
- **`get_price_history`**: (NEW) Fetches recent historical prices to determine if news is "priced in".
- **`get_position_pnl`**: (NEW) Fetches current unrealized P&L and cost basis for existing positions to ensure trading winners and selling losers slowly.

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

Every LLM returns two types of objects matching these schemas:

### **Trading Decision Objects**

```python
class DecisionObject(BaseModel):
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: int  # Range: 0-100
    reasoning: str   # Qualitative explanation
    ticker: str      # Stock Symbol
    catalyst_type: Literal["MACRO", "EARNINGS", "M_A", "PRODUCT", "REGULATORY", "OTHER"]
    catalyst_duration: Literal["INTRADAY", "SHORT_TERM", "LONG_TERM"]
    source_id: str   # Link to the raw news chunk
    price: float | None  # Stock price (optional, for validation)
    allocation_percentage: int | None  # % of buying power to allocate (0-100)
```

### **Macro Event Objects**

Models also identify broader market signals that don't trigger a specific ticker trade but inform the overall market regime:

```python
class MacroEvent(BaseModel):
    event_name: str
    impact: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    reasoning: str
    is_ongoing: bool  # Whether the event is still unfolding (e.g. "Trade War Escalating")
    is_future_catalyst: bool # Whether this is a precursor for a future move
    historical_parallel: str | None # Comparison to past events (e.g. "1970s stagflation")
    future_date: str | None # Extracted future timeframe
```

## 4. Parallel Orchestration (Consolidated Mode)

To minimize latency and costs, the system uses a **Batch-Parallel** approach. Instead of querying models for every individual news snippet, all chunks are bundled into a single batch per provider.

1.  **Ingestion**: News chunks are fetched from Gmail and cleaned via the LLM De-advertisement pass (Gemini Flash).
2.  **Filtering**: Chunks are validated to ensure they contain both `source_id` and `content`. Malformed chunks are skipped to prevent pipeline errors.
3.  **RAG Batching**: Gemini embeddings are generated for ALL valid chunks in a single batch call.
4.  **Dispatch & Tool Loop**: Each LLM is called in a sequence designed to allow multiple "reasoning and verification" steps.
    *   **Phase A**: Model reasoning on news chunks.
    *   **Phase B**: Tool call triggered for ticker verification.
    *   **Phase C**: Tool result returned (via `MarketDataManager`).
    *   **Phase D**: Final structured decision generated.
5.  **Validation**: `Instructor` extracts and validates the model's list of decisions against the Pydantic schema.
6.  **Aggregation**: Validated `DecisionObject` outputs are saved for the Consensus phase.

## 5. Sophisticated Trading Logic

To move beyond simple "news-chasing," the system now enforces a multi-step qualitative verification process in the system prompt. Before recommending a trade, agents are instructed to leverage their tools to answer:

1.  **Is this news already priced in?** (Using `get_price_history`)
2.  **If I already own this stock, has this trade been profitable?** (Using `get_position_pnl`)
3.  **What is the expected timeline for this catalyst to materialize?**
4.  **What are the primary risks or counter-arguments to this trade?**
5.  **How does this stock correlate with my existing portfolio?**

This logic ensures that trades are based on predicted future movements rather than reacting to yesterday's news.

## 6. Verification

The logic is verified using a comprehensive test suite:
- **Core Logic**: `pytest apps/engine/tests/test_analysis_logic.py`
- **Tool Calling**: `pytest apps/engine/tests/test_llm_tools.py`
- **Scope**: Validates schema enforcement, parallel task orchestration, and tool-result handling.

## 6. How to Run

To execute the pipeline (Ingestion -> Snapshot -> Analysis):

```bash
python apps/engine/main.py ingest
```

The engine will log the generated decisions from each model as they complete.

## 7. Robustness & Fault Tolerance

To ensure the pipeline continues even if individual models fail:

- **Tool Execution Wrapping**: Tool calls (`get_stock_quote`, etc.) are wrapped in `try/except` blocks. If a model tries to call a tool with invalid arguments or the tool service fails, the engine logs a warning and proceeds with a "basic analysis" fallback rather than crashing the entire batch.
- **Optional Schema Fields**: Newer metadata fields like `is_ongoing` or `historical_parallel` are marked as optional. If a model fails to extract them, the system defaults to `None` or `False` rather than rejecting the entire event.
