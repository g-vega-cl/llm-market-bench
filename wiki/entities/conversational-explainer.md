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

Pulls alphanumeric tokens of length ≥ 3 from the user query, drops an expanded stopword set (`what`, `when`, `think`, `after`, `the`, `can`, `some`, `more`, `get`, `put`, `puts`, `call`, `calls`, `into`, `lower`, `higher`, …), lowercases them, and returns at most 6 keywords (falling back to the first 3 raw non-common words if everything was filtered). These keywords drive targeted retrieval while preventing blanket query matches.

### `rank_and_filter_memories(memories, query, now_dt, limit=5)`

Composite ranking function that guarantees fresh, active records outrank decayed historical rows:
- Drops non-ACTIVE rows, academic textbooks (`ACADEMIC_PAPER`), expired calendar events (`target_date < today`), and decayed rows with `relevance_score < 0.20`.
- Ranks candidate rows via composite scoring: `(importance_score / 10) * relevance_score * (0.5 ** (age_days / 60)) * match_boost`.
- Prevents stale high-importance historical events from crowding out fresh market catalysts.

### `retrieve_qa_grounding(sb_client, query, ticker="SPY", limit_memories=5)`

Gathers cross-domain context from the archive DB, failing soft per source (each wrapped in `try/except` with `logger.exception`):

- **`market_feeling`** — the 3 most recent desk turns (`sentiment_label`, `confidence_score`, `why_explanation`, `trades_summary`, `news_summary`, `created_at`).
- **`breaking_news`** — the 5 most recent live headlines from `intraday_market_news` (`source`, `headline`, `event_timestamp`), filtered strictly to `jev_choice = "MARKET_MOVING"` so only Jev-vetted catalysts reach the explainer's news grounding (see [[concepts/jev-news-sieve]]).
- **`trades`** — the 3 most recent executions (`ticker`, `signal`, `price`, `reasoning`, `executed_at`).
- **`memories`** — keyword-matched active rows combined with fresh active market memories, ranked and filtered by `rank_and_filter_memories`.
- **`cause_and_effect`** — keyword-matched causal chains, falling back to the most recent rows.
- **`market_barometer_history`** — the latest valuation ratios with explicit as-of date (`pe_ratio`, `forward_pe`, `pb_ratio`, `ps_ratio`, `earnings_surprise_momentum`).
- **`catalyst_radar`** — upcoming narrative collisions (`target_date >= today`) including target date and impact.

Returns a dict with keys `recent_decisions`, `recent_trades`, `memories`, `cause_and_effect`, `barometer`, `catalyst_radar`, `breaking_news`, `news_summary`, `current_timestamp`.

### `format_qa_context(grounding)`

Renders the grounding dict into lean Markdown sections for the LLM:

- `### CURRENT MARKET CLOCK: YYYY-MM-DD HH:MM UTC` — provides an explicit wall-clock anchor so the model never treats past dates as upcoming events.
- `### TRADING DESK RECENT CHOICES & POSITIONING` — stance, action, VWAP/RSI technicals, UTC turn timestamp, and truncated rationale.
- `### BREAKING LIVE NEWS & MACRO INTELLIGENCE` — rolling 30-minute AI news synthesis and live headlines.
- `### HISTORICAL PRECEDENTS & RETRIEVED MEMORIES` — date-annotated active memories with importance scores.
- `### CAUSAL CHAINS (cause_and_effect)` — cause → market outcome pairs.
- `### MACRO BREADTH & CATALYSTS` — dated barometer ratios (`As of YYYY-MM-DD`) and upcoming dated catalysts.

### `answer_audience_question(query, author, grounding, http_client, strata_url, cheap_proxy_url)`

Builds a **Chief Market Strategist** system prompt (explicitly instructing Markdown prose, no JSON) plus a user prompt containing the audience inquiry and formatted grounding, then calls `query_multi_tier_llm` with `max_tokens=16384` (`EXPLAINER_MAX_TOKENS`) and `reasoning_budget_tokens=12288` (`EXPLAINER_REASONING_BUDGET`). This unconstrained headroom ensures reasoning models (such as Strata ORCA, Gemini Flash, or DeepSeek R1) have ample budget for multi-thousand token chain-of-thought deliberation without truncating the visible Markdown commentary. The two-tier cascade (local Strata with 45s runway → centralized free proxy with 75s fallback) is inherited from [[entities/live-agent-trader]] and wrapped in a 120-second worker client timeout.

### LLM Outage Fallback (`FALLBACK_DESK_PROSE` / `is_llm_outage_fallback`)

When both LLM tiers fail, `query_multi_tier_llm` returns a neutral `HOLD` decision JSON (or an `"All LLM endpoints currently unavailable"` payload) so the trading loop never crashes. That emergency payload is valid for the trader but is **not** valid conversational prose — surfacing raw JSON to the audience would leak internal decision schema and read as broken.

To keep the audience experience clean, `answer_audience_question` post-processes the raw response through `is_llm_outage_fallback(text)`:

- Returns `True` when the text is empty/`None`, contains the substring `"All LLM endpoints currently unavailable"`, or is a JSON object (starts with `{`) that carries an `"action"` key (the trader decision schema).
- When a fallback is detected, the function logs a warning (`Audience QA received emergency LLM fallback response for @{author}; serving clean desk notice.`) and returns the module-level `FALLBACK_DESK_PROSE` constant instead of the raw payload.

`FALLBACK_DESK_PROSE` is a blockquote **Desk Notice** explaining that the quantitative commentary models and local inference desk are temporarily at high inquiry volume or under endpoint maintenance, that the desk is maintaining a neutral risk posture, and that the inquiry has been recorded for the strategists on the next evaluation turn. This guarantees the `agent_chat_queue` row is always persisted with human-readable prose, never raw JSON.

### `process_pending_queue_item(sb_client, http_client, strata_url, cheap_proxy_url)`

One worker iteration:

1. **Atomic dequeue** via the `pop_next_queue_item` RPC (see [[entities/database]]). On RPC failure, falls back to a direct `agent_chat_queue` select of the oldest `pending` row followed by an `injected` status update.
2. Returns `None` when the queue is empty.
3. Retrieves grounding, generates the answer (with the outage fallback applied), and updates the row to `status = 'answered'` with `agent_response` and a fresh `injected_turn_at`.
4. Returns `{id, author, message, response}` for logging.

## Runner Integration

`apps/engine/trading/runner.py` adds `run_qa_worker_loop(sb_client, strata_url, cheap_proxy_url, interval_seconds=300)`, a 5-minute loop that calls `process_pending_queue_item` and logs each answered inquiry. `run_loop` now gathers three concurrent tasks:

- `tape_task` — 20-second Alpaca tape poller + SSE broadcaster.
- `agent_task` — 5-minute autonomous trader turn.
- `qa_task` — 5-minute conversational explainer worker.

## Frontend

`apps/web/src/features/home/components/ConsoleQueueCard.tsx` labels the card **Audience Interactive Queue & Desk Explainer**, prompts visitors to ask about past choices / positioning / macro hypotheses, and renders the latest answered turn's Markdown response in a `whitespace-pre-wrap` block. The answered-turn view (`AnsweredTurnView`) consolidates the question header into a single clean meta row: the `Question` label sits on the left, while the author handle (`@{display_name}`) and short Eastern Date & Time (`formatEasternDateTime` on `created_at`, e.g. `Nov 3 • 10:42 AM ET`) sit on the right, eliminating redundant turn timestamps and clearly indicating the month, day, and time when the question was submitted. When the stored `agent_response` is itself an outage fallback (detected client-side via `isOutageFallbackResponse`), the card renders a styled **DESK NOTICE: HIGH SYSTEM VOLUME** panel instead of the raw text and reports the outage to PostHog Error Tracking (see [[entities/live-agent-trader]] and [[concepts/posthog-stealth-proxy]]).

## Related

- [[entities/live-agent-trader]] — the autonomous trader whose decisions the explainer narrates
- [[entities/database]] — `agent_chat_queue`, `market_feeling`, `memories`, `cause_and_effect`, `catalyst_radar` tables
- [[entities/secondary-minipc-edge]] — the edge host running the trader + QA worker containers
- [[concepts/private-memory-vault]] — user-isolated memory storage
- [[concepts/posthog-stealth-proxy]] — canonical `posthog.captureException` error tracking standard
- [[concepts/jev-news-sieve]] — the sieve whose MARKET_MOVING filter constrains breaking-news grounding
