---
tags: [trading, agent, audience, qa, explainer, llm, edge, runner]
category: entity
---

# Conversational Desk Explainer

`apps/engine/trading/conversational_explainer.py` is the decoupled audience Q&A engine for the live intraday trader. It answers community questions about the desk's past choices, current SPY positioning, and macroeconomic hypotheses (election cycles, midterms, rate decisions, earnings) in articulate Markdown prose, grounded strictly in historical memories, causal chains, and live desk state.

It exists to keep the autonomous trader's decision loop **100% data-driven**: rather than injecting untrusted user text into the trading prompt, the audience queue is served by a separate 5-minute background worker that never touches paper order execution.

## Why It Exists

Earlier the live trader dequeued audience questions inside `execute_intraday_agent_step` and wrapped them in `<audience_question>` blocks inside the trading prompt. That coupled untrusted user input to trade parameters and forced the JSON decision schema to also carry conversational rationale. The explainer splits the two concerns:

- **Trader** — evaluates tape, news, and read-only grounding with zero audience input (see [[entities/live-agent-trader]]).
- **Explainer** — a concurrent worker that reads the queue, retrieves grounding, and writes a conversational answer back to `agent_chat_queue`.

## Components

### `extract_search_keywords(query)`

Pulls alphanumeric tokens of length ≥ 3 from the user query, drops a fixed stopword set (`what`, `when`, `think`, `after`, …), lowercases them, and returns at most 6 keywords (falling back to the first 3 raw words if everything was filtered). These keywords drive the `ilike` OR-filters used for memory and causal-chain retrieval.

### `retrieve_qa_grounding(sb_client, query, ticker="SPY", limit_memories=5)`

Gathers cross-domain context from the archive DB, failing soft per source (each wrapped in `try/except` with `logger.exception`):

- **`market_feeling`** — the 3 most recent desk turns (`sentiment_label`, `confidence_score`, `why_explanation`, `trades_summary`, `created_at`).
- **`trades`** — the 3 most recent executions (`ticker`, `signal`, `price`, `reasoning`, `executed_at`).
- **`memories`** — keyword-matched rows via `.or_(content.ilike.%kw%…)` ordered by `importance_score` descending; if fewer than 2 matches, tops up with the highest-importance memories.
- **`cause_and_effect`** — keyword-matched causal chains, falling back to the most recent rows.
- **`market_barometer_history`** — the latest valuation ratios (`pe_ratio`, `forward_pe`, `pb_ratio`, `ps_ratio`, `earnings_surprise_momentum`).
- **`catalyst_radar`** — the 2 most recent narrative/calendar collisions.

Returns a dict with keys `recent_decisions`, `recent_trades`, `memories`, `cause_and_effect`, `barometer`, `catalyst_radar`.

### `format_qa_context(grounding)`

Renders the grounding dict into lean Markdown sections for the LLM:

- `### TRADING DESK RECENT CHOICES & POSITIONING` — stance, action, VWAP/RSI technicals, and truncated rationale.
- `### HISTORICAL PRECEDENTS & RETRIEVED MEMORIES` — memory content with importance scores.
- `### CAUSAL CHAINS (cause_and_effect)` — cause → market outcome pairs.
- `### MACRO BREADTH & CATALYSTS` — barometer ratios and catalyst radar entries.

### `answer_audience_question(query, author, grounding, http_client, strata_url, cheap_proxy_url)`

Builds a **Chief Market Strategist** system prompt (explicitly instructing Markdown prose, no JSON) plus a user prompt containing the audience inquiry and formatted grounding, then calls `query_multi_tier_llm` with `max_tokens=1500`. The two-tier cascade (local Strata → centralized free proxy) is inherited from [[entities/live-agent-trader]].

### `process_pending_queue_item(sb_client, http_client, strata_url, cheap_proxy_url)`

One worker iteration:

1. **Atomic dequeue** via the `pop_next_queue_item` RPC (see [[entities/database]]). On RPC failure, falls back to a direct `agent_chat_queue` select of the oldest `pending` row followed by an `injected` status update.
2. Returns `None` when the queue is empty.
3. Retrieves grounding, generates the answer, and updates the row to `status = 'answered'` with `agent_response` and a fresh `injected_turn_at`.
4. Returns `{id, author, message, response}` for logging.

## Runner Integration

`apps/engine/trading/runner.py` adds `run_qa_worker_loop(sb_client, strata_url, cheap_proxy_url, interval_seconds=300)`, a 5-minute loop that calls `process_pending_queue_item` and logs each answered inquiry. `run_loop` now gathers three concurrent tasks:

- `tape_task` — 20-second Alpaca tape poller + SSE broadcaster.
- `agent_task` — 5-minute autonomous trader turn.
- `qa_task` — 5-minute conversational explainer worker.

## Frontend

`apps/web/src/features/home/components/ConsoleQueueCard.tsx` labels the card **Audience Interactive Queue & Desk Explainer**, prompts visitors to ask about past choices / positioning / macro hypotheses, and renders the latest answered turn's Markdown response in a `whitespace-pre-wrap` block.

## Related

- [[entities/live-agent-trader]] — the autonomous trader whose decisions the explainer narrates
- [[entities/database]] — `agent_chat_queue`, `market_feeling`, `memories`, `cause_and_effect`, `catalyst_radar` tables
- [[entities/secondary-minipc-edge]] — the edge host running the trader + QA worker containers
- [[concepts/private-memory-vault]] — user-isolated memory storage
