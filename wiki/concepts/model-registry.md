---
tags: [models, providers, registry, cost, audit]
category: concept
---

# Model Registry & Currency

`packages/config/models.json` is the single source of truth for which LLM the platform runs in each pipeline slot. It is read by the Python engine (`apps/engine/core/config.py`) and mirrored by hand into the web layer (`apps/web/src/config/models.ts`), so the registry, the gateway routing table, and the UI labels must be kept in step.

## Current Lineup (verified 2026-11-17 against live provider catalogs)

| Slot | Model id | Provider / endpoint | List price (in / out per 1M) |
| :--- | :--- | :--- | :--- |
| `OPENAI_MODEL` | `gpt-6-luna` | OpenAI `chat/completions` | $0.20 / $1.20 |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | Anthropic `messages` | newest Haiku tier |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Gemini `generateContent` (direct key) | $0.30 / $2.50 |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini embeddings, 768 dims | — |
| `DEEPSEEK_MODEL` / `DEEPSEEK_FLASH_MODEL` | `deepseek-flash` | DeepSeek OpenAI-compatible | flash tier (served by V4.1-Flash-1017) |
| `MINIMAX_MODEL` | `MiniMax-M3.1-Flash` | `api.minimax.io/anthropic` | $0.15 / $0.60 |
| `JEV_MODEL` | `~typesafe/jev-latest` | free-llm-proxy → OpenRouter Decisions | — |

Utility flows route through the free-llm-proxy `auto-go` alias instead of a paid slot; see [[concepts/auto-go-utility-llm]] and [[entities/free-llm-proxy]].

## Renames Are Identity Changes

A model string is not only a routing key. It is also an identity key:

- System portfolio owner ids are derived by concatenation (`sys-daily-spy-{model}`, `sys-daily-tlt-close-{model}` in `apps/engine/execution/daily_trading.py` and `apps/engine/execution/daily_bond_trading.py`). Renaming a slot creates a **new** portfolio, so the old one stops trading and its track record stays frozen under the previous id.
- `AUTORESEARCH_EXPERIMENT_OWNER_IDS`, `AUTORESEARCH_TRACKS`, `AUTORESEARCH_TRACK_MODELS`, and `SKIP_VERIFIER_OWNER_IDS` are keyed by the same strings, so a rename forks the prompt-evolution lineage unless those lists are updated in the same commit. See [[concepts/multi-track-autoresearch]].
- Historical rows (`daily_predictions.model_name`, `decisions.model_name`, `sector_predictions.model_name`, `earnings_predictions.model_name`, `memories.metadata.track_id`) keep the old id forever; anything that joins on model name across the rename boundary must accept both values. Two live examples: `supabase/migrations/20261117120000_leaderboard_accept_minimax_m31_owner_id.sql` widens the leaderboard verifier exemption to `IN ('MiniMax-M3', 'MiniMax-M3.1-Flash')`, and `supabase/migrations/20261117130000_market_feeling_default_minimax_m31.sql` moves the `market_feeling.model_used` column default forward without rewriting history.

### Read-Side Rules After a Rename

- **Display helpers must not relabel history.** `apps/web/src/config/model-aliases.ts` is the single place allowed to name a retired id: it maps `gpt-5.6-luna` → `GPT-5.6 Luna`, `MiniMax-M3` → `MiniMax M3`, `deepseek-v4-flash` → `DeepSeek Flash` (same backend, renamed). It exports `legacyModelLabel(modelName)` (case- and whitespace-tolerant lookup returning `undefined` for live ids) and `isLegacyModelId(modelName)`. The module is presentation-only — it performs no I/O and never imports the live registry, so it can never be consulted when calling a provider. `getAgentDisplayName` (daily score), `getModelDisplayName` (sector predictions) and `getModelDisplayInfo` (leaderboard) consult it before their family-substring fallbacks, so an old row renders as the model that actually ran instead of being silently relabelled as its successor.
- **The leaderboard shows the current lineup only.** `apps/web/src/features/leaderboard/api/fetch-leaderboard.ts` filters RPC rows to `Object.values(MODELS)`, so retired ids keep their rows and equity in `portfolios` but drop off the leaderboard. The alternative — migrating `portfolios.owner_id` in place, which `20260614191000_update_minimax_model_to_m3.sql` did for M2.7 → M3 — preserves the track record but attributes the old model's P&L to the new one.
- **A renamed slot starts a fresh $10k portfolio** unless owner ids are migrated: `Portfolio.load()` creates the missing row with initial cash and Reg T metrics, so the new id trades immediately while the old id freezes. Provision the mechanical `sys-*` rows (spy, spy-close, tlt-close) before the first trading run, because the close-phase liquidation iterates *existing* portfolios rather than creating them.

## API-Surface Gates That Turn a Rename Into a Code Change

A model can be listed in a provider catalog and still be unusable with the payload this app sends. Before swapping an id, probe with the production payload shape:

- **OpenAI Chat Completions + function tools** require `reasoning_effort="none"`. Passing any other effort (or omitting it) returns 400 "Function tools with reasoning_effort are not supported ... use /v1/responses". `gpt-6-luna` and `gpt-5.6-luna` both honour `"none"`; the `gpt-6.2` family does not — it rejects `none` outright *and* rejects tools with any accepted effort, so it only works through the Responses API. Adopting `gpt-6.2` is a handler project, not a config edit. See [[concepts/thinking-agents]].
- **Anthropic 5.5-generation models** reject `{"thinking": {"type": "enabled", "budget_tokens": N}}` and require adaptive thinking plus `output_config.effort`. `get_anthropic_thinking_kwargs` in `apps/engine/core/llm/handlers/anthropic.py` special-cases the literal string `haiku-5-5`; moving to Sonnet/Opus 5.5 means generalising that check first.
- **Gemini 4 Hydrogen** accepts `thinking_level` of `LOW`/`MEDIUM`/`HIGH`/`XHIGH` only (`MINIMAL` and `thinking_budget` are 400s) and silently ignores temperature/top_p/top_k.
- **MiniMax-M3.1-Flash** is a verified drop-in on the Anthropic-compatible endpoint, with and without a thinking budget, at half the M3 price.

## Currency Audit Procedure

1. Read `packages/config/models.json` whole, then grep for hand-maintained copies (`apps/web/src/config/models.ts`, workflow `env:` blocks, CLI defaults, prompt text, gateway `preferred_patterns`).
2. Hit every provider's model-listing endpoint from a scratch script (never commit keys) and diff the configured ids against the live catalog.
3. Probe each configured and candidate model with the production payload shape, tiny output. Distinguish "unknown parameter" (model exists, payload wrong) from "model not found" and from 401/402/403 (credential/billing, which outranks any version gap).
4. Check real usage, not just config: free-llm-proxy `call_logs` for routed provider/model, and per-table `model_name` + `created_at` freshness in the archive DB.
5. Price the delta before recommending; state the multiplier.

`apps/engine/tests/test_model_registry_currency.py` pins the outcome of that procedure: canonical ids per slot, `core.config` re-export parity, owner-id list coherence (`AUTORESEARCH_EXPERIMENT_OWNER_IDS`, `AUTORESEARCH_TRACKS`, `AUTORESEARCH_TRACK_MODELS`, `SKIP_VERIFIER_OWNER_IDS` must all reference configured models), the `models.ts` mirror, and a repo-wide scan proving no retired id survives in production code outside the display-alias map. The scan walks `apps/engine`, `apps/web/src`, `packages/config`, and `.github/workflows`, skipping test directories and `test_*`/`*.test.*`/`*.spec.*` files, and matches `MiniMax-M3` only as an exact id (`MiniMax-M3(?![\w.-])`) so the live `MiniMax-M3.1-Flash` successor is never flagged. A companion assertion keeps `model-aliases.ts` a pure static map — it must still name every retired id (or historical rows would render raw) and must contain no `fetch(`, no `supabase`, and no import of `~/config/models`. `apps/web/src/config/model-aliases.test.ts` covers the label lookups, case/whitespace tolerance, and the live-id negative cases.

## Deferred Upgrades (assessed 2026-11-17, not adopted)

- **`gpt-6.2-sol` / `gpt-6.2-astra`** — requires a Responses API tool loop; 10x/8x the `gpt-6-luna` price. Deferred as a handler project.
- **`gemini-4-hydrogen`** (GA 2026-11-12) and **`gemini-3.8-flash`** — available, but 5x/2.5x the flash-lite input price and Hydrogen changes thinking/sampling semantics. The Gemini slot stays on the cost-efficient tier by choice.
- **`gemini-embedding-2`** — a swap requires re-embedding every stored vector and may change dimensionality; a migration, never a string edit.
- **Claude Sonnet/Opus 5.5** — needs the adaptive-thinking generalisation above plus a tier price jump.

## Related

- [[concepts/thinking-agents]] — per-provider thinking/tooling contracts
- [[concepts/model-anomalies]] — failure modes per model family
- [[concepts/multi-track-autoresearch]] — per-model prompt lineages keyed by these strings
- [[entities/free-llm-proxy]] — provider routing table and zero-cost alias behaviour
- [[concepts/system-portfolios]] — owner-id derivation for systematic portfolios
- [[entities/gemini-api-dev]] — Gemini model catalog, pricing, and thinking-level constraints
