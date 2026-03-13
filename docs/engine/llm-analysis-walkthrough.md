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
| **Contrarian Agent** | `google-genai` | `gemini-3-flash-preview` |
| **Manager Agent** | `google-genai` | `gemini-3-flash-preview` |

### **Active Tool Calling**
Models (**OpenAI, Anthropic, Gemini**) now actively call multiple tools to verify market data and context *before* committing to a trade:
- **`get_stock_quote`**: Verifies ticker existence, real-time pricing, and liquidity.
- **`get_price_history`**: Fetches recent historical prices to determine if news is "priced in".
- **`get_position_pnl`**: Fetches current unrealized P&L and cost basis for existing positions.
- **`sell_10_percent`, `sell_25_percent`, `sell_33_percent`, `sell_50_percent`, `sell_75_percent`, `sell_100_percent`**: Calculates exact share quantities for partial or full exits of existing positions. **Using these tools is now MANDATORY for any SELL decision.**

### **Handler Architecture**
To improve code maintainability and adhere to Google's Python Style Guide, the tool execution logic has been refactored into provider-specific handlers:

- **`apps/engine/core/llm/handlers/base.py`**: Common tool execution dispatcher.
- **`apps/engine/core/llm/handlers/openai.py`**: Handles OpenAI and DeepSeek tool loops.
- **`apps/engine/core/llm/handlers/anthropic.py`**: Handles Anthropic's specific message formats.
- **`apps/engine/core/llm/handlers/gemini.py`**: Handles Gemini's complex content mapping and tool execution.

This separation ensures that each provider's unique API requirements are isolated, making the codebase easier to test and extend.

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
    catalyst_type: Literal["MACRO", "EARNINGS", "M_A", "PRODUCT", "REGULATORY", "EVENT", "INNOVATION", "TECHNICAL", "UNCROWDED_TRADE", "OTHER"]
    catalyst_duration: Literal["INTRADAY", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"]
    source_id: str   # Link to the raw news chunk
    price: float | None  # Stock price (optional, for validation)
    allocation_percentage: int | None  # % of buying power to allocate (0-100)
    is_priced_in: bool   # Whether news is priced in
    is_priced_in_reasoning: str # Reasoning for pricing
    profit_potential_reasoning: str # Justification for profit potential
    strategy_reasoning: str | None # "Is it possible to make a strategy based on this?"
    advance_planning_notes: str | None # "Should I sell X to buy Y?"
    sell_tool_called: bool # MANDATORY FOR SELL: Whether a tool was used to calculate quantity
    quantity: int | None # The exact quantity of shares to trade
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
    is_government_incentive: bool # Related to government budgets/policy
    expiry_date: str | None # Date when policy/incentive expires
    scenario_analysis: str | None # "If event resolves like X, then position in A"
    source_id: str | None # ID of the source chunk (Optional)
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

1.  **Is it possible to make a profitable trade based on this?** (Profit potential justification)
4.  **Calendar Alignment**: (Using the injected `CALENDAR_STRATEGY_KNOWLEDGE`) Does this trade align with any of the 7 key seasonal strategies?
    - **Turn of the Month (ToM)**: Rally in last trading day + first 3 days of next month.
    - **Payday Anomaly**: Momentum around the 15th and end of the month.
    - **Pre-ECB/Fed Drift**: Positive drift 24-48h before central bank meetings.
    - **Tax Day Trade**: Pressure before April 15th, followed by a relief rally.
    - **Pre-Election Drift**: Election cycle momentum.
    - **Pre-Holiday Effect**: Positive drift 1-2 days before market holidays.
    - **Cultural Calendars (Gold)**: Demand spikes for GLD during festivals (Diwali, etc.).
5.  **Is this news already priced in?** (Using `get_price_history`)
6.  **What is being incentivized right now?** (Government budgets and objectives)
7.  **If I already own this stock, has this trade been profitable?** (Using `get_position_pnl`)
8.  **Should I reduce exposure or take profits?** (Using the granular sell tools like `sell_10_percent` through `sell_100_percent` to calculate exact quantities. **MANDATORY for all SELLs.**)
9.  **What is the expected timeline for this catalyst to materialize?**
10. **What are the primary risks or counter-arguments to this trade?**
11. **How does this stock correlate with my existing portfolio?**


### **The "Source of Truth" Rule**
To prevent confusion between historical context and current holdings, the system prompt explicitly instructs models that the **`Current Portfolio Status`** section is the **ONLY** source of truth for assets they currently own. Any mention of trades in the `Historical Context` (retrieved via RAG) should be treated as past reasoning, not current state.

This logic ensures that trades are based on predicted future movements rather than reacting to yesterday's news.

## 6. Verification

The logic is verified using a comprehensive test suite:
- **Core Logic**: `pytest apps/engine/tests/test_analysis_logic.py`
- **Tool Calling**: `pytest apps/engine/tests/test_llm_tools.py` and `pytest apps/engine/tests/test_gemini_tools.py`
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
- **Defensive Pydantic Validation**:
  - The system uses default values for critical fields like `source_id` in macro events and supports common LLM hallucinations like `MEDIUM_TERM` duration.
  - **JSON List Robustness**: A `field_validator` automatically detects if the LLM returned a JSON-encoded string for the `decisions` or `macro_events` fields (a common behavior in Claude 3.5/4.5 tool use) and parses it into a Python list before validation.
- **Decision Backfill (Resilience)**: If an LLM recommends a trade and provides a valid ticker but fails to extract a price into the JSON schema, the engine automatically backfills the current market price using the `MarketDataManager` before validation.
- **Sync/Async Resilience**: The analysis and verification loops are designed to handle both synchronous and asynchronous response objects from different provider SDKs. For example, the verifier (in `verification.py`) uses a safety check (`hasattr(..., "__await__")`) to support Gemini's native client while remaining compatible with OpenAI/Anthropic's `awaitable` patterns.
- **Ingestion Monitoring (Semantic Fragility)**: The ingestion pipeline (`newsletter.py`) includes a "Semantic Fragility" check that monitors if a sender found in the Gmail search results fails to produce a valid snapshot. This ensures that alerts are only triggered for actual parsing/template failures, avoiding false positives when a sender simply hasn't sent an update in the current window.
- **Verification Safeguards**: The verification layer handles model-specific role mapping (e.g., converting `"assistant"` to `"model"` for Gemini) to ensure compatibility with diverse LLMs acting as skeptical verifiers. It also uses safe variable initialization in the main loop to prevent leaking state between decisions.
- **ETF Liquidity Accuracy**: The `yfinance` provider includes a fallback mechanism to check `totalAssets` or `netAssets` for ETFs, ensuring that specialized funds like `BDRY` are not incorrectly rejected for "$0.00B" market cap.
- **Portfolio Price Persistence**: The execution engine ensures that existing position prices are reused during trade execution, preventing redundant "Market data missing" warnings in logs and maintaining SMA calculation accuracy between market snapshots.
