---
tags: [llm, free-llm-proxy, auto-go, architecture, cost-optimization, utility-flows]
category: concept
---
# Auto-Go Utility LLM Consolidation

The engine routes nearly every non-trading "utility" LLM call — newsletter de-advertisement, economic-calendar relevance filtering, government policy extraction, memory consolidation, post-trade post-mortems, cause & effect analysis, weekly log auditing, newsletter pre-filter summarization, memory importance ranking, and related-ticker discovery — through a single client factory pointed at the **free-llm-proxy** virtual alias **`auto-go`**. Only the competitive trading agents, verifier, and predictors keep their own dedicated provider clients.

## Why It Exists

Utility flows are high-volume, low-stakes, and structurally similar: they take a chunk of text, ask a model for a structured Pydantic object, and persist the result. Giving each one its own hardcoded provider and model (`GEMINI_MODEL`, `DEEPSEEK_FLASH_MODEL`, …) coupled the engine to whichever vendor happened to be cheap that quarter, and duplicated per-provider SDK quirks (forced tool_choice, empty content, thinking-block preservation) across a dozen call sites.

`auto-go` — the free-llm-proxy alias that exhausts the free provider pool before ever falling back to the paid OpenCode Go tier (see [[entities/free-llm-proxy]]) — collapses all of that into one HTTP endpoint. Provider churn (Groq, Gemini, OpenRouter, NVIDIA NIM, local Strata) is absorbed by the proxy's dynamic catalog discovery and circuit breaker, so the engine no longer needs a code change when a free-tier checkpoint is retired.

## Configuration

The free-proxy endpoint and credential are engine config, not per-call literals:

| Setting | Source | Default |
| :--- | :--- | :--- |
| `AUTO_GO_MODEL` | `apps/engine/core/config.py` | `"auto-go"` |
| `FREE_LLM_PROXY_URL` | env (`FREE_LLM_PROXY_URL`) | `https://llm.clvg.uk/v1` |
| `FREE_PROXY_MASTER_KEY` | env (`FREE_PROXY_MASTER_KEY`) | empty |

Both env keys are declared in `apps/engine/.env.example`. Every GitHub Actions workflow that exercises a migrated flow injects `FREE_LLM_PROXY_URL` and `FREE_PROXY_MASTER_KEY` from repo secrets, so CI runners reach the same proxy as local runs. The covered workflow steps are:

| Workflow | Step(s) |
| :--- | :--- |
| `ingest.yml` | Run ingestion & consensus pipeline |
| `weekend-ingest.yml` | Run weekend ingestion pipeline |
| `generate-newsletter.yml` | Run Newsletter Generator; Research Newsletter Mentioned Companies |
| `calendar.yml` | Run Calendar Ingestion |
| `update-earnings-alpha.yml` | Run earnings alpha and bellwether update script |
| `post-analysis.yml` | Run post-analysis pipeline |
| `cause-and-effect.yml` | Run Cause & Effect Analysis |
| `audit.yml` | Run system audit; Cleanup old records |
| `autoresearch.yml` | Run auto-research cycle |
| `daily-predictor.yml` | Run Daily Predictor Command; Run Daily TLT Bond Predictor; Run Day-1 Earnings Movement Predictor; Run Daily Stock Picker Arena (3 Up, 3 Down) |
| `frontier-tech.yml` | Execute Frontier Tech Supercycle Task |
| `future-forces.yml` | Execute Future Forces Task |

That is 15 guarded steps across 12 workflows. Any new workflow step that invokes a migrated flow must add both secrets to its `env:` block, otherwise the factory raises on a remote proxy URL and the flow degrades to its fallback behavior.

## Client Factories (`apps/engine/core/llm/clients.py`)

Two factories back all utility calls, both re-exported from `core.llm` and registered in `CLIENT_FACTORIES` under the key `"auto_go"`:

### `get_auto_go_raw_client(api_key=None, purpose=None)`
Returns a raw `AsyncOpenAI` pointed at `FREE_LLM_PROXY_URL` with `max_retries=0` and the engine's standard `TIMEOUT`. When a `purpose` is supplied it is attached as the `X-Purpose` default header, so free-llm-proxy's audit database records *why* each call happened (`newsletter-pre-filter`, `weekly-log-audit`, `memory-consolidation`, `post-trade-analysis`, `economic-calendar-filter`, `government-policy-extraction`, `cause-and-effect-analysis`, `cause-and-effect-tickers`, `tool-search-related-tickers`, `rank-memories`, `newsletter-de-advertisement`).

Credential resolution: an explicit `api_key` wins, otherwise `FREE_PROXY_MASTER_KEY`. If the resolved key is empty the factory raises `ValueError("FREE_PROXY_MASTER_KEY must be configured for remote free-llm-proxy calls.")` — **unless** `FREE_LLM_PROXY_URL` points at loopback (`127.0.0.1`, `localhost`, `::1`), in which case a `"local"` placeholder key is used so a locally-hosted proxy works without a master key. This keeps hermetic tests and unprovisioned dev boxes clean.

### `get_auto_go_client(api_key=None, purpose=None)`
Wraps the raw client with `instructor.from_openai(..., mode=instructor.Mode.MD_JSON)`. Markdown-JSON extraction avoids forced `tool_choice`, which is what lets the proxy's heterogeneous provider pool (reasoning models, Gemini, Groq, etc.) return structured Pydantic objects without 400 errors.

Every migrated call site closes its client in a `finally` block via `close_client(client, "auto_go")` (or `client.close()` for the raw client), so no HTTP connection pool leaks across long pipeline runs. Call sites that construct the client inside their `try` block guard the close with `if client is not None:` so a factory failure cannot raise a second time from the cleanup path.

## Migrated Call Sites

| Module | Flow | Previously |
| :--- | :--- | :--- |
| `apps/engine/ingest/cleaner.py` | De-advertisement pass (`clean_newsletter_content`) | Gemini Flash Lite |
| `apps/engine/ingest/calendar.py` | `CalendarPipeline` economic-calendar relevance | DeepSeek Flash |
| `apps/engine/ingest/government.py` | `GovernmentPipeline.extract_policy_memories` policy catalyst extraction | Gemini |
| `apps/engine/analysis/pre_filter.py` | `summarize_newsletters` newsletter triage menu | DeepSeek Flash |
| `apps/engine/analysis/post_analysis.py` | Manager Agent post-trade post-mortems | Gemini |
| `apps/engine/analysis/cause_and_effect_analysis.py` | Ticker suggestion + causal outcome synthesis | Gemini |
| `apps/engine/memory/store.py` | `consolidate_overlapping_memories` sleep-cycle synthesis | DeepSeek Flash |
| `apps/engine/scripts/rank_memories.py` | Memory importance ranking script | Gemini |
| `apps/engine/core/audit/analyzer.py` | Weekly log-blob audit (`analyze_log_blob`) | DeepSeek via `AsyncOpenAI` |
| `apps/engine/tools/earnings.py` | `search_related_tickers` thematic ticker discovery | Gemini |

`apps/engine/core/audit/analyzer.py` uses the raw client (it parses a JSON array out of plain text rather than a Pydantic model) and accepts `FREE_PROXY_MASTER_KEY` as a third fallback behind the legacy `DEEPSEEK_API_KEY` alias, which is retained solely so existing tests keep importing a stable name. `apps/engine/cli/audit.py` now calls `configure_analyzer(FREE_PROXY_MASTER_KEY)`.

## What Stays on Direct Provider Clients

The auto-go migration is deliberately scoped to utility flows. Unchanged:

- **Trading analysis agents, verifier, and predictors** — DeepSeek, Anthropic, Gemini, OpenAI Luna, and MiniMax keep their dedicated clients, thinking-mode contracts, and tool loops (see [[concepts/thinking-agents]] and [[concepts/agents]]).
- **`apps/engine/core/llm/policy_lookup.py`** — stays on the Google GenAI SDK because it depends on Gemini's built-in Google Search grounding tool, which the proxy cannot provide.
- **Vector embeddings** — Gemini embedding calls are unrelated to chat completions.

## Live Trader: Single-Tier Auto-Go Routing

`query_multi_tier_llm` in `apps/engine/trading/live_intraday_agent.py` no longer cascades through local Strata first. It posts directly to `{FREE_LLM_PROXY_URL}/chat/completions` with `model = FREE_PROXY_MODEL` (default `auto-go`), a `purpose` argument threaded into the `X-Purpose` header (`live-spy-trader`, `homepage-audience-qa`, `homepage-news-synthesis`), and an optional `Authorization: Bearer <master key>`. This removes GPU contention between the 24/7 daemon and local autoresearch runs.

Legacy `strata_url`, `reasoning_budget_tokens`, and `strata_timeout` parameters remain in the signature for caller compatibility and are explicitly ignored. The `market_feeling.model_used` field now records the resolved `FREE_PROXY_MODEL` instead of the old `"Strata / Cheap-LLM-Cascade"` label. `docker/archive/docker-compose.secondary.yml` likewise defaults `FREE_PROXY_MODEL` to `auto-go` instead of `auto-strata`. See [[entities/live-agent-trader]] and [[entities/secondary-minipc-edge]].

Reasoning tokens are billed inside `max_tokens`, so the auto-go budget is the thinking budget. `query_multi_tier_llm` now defaults to `max_tokens=32768` (the trading turn and the conversational explainer both use it) because the previous `16384` sat exactly on the proxy's global clamp and truncated chain-of-thought-heavy answers before the visible decision was emitted. Utility flows keep deliberately terse budgets — the news synthesizer still passes `4096` — because they want short answers, not deep thinking. On the proxy side the clamp is now per-provider (`max_output_tokens` in `providers.json`), so a raised caller budget is no longer silently rewritten to a single global ceiling. See [[entities/free-llm-proxy]].

## Never-Unanswered Failover

`auto-go` is defined as "free pool, then OpenCode Go", and the proxy now enforces that definition end to end. Before this contract, 24 of 7,681 audited calls returned a terminal `502`; every one of them had attempted 5-7 distinct providers (no chain ever repeated a provider), and 10 of them ended with `opencode-go (skipped: paid guard after free timeout)` — the one tier that answers was refused because a free provider was slow. The wasted effort was compounded by the callers: `get_auto_go_client` is wrapped by instructor call sites that pass `max_retries=2` (`apps/engine/ingest/cleaner.py`, `apps/engine/analysis/pre_filter.py`, `apps/engine/tasks/newsletter_generator.py`), so the visible "three retries" is three attempts at the same alias, each one a full multi-provider pass, and each pass took 272-721s against a 180s caller timeout (`TIMEOUT` in `apps/engine/core/llm/clients.py`).

Three changes make the alias keep its promise:

1. **Routing is the money control** — the paid provider's `auto_aliases` allowlist admits OpenCode Go to `auto-go`, `auto-strata-go`, and `strata-auto-go` only, so a free alias never receives a paid candidate. The old timeout-keyed `PAID_TIMEOUT_GUARD` branch was unreachable once that allowlist did the work, and was deleted rather than left as a knob that could not change anything.
2. **Free-plan models first inside Go** — `free_model_patterns` (`["*free*"]`) is matched against Go's live catalog before the single metered `last_resort_model` (`deepseek-v4.1-flash`), so a subscription call does not buy tokens while a plan-included model is available. At most one metered model is dispatched per request.
3. **Bounded pass** — `FREE_ATTEMPT_TIMEOUT_SECONDS` (45s), `FREE_PASS_DEADLINE_SECONDS` (120s), `PAID_ATTEMPT_TIMEOUT_SECONDS` (45s) and `PAID_PASS_DEADLINE_SECONDS` (45s) bound a non-streaming pass to roughly 165s, inside the caller's 180s window. The remaining budget is re-checked before every dispatch, including each in-provider cascade retry, so a four-model cascade cannot spend it four times over; a per-day/quota `429` ends the cascade instead of spending four attempts on a wall that cannot clear.

See [[entities/free-llm-proxy]] for the knobs and the terminal `failover_chain` shape.

## Failure Behavior

Migrated flows keep their pre-existing failure semantics. De-advertisement still falls back to the original newsletter text, the calendar pipeline returns `0` events, government extraction returns `0` memories, and post-analysis simply logs and skips the trade. The log analyzer returns `None` on a missing key, empty `choices`, or an exception — and now distinguishes the empty-response case explicitly with `logger.error("auto-go log analysis returned empty choices/content")` rather than crashing on `choices[0]`. All exception handlers were upgraded to `logger.exception(...)` per [[concepts/observability-standard]].

`clean_newsletter_content` in `apps/engine/ingest/cleaner.py` constructs its auto-go client **inside** the `try` block, so a factory-level failure (for example a missing `FREE_PROXY_MASTER_KEY` while `FREE_LLM_PROXY_URL` points at a remote proxy) is caught by the same handler that guards the LLM call. The newsletter is returned unchanged as a `CleanedNewsletterText` with `is_pure_ad=False`, `ads_removed_count=0`, and an empty `ads_summary`, and the `finally` block only calls `close_client` when a client was actually created. A misconfigured proxy therefore degrades ingestion to raw text instead of aborting the pipeline.

## Verification

`apps/engine/tests/test_auto_go_migration.py` is a hermetic reproduction suite covering: config defaults, factory kwargs (`api_key`, `base_url`, `max_retries=0`, `X-Purpose` header), the remote-key `ValueError`, MD_JSON wrapping, every migrated call site asserting `model="auto-go"` plus the paired `close_client(..., "auto_go")`, the policy-lookup exception that keeps Gemini + Google Search, and a YAML assertion that all 15 guarded steps across the 12 workflows listed above inject both free-proxy secrets. It also asserts that `synthesize_recent_news` requests at least 2,048 completion tokens (see [[entities/live-agent-trader]]) and that `clean_newsletter_content` returns the original text when `get_auto_go_client` raises. Existing suites (`test_cleaner.py`, `test_calendar.py`, `test_post_analysis.py`, `test_government_pipeline.py`, `test_memory_consolidation.py`, `test_audit_analyzer.py`, `test_deepseek_flash_migration.py`, `test_cause_and_effect_dedupe.py`, `test_newsletter_menu_flow.py`, `test_log_reduction.py`) were repointed from the old provider patches to `get_auto_go_client` / `get_auto_go_raw_client`.

`apps/engine/tests/conftest.py` seeds `FREE_PROXY_MASTER_KEY="mock-free-proxy-key"` alongside the other dummy credentials so the suite never depends on ambient env.

## Related
- [[entities/free-llm-proxy]] — the proxy whose `auto-go` alias backs every call described here
- [[concepts/thinking-agents]] — the provider-specific contracts that trading agents still use
- [[concepts/agents]] — the specialized multi-agent roles, including the Manager and Cause & Effect agents migrated here
- [[concepts/ad-stripping-audit]] — the de-advertisement cleaner now running on auto-go
- [[entities/government-ingestion]] — the policy extraction stage now running on auto-go
- [[concepts/memory-feedback]] — post-mortem and sleep-cycle consolidation flows
- [[concepts/weekly-audit]] — the weekly log audit that consumes the migrated analyzer
- [[concepts/observability-standard]] — traceback hardening applied across the migrated handlers
- [[entities/live-agent-trader]] — the daemon whose inference path is now single-tier auto-go
