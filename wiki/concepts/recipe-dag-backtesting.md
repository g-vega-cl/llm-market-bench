---
tags: [recipes, dag, backtesting, validation, point-in-time, pnl, llm-budget]
category: concept
---

# Recipe DAG Validation & Timeline Backtesting

The invariants and accounting rules that make a [[entities/recipe-studio]] strategy recipe safe to simulate and safe to run live. A recipe is a Directed Acyclic Graph of news, price, technical, LLM, and risk nodes; the engine must reject malformed graphs before execution, replay them without forward-looking leakage, and report P&L under two explicit cost models.

## 1. DAG Validation (`apps/engine/recipes/validator.py`)

`validate_recipe_graph(graph_data)` accepts a `RecipeGraph` or a raw dict and returns `(is_valid, errors)`. It enforces five structural invariants:

1. **Schema conformance** — the graph must parse as `RecipeGraph`; each node's `config` is re-validated against its per-type Pydantic model (`NewsSourceConfig`, `TechnicalGateConfig`, `ClassificationConfig`, `GenerativeAnalystConfig`, `RiskOutputConfig`).
2. **Unique node IDs** — duplicate IDs are rejected.
3. **Edge integrity** — every edge's `from` and `to` must reference an existing node.
4. **Source and sink presence** — at least one source node (`news_source` or `price_tape`) and exactly at least one terminal `risk_output` node are required. A graph with no sink can never emit a trade.
5. **Acyclicity** — a three-color DFS (`_detect_cycle`) rejects any cycle. Recipes must be DAGs, so a node can never feed back into an ancestor.

The worker calls the validator on every dequeued job and raises `ValueError` on failure, which marks the queue row `failed` with the joined error list in `error_message`.

## 2. Point-in-Time News Corpus (`apps/engine/recipes/news_corpus.py`)

`query_corpus_point_in_time(sb_client, cutoff_timestamp, tickers, buckets, keywords, lookback_hours, limit)` is the only sanctioned way the backtester reads news. It guarantees:

- `date_published <= cutoff_timestamp` — zero forward leakage; an article published after the simulated bar can never influence that bar.
- `date_published >= cutoff_timestamp - lookback_hours` — bounded recency window.
- Optional `overlaps()` filters on the `tickers` and `buckets` GIN-indexed array columns, plus an in-memory keyword filter over `title` + `full_text`.

### Bucket Derivation

`derive_article_buckets(title, full_text, company, companies, tickers)` assigns each article to canonical thematic buckets through three passes:

1. **Company map** (`_COMPANY_TO_BUCKETS`) — e.g. `Nvidia` → `semiconductors` + `ai_cloud`, `JPMorgan Chase` → `financials`.
2. **General-market promotion** — when `company == "general_market"` or no tickers are present, the article is tagged `macro_general` and the macro index tickers `SPY`, `QQQ`, `TLT` are appended.
3. **Regex keyword matching** (`_BUCKET_PATTERNS`) across ten buckets: `semiconductors`, `ai_cloud`, `earnings`, `fed_rates`, `macro_inflation`, `energy`, `financials`, `healthcare`, `tariffs_trade`, `m_and_a`. A fallback `general_market` bucket is applied when nothing matches.

`parse_and_normalize_article(raw)` rejects records missing `article_id`, `title`, `url`, or a parseable `date_published`, and normalizes timestamps to UTC ISO-8601. `import_stock_news_corpus(paths, sb_client, batch_size)` upserts idempotently on `article_id` and returns `{total_read, inserted, skipped_or_invalid}`.

## 3. Timeline Backtest Semantics (`apps/engine/recipes/backtester.py`)

`run_recipe_backtest(recipe, bars_by_week, news_articles, llm_evaluator, max_llm_calls=40, slippage_bps=5.0, starting_capital=10000.0)` steps each ISO week chronologically, bar by bar:

1. **Exit evaluation first** — open positions are checked before new entries so freed capital is available in the same bar.
2. **Concurrency cap** — `concurrency.max_open_trades` (default 3) blocks new entries; `max_equity_pct_per_trade` (default 33.3%) sizes each position.
3. **Technical gate short-circuit** — `evaluate_technical_gate` runs all `ConditionRule`s with AND semantics. A failure logs a `TECHNICAL_BLOCKED` skipped trade and **never invokes the LLM**, which is the primary compute-saving mechanism.
4. **News catalyst gate** — `_find_qualifying_article` selects the latest article within `lookback_hours` matching the configured bucket and tickers; absence logs `NO_CATALYST`.
5. **LLM classification gate** — `_evaluate_llm_gate` caches results by `article_id` so a repeated article costs one call, and enforces the `max_llm_calls` budget (default 40) by logging `BUDGET_EXCEEDED`. A choice/confidence miss logs `LLM_REJECTED`.
6. **Entry** — `_create_position` computes shares from allocated cash, then sets stop-loss and target-profit prices from the configured percentages (inverted for `SELL`/short).

### Conservative Exit Ordering

`_check_position_exit` evaluates, in order: stop loss → target profit → `MAX_HOLD` (bar count) → `SESSION_CLOSE` (last bar of the week when `exit_on_session_close` is true). When a single bar breaches **both** the stop and the target, the stop is assumed to have filled first — a deliberately pessimistic assumption that prevents backtests from overstating performance on wide-wick bars.

## 4. Dual P&L Accounting (`apps/engine/recipes/backtest_models.py`)

Every completed trade carries two parallel results so users can separate signal quality from execution friction:

- **Midpoint (zero-cost)** — `pnl_midpoint` / `return_pct_midpoint` computed at the raw entry and exit prices.
- **Net (slippage-adjusted)** — `pnl_net` / `return_pct_net` computed with `slippage_rate = slippage_bps / 10000` applied adversely on both legs: a long pays `entry * (1 + rate)` and receives `exit * (1 - rate)`; a short receives `entry * (1 - rate)` and pays `exit * (1 + rate)`.

`close_position` fills at the exact `target_price` or `stop_loss_price` when the exit reason is `TARGET_PROFIT` or `STOP_LOSS`, and at the bar close otherwise.

`build_backtest_summary` aggregates the run into `total_return_pct_midpoint` / `total_return_pct_net`, `win_rate_pct`, `profit_factor` (gross profit / gross loss, capped at `99.0` when there are no losses), `max_drawdown_pct` (peak-to-trough over the net equity curve), `llm_calls_made`, the full `equity_curve`, `trades`, `skipped_trades`, and a per-week `weeks_breakdown`.

## 5. Counterfactual Skipped-Trade Attribution

`SkippedTrade` records every signal the recipe declined to take, tagged with one of four `skip_type` values — `TECHNICAL_BLOCKED`, `NO_CATALYST`, `LLM_REJECTED`, `BUDGET_EXCEEDED` — plus the timestamp, human-readable reason, and the catalyst headline. This makes the backtest auditable in the same spirit as [[concepts/auditability]]: a user can see not only what the strategy traded, but which gates suppressed which opportunities.

## Related

- [[entities/recipe-studio]] — the subsystem that hosts these modules
- [[concepts/zero-lookahead-materialization]] — the broader point-in-time discipline
- [[concepts/auditability]] — full traceability of every decision
- [[concepts/jev-decisions-model]] — the classifier used by `classification` nodes
- [[concepts/zero-frontend-compute]] — heavy simulation runs in the engine, never in the browser
