# Asset Discovery: Alpha Discovery Agent

The **Alpha Discovery Agent** is a specialized, tool-calling reasoning engine that identifies actionable investment assets (stocks, ETFs) driven by specific market catalysts or macro events. 

Unlike the previous hardcoded multi-stage pipeline, this agent uses a dynamic, autonomous reasoning loop to ensure that identified assets are logically aligned with the event's "How to Profit" thesis and verified against real-time market data.

---

## 1. Discovery Architecture

The discovery process is encapsulated within the `DiscoveryAgent` class, which operates as a standalone "mission" for each market theme.

### **Reasoning Loop (Tool-Calling)**
The agent uses a **Tool-Calling Reasoning Loop** (up to 3 steps) to perform its mission:
1.  **Mission Start**: Receives the market theme and context.
2.  **Screening**: Invokes the `run_stock_screener` tool to find candidates based on financial metrics (Market Cap, Beta, Sector, Industry).
3.  **Research & Verification**: Uses native **Web Search** (OpenAI `web_search`, Anthropic `web_search`, Google Search for Gemini) to verify the business model, thematic relevance, and recent news for the candidates.
4.  **Synthesis**: Ranks the candidates and formulates a "Mechanism of Profit" for each.

### **Thematic Mapping Logic**
The agent is guided by the **"5 Whys"** technique to ensure high-fidelity discovery. The agent is **required** to include explicit answers to all 5 Whys in its output:

1. **Why** is this theme market-moving?
2. **Why** will these specific assets benefit?
3. **Why** are these not already priced in?
4. **Why** is this the most efficient way to profit?
5. **Why** is your recommendation the best beneficiary?

The output must follow this structured format:

```markdown
## 5 Whys Analysis
Answer EACH of the following questions explicitly:
1. **Why** is this theme market-moving? [Your detailed answer]
2. **Why** will these specific assets benefit? [Your detailed answer]
3. **Why** are these not already priced in? [Your detailed answer]
4. **Why** is this the most efficient way to profit? [Your detailed answer]
5. **Why** is your recommendation the best beneficiary? [Your detailed answer]

## Recommended Assets
| Ticker | Company Name | Relevance Score | Mechanism of Profit |
|--------|--------------|-----------------|---------------------|
| AAPL   | Apple Inc.  | 85              | [Why it benefits]   |
```

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
2.  **`DiscoveryAgent.discover_assets(theme)`**: Starts the tool-calling mission.
3.  **Loop Step 1-3**: Agent calls `run_stock_screener` and `web_search`.
4.  **Final Extraction**: The agent walks backward through messages to find:
    - First, the last assistant message with meaningful text content
    - If none found (or content < 50 chars), collects relevant tool results (stock screening output)
5.  **5 Whys Validation**: The `_validate_5_whys()` method validates that all 5 Whys questions are explicitly answered using regex pattern matching. If validation fails and content is short, a note is appended indicating which Whys are missing.
6.  **Memory Storage**: The result is wrapped as a single high-fidelity "AGENT_DISCOVERY" asset in the `memories` table to preserve the agent's full reasoning.

---

## 5. Why This Approach?

#### **Autonomous Precision**
By moving from a hardcoded 3-stage pipeline to an autonomous agent, the system can adapt its search strategy based on the theme. For example, it might choose to search for "niche lithium miners" via web search first, then use the screener to verify their liquidity.

#### **Liquidity & Quality Guardrails**
The agent is explicitly prompted to filter for **NYSE/NASDAQ** only and ensure assets are **actively trading**. It also enforces a **15-ticker cap** to prevent "context bloating" for the downstream parallel analysis LLMs.

#### **Institutional Memory**
By storing the agent's full analysis in the "Investable Assets" section of the memory, we provide the Reasoning Manager with a rich "How to Profit" playbook rather than just a list of tickers.

---

## 6. Verification
The discovery pipeline quality is verified using:
- **`pytest apps/engine/tests/test_discovery_quality.py`**: Validates that the service correctly delegates to the agent.
- **`pytest apps/engine/tests/test_regression_fixes.py`**: Verifies handler imports and fallback paths for the agent.
