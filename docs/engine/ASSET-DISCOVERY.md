# Asset Discovery: Alpha Discovery Agent

The **Alpha Discovery Agent** is a specialized, tool-calling reasoning engine that identifies actionable investment assets (stocks, ETFs) driven by specific market catalysts or macro events.

The agent uses a **single-call approach** with up to 3 tool steps, outputting structured JSON for direct frontend rendering.

---

## 1. Discovery Architecture

The discovery process is encapsulated within the `DiscoveryAgent` class, which operates as a standalone "mission" for each market theme.

### **Single-Call Flow (max 3 tool steps)**
1.  **Mission Start**: Receives the market theme and context.
2.  **Step 1**: Invokes the `run_stock_screener` tool to find up to 15 candidates based on financial metrics.
3.  **Step 2** (optional): Uses native **Web Search** to verify business models and thematic relevance.
4.  **Step 3**: LLM synthesizes findings and outputs structured JSON directly.

### **Strategic Framework**
The agent is guided by:
1. **Identify the Bottleneck:** Who owns the critical infrastructure or supply that everyone else needs?
2. **Chain of Events:** If X happens, who are the secondary and tertiary beneficiaries?
3. **Uncrowwd Plays:** Look for mid-cap or niche companies that aren't yet priced in.

### **Output Format**
The LLM outputs **structured JSON** for direct frontend rendering:

```json
{
  "assets": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "reason": "Primary beneficiary of AI integration in consumer devices - specific profit mechanism"
    }
  ]
}
```

**Rules:**
- Maximum **5 assets** (fewer is fine)
- NYSE/NASDAQ only, actively trading
- Each asset has: `ticker`, `name`, `reason`

---

## 2. The `run_stock_screener` Tool

This tool is available to all primary providers (OpenAI, Anthropic, Gemini) and serves as the backbone for asset retrieval.

### **Volume Context Enrichment**
The screener automatically enriches each result with **volume context** by fetching per-stock historical volume data and computing a human-readable comparison string (e.g., "2.3x above 20-day average (85th percentile)"). This helps identify stocks with unusual trading activity.

### **Supported Filters**
- **Market Cap**: `market_cap_more_than`, `market_cap_lower_than`
- **Price**: `price_more_than`, `price_lower_than`
- **Beta (Volatility)**: `beta_more_than`, `beta_lower_than`
- **Volume**: `volume_more_than`, `volume_lower_than`
- **Dividend Yield**: `dividend_more_than`, `dividend_lower_than`
- **Classification**: `sector`, `industry`, `exchange` (Defaults to NYSE,NASDAQ)
- **Limits**: Maximum of 15 results per call to ensure context efficiency.

### **Implementation Detail**
The tool is implemented in `apps/engine/core/llm/tools.py` and executed via the `MarketDataManager`. It hits the **Financial Modeling Prep (FMP)** `/company-screener` endpoint.

---

## 3. Provider Support

The `DiscoveryAgent` uses **OpenAI (gpt-5.4-nano)** as the primary provider by default. The `DiscoveryService` initializes the agent with `OPENAI_MODEL` from the shared config.

The agent automatically detects the provider and configures the appropriate tool definitions and handlers:

| Provider | Handler | Search Tool | Screener Definition |
|----------|---------|-------------|---------------------|
| **OpenAI** *(primary)* | `openai.run_tool_loop` | `web_search` (native) | `RUN_STOCK_SCREENER_TOOL_DEFINITION_OPENAI` |
| **Gemini** | `gemini.run_tool_loop` | `google_search` | `RUN_STOCK_SCREENER_TOOL_DEFINITION_GEMINI` |
| **Anthropic** | `anthropic.run_tool_loop` | `web_search_20250305` | `RUN_STOCK_SCREENER_TOOL_DEFINITION_ANTHROPIC` |

> **Note:** OpenAI is preferred because it has straightforward function calling without the Gemini quirk of rejecting combined built-in tools + custom function declarations.

### **Client Architecture**
The `DiscoveryAgent` passes the **raw OpenAI client** (`client.client`) to `run_tool_loop` rather than the Instructor-wrapped client. This is because Instructor intercepts `chat.completions.create()` calls and expects a `response_model` argument, which `run_tool_loop` doesn't provide.

---

## 4. Operational Flow

1.  **`DiscoveryService.discover_assets(event)`**: Entry point. Initializes `DiscoveryAgent` with `OPENAI_MODEL`.
2.  **`DiscoveryAgent.discover_assets(theme)`**: Single tool-calling mission with `max_tool_steps=3`.
3.  **Tool Loop**: Agent calls `run_stock_screener` (step 1), optionally `web_search` (step 2), then synthesizes JSON (step 3).
4.  **JSON Parsing**: Final text is searched for JSON blocks (markdown ```json ``` or raw JSON). Parsed into `List[dict]` with `ticker`, `name`, `reason`.
5.  **Validation**: Tickers are uppercased, assets without tickers are filtered out.
6.  **Return**: Returns `List[dict]` (max 5 assets) directly — no wrapper.

---

## 5. Why This Approach?

#### **Simplicity & Reliability**
Single-call flow with JSON output eliminates the complexity of retry logic and multiple fallback mechanisms, reducing failure modes.

#### **Frontend-Ready Output**
Structured JSON is designed for direct frontend rendering in the "Investable Assets" section of memory cards, without requiring additional parsing or transformation.

#### **Liquidity & Quality Guardrails**
The agent is explicitly prompted to filter for **NYSE/NASDAQ** only and ensure assets are **actively trading**. The screener returns up to 15 candidates; the LLM narrows to best ~5.

---

## 6. Verification
The discovery pipeline quality is verified using:
- **`pytest apps/engine/tests/test_discovery_agent.py`**: Unit tests for JSON parsing, single-call behavior, and validation.
- **`pytest apps/engine/tests/test_discovery_quality.py`**: Integration tests validating the service correctly delegates to the agent.
- **`pytest apps/engine/tests/test_regression_fixes.py`**: Verifies handler imports and stalled loop behavior.
