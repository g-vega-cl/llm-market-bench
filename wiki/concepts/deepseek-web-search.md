---
tags: [deepseek, web-search, tool, concept]
category: concept
---

# DeepSeek Web Search Tool

The system integrates a generic `web_search` tool into DeepSeek's tool-calling loop, enabling LLM agents to perform live web queries for real-time financial news, catalysts, and market reports. The tool is conditionally enabled via the `ENABLE_DEEPSEEK_WEB_SEARCH` environment variable (defaults to `true`).

## Implementation

- **Tool Function**: `execute_web_search_tool` in `apps/engine/core/llm/tools.py`, dispatched by `apps/engine/core/llm/handlers/base.py`.
- **Search Strategy**:
  1. **Primary**: DuckDuckGo HTML scraping via `httpx` and `BeautifulSoup` (parses `result`-class divs).
  2. **Fallback**: FMP Stock News API (extracts tickers from query, defaults to `"LIN"`).
- **Injection**: Added to the base tool list in `_build_deepseek_tool_list()` (`apps/engine/core/llm/handlers/deepseek.py`), making it available to all DeepSeek tool loops when enabled.

## Usage in Agents

- **LinAgent** (`apps/engine/analysis/lin_agent.py`): Uses `web_search` during its `query_llm` method to retrieve semiconductor fab gas demand catalysts before making trade decisions.
- **AutoResearcher** (`apps/engine/autoresearch/researcher.py`): The `PromptResearchResult` model includes `'web_search'` in its list of selectable tools, allowing weekly prompt mutations to enable web search for catalyst discovery.

## Configuration

Set `ENABLE_DEEPSEEK_WEB_SEARCH=true` (default) to make the tool available. When disabled, agents will not have access to web search.

## Related

- [[entities/lin-renko-agent]] — uses the tool in its analysis loop
- [[entities/autoresearch]] — can select the tool via prompt mutation
- [[concepts/tool-enforcement]] — the 4-layer enforcement system that validates tool usage
