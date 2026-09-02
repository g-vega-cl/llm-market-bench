---
tags: [entity, chat, gateway, LLM, UI]
category: entity
---

# Investment Chat Gateway

Gated "Should I invest in this stock?" chat interface connecting users with LLM agents, PostgreSQL database tables, memory theses, and market briefings. The gateway provides a conversational research terminal for interrogating previous agent decisions, market memories, causal chains (cause_and_effect), and portfolio performance.

## Architecture

### UI Architecture
- **Dedicated `/chat` terminal** (`ChatPage.tsx`): Full-page responsive research terminal with hero background, section heading, and chat stream. This is the primary entry point for the chat gateway.
- **Floating drawer widget** (`ChatWidget.tsx`): Previously rendered globally, now unused in the root layout. The widget component still exists but is not currently rendered on any page.

### Chat Components
- **ChatInterface**: Core component providing message stream, input, tool trace accordion, and suggested prompt chips. Handles authorization gating, localStorage persistence, and auto-scrolling.
- **ChatPage**: Wraps ChatInterface in a full-page layout with hero header and section heading.

### Tool Suite (4 specialized tools)
The chat agent (DeepSeek Flash) uses these read-only tools against Supabase:

1. **search_memories_and_theses** — Searches `memories` and `cause_and_effect` tables by ticker or keyword. Returns memory cards, causal links, and importance scores.
2. **get_stock_context_and_trades** — Retrieves recent trades, execution prices, buy/sell theses, and model decisions from the `trades` and `decisions` tables.
3. **get_market_sentiment_and_newsletter** — Fetches latest `market_feeling` entry and `generated_newsletters` entry.
4. **query_database_table** — Generic safe read-only SQL-like query against any table (trades, portfolios, sector_predictions, etc.).

### Deep Links & Context Sharing
- **Daily Market Briefings**: Briefing pages have a "Discuss in AI Chat" button pre-populating the query with the newsletter title and summary.
- **Memory Cards**: Memory cards have "Discuss in Chat" links that carry the memory content and ticker into `/chat`.
- **Asset Theses**: Asset modal views feature "Ask AI Gateway ($TICKER)" deep-links.

### Authorization
- Only the email `g.vega.cl@gmail.com` is whitelisted via `ALLOWED_CHAT_EMAILS`.
- Unauthorized users see a gated banner with a sign-in button listing available capabilities.

### Conversation History & Next Best Questions
- Messages are persisted to `localStorage` under key `benchify_chat_messages_v2`.
- Greeting message is prepended on fresh conversation with static suggested inquiries.
- **Contextual Follow-up Questions**: On each turn, the assistant generates 2-3 tailored follow-up queries enclosed in `<suggested_questions>` tags. The server sanitizes the text, extracts the questions array, and the UI renders interactive prompt chips below the latest assistant message.
- A "Clear" button resets history.

## Tool Execution Flow

1. **System prompt** instructs the LLM to use tools, format responses with Markdown, and end responses with structured `<suggested_questions>` blocks.
2. **executeSingleStep**: Sends messages to DeepSeek API with tool definitions.
3. **processToolCalls**: For each tool call, executes the appropriate backend function, accumulates a `ToolTrace` with tool name and summary.
4. **MAX_TOOL_STEPS = 4**: Up to 4 back-and-forth rounds of tool calls allowed.
5. **ToolTraces and Suggested Questions** are extracted and returned with the final assistant message for interactive UI display.

## Related

- [[entities/web-app]] — Parent web application
- [[entities/database]] — Supabase tables and schemas
- [[entities/generated-newsletters]] — Newsletter pages with deep links
- [[concepts/memory-feedback]] — Long-term memory reflection system
- [[concepts/rag-strategy]] — Retrieval augmented generation patterns
