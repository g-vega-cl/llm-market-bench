---
tags: [entity, stock-picker, daily-predictions, long-short, autoresearch]
category: entity
---

# Daily Stock Picker Arena (3 Up, 3 Down)

The **Daily Stock Picker Arena** (`apps/engine/tasks/stock_picker.py`) is an autonomous multi-model equity selection engine that runs every morning before the US market opens. It screens morning intelligence briefings, tasks an arena of foundation models with selecting exactly 3 stocks to go UP (Long) and 3 stocks to go DOWN (Short) during Regular Trading Hours (09:30 AM to 04:00 PM ET), evaluates directional hit rates and Long/Short spread alpha at market close, and continuously evolves its prompt strategies via an isolated weekly autoresearcher.

## 1. Candidate Universe & Extraction

Unlike static watchlists or unconstrained universe scans, candidate tickers are dynamically extracted from that morning's synthesized intelligence briefing (`apps/engine/tasks/newsletter_generator.py` open session) and pre-market gap scans:
* **Pool Size**: 15 to 30 active equities per session.
* **Extraction**: `extract_candidate_tickers(briefing_text)` extracts capitalized stock mentions (with regex filtering out macro acronyms like `CPI`, `FOMC`, and index ETFs `SPY`, `QQQ`).
* **Anchor Fallback**: Supplemented with high-liquidity large-cap anchors (`NVDA`, `TSM`, `AAPL`, `MSFT`, `AMZN`, `GOOGL`, `META`, `TSLA`, `AVGO`, `CRWV`, `ETR`, `CB`, `XLF`, `ABNB`) to ensure depth.

## 2. Multi-Model Arena & Deterministic Consensus

Three distinct frontier models compete in parallel under independent prompt lineages:
1. **DeepSeek Flash** (`deepseek-v4-flash`) — Instruct-based structured JSON extraction.
2. **MiniMax** (`MiniMax-M3`) — High-context reasoning LLM with JSON format output.
3. **GPT Luna** (`gpt-5.6-luna`) — OpenAI high-conviction decision model.

### Reciprocal Rank Fusion (RRF) with Leg Exclusivity

To generate the platform's official **Consensus Basket** without model hallucination or empty sets:
* **Score Accumulation**: For each direction (UP, DOWN), each model vote contributes:
  $$
  \text{Score}(t) = \sum_{m \in \text{models}} \left( \frac{1}{60 + \text{Rank}_m(t)} \times \frac{\text{Confidence}_m(t)}{100.0} \right)
  $$
* **Leg Exclusivity**: If a ticker receives votes in both UP and DOWN across models, it is assigned strictly to the direction with the higher aggregate score and disqualified from the opposing leg.
* **Tie-Breaking**: Sorted descending by `Score` $\to$ `Mean Confidence` $\to$ `Alphabetical Ticker`.
* **Sanitization Invariant**: The top 3 ranked tickers for UP and top 3 for DOWN are selected, guaranteeing exactly 6 unique stocks per consensus basket (`apps/engine/tasks/stock_picker.py`).

## 3. Two-Tier Relational Schema

To enforce [[concepts/zero-frontend-compute]] and CP-safe atomic transactions, data is persisted across two relational tables (`supabase/migrations/20261112000000_create_daily_stock_picks.sql`):

* **Parent Basket** (`daily_stock_baskets`):
  * `id` (UUID PK), `target_date`, `model_name` (`consensus`, `deepseek-v4-flash`, `MiniMax-M3`, `gpt-5.6-luna`).
  * Pre-materialized performance metrics: `directional_hit_rate`, `mean_long_return_pct`, `mean_short_return_pct`, `ls_spread_alpha_pct`, `excess_alpha_vs_spy_pct`, `benchmark_spy_return_pct`.
  * `status`: `pending` $\to$ `evaluated` or `cancelled`.
  * Unique constraint: `(target_date, model_name)`.
* **Granular Pick Items** (`daily_stock_picks`):
  * `basket_id` (FK referencing `daily_stock_baskets`), `ticker`, `direction` (`UP` / `DOWN`), `rank` (1..3), `confidence` (50..100%).
  * Execution columns: `open_price`, `close_price`, `stock_return_pct`, `position_return_pct` (`stock_return` for Long, `-stock_return` for Short), `is_hit`, `conviction_points`.
  * Unique constraints: `(target_date, model_name, ticker)` preventing duplicate picks within a basket, and `(target_date, model_name, direction, rank)`.
  * Invariant check constraint `chk_pick_evaluation_invariants` making illegal states unrepresentable (see [[concepts/state-machines]]).

## 4. Post-Market Close Evaluation

Scheduled at 17:00 ET (`apps/engine/tasks/evaluate_stock_picks.py`), the evaluator fetches Regular Trading Hours (09:30 to 16:00 ET) Open and Close prices:
* **Halt Defensive Guard**: If `open_price <= 0` or missing (e.g. LULD volatility halts), the pick is marked `status = 'cancelled'`, preventing zero-division crashes.
* **Return Metrics**:
  * $\text{Stock Return} = \frac{\text{Close} - \text{Open}}{\text{Open}} \times 100\%$
  * $\text{Position Return} = \text{Stock Return}$ for UP, $-\text{Stock Return}$ for DOWN.
  * $\text{L/S Spread Alpha} = \text{Mean}(\text{Long Returns}) - \text{Mean}(\text{Short Stock Returns})$.
  * $\text{Directional Hit Rate} = \frac{\text{Count}(\text{is\_hit})}{\text{Total Valid Picks}} \times 100\%$.

## 5. Weekly Autoresearch & Normalized Ratchet Hurdle

Every Sunday at 18:00 ET (`apps/engine/tasks/stock_picker_autoresearch.py`), each model track evaluates its rolling 5-session window against its historical baseline.

### Normalized Ratchet Hurdle Score
To eliminate dimension mismatch between percentage-point returns and hit rates, raw L/S Alpha is mapped into $[0, 100]$ centered at 50 ($10\text{ pts}$ per $1\%$ alpha):
$$
\text{Alpha}_{\text{norm}} = \text{clamp}(50.0 + (\text{LS\_Alpha\_pct} \times 10.0), 0.0, 100.0)
$$
$$
\text{Score} = 0.50 \times \text{Hit Rate} + 0.40 \times \text{Alpha}_{\text{norm}} + 0.10 \times \text{Conviction}_{\text{norm}}
$$

* **1-in-6 Stochastic Cold Start**: Independently rolled per model track (`random.randint(1, 6) == 1`). If triggered, prompt mutations reset "from 0" using default strategy rules (see [[concepts/stochastic-cold-start]]).
* **Prompt Section Splitting**: Frozen headers and JSON schema footers are strictly preserved via `split_stock_picker_prompt`, mutating only the analytical strategy body.
* **Promotion & Memory**: Variants that beat the baseline are promoted to `status = 'baseline'`, demoting prior active variants to `saved`. High-conviction takeaways are stored in `memories` with `memory_type = 'AUTORESEARCH_INSIGHT'`.

## 6. Pipeline Scheduling & Workflow Piggybacking

Enforcing Principle 14 (Workflow Consolidation):
* **Morning Run**: Piggybacked into `.github/workflows/daily-predictor.yml` under step `Run Daily Stock Picker Arena (3 Up, 3 Down)` at 9:17 AM ET.
* **Evening Evaluation**: Chained in `daily-predictor.yml` under step `Evaluate Daily Stock Picks` at 5:00 PM ET.
* **Sunday Autoresearch**: Triggered via scheduled cron `0 22 * * SUN` in `daily-predictor.yml` under step `Run Weekly Stock Picker Autoresearch`.

## 7. Web Dashboard Presentation

Surfaced as a first-class segmented tab in the Daily Predictions Arena (`apps/web/src/features/daily-predictions/components/DailyStockPicksTab.tsx`):
* **Model Filter Buttons**: Instant toggle between `⭐ Consensus`, `DeepSeek Flash`, `MiniMax-M3`, and `GPT-5.6 Luna`.
* **Two-Column Pick Showcase**: 3 UP (Long) cards with rank badges and green borders; 3 DOWN (Short) cards with red borders.
* **Performance Tiles**: Directional Hit Rate, Net L/S Spread Alpha, SPY Benchmark move, and Excess Alpha.
* **Historical Baskets Table**: Complete audited ledger of past sessions with right-aligned tabular numbers and zero floating tooltips (Principle 11).

## Related

- [[entities/daily-market-predictor]] — the SPY and TLT directional arenas
- [[entities/autoresearch]] — the platform auto-research framework
- [[concepts/multi-track-autoresearch]] — parallel isolated model lineages
- [[concepts/zero-frontend-compute]] — pre-materialization architecture
- [[concepts/stochastic-cold-start]] — 1-in-6 dice resets
- [[entities/cli]] — CLI commands `stock-picker`, `evaluate-stock-picks`, `stock-picker-autoresearch`
- [[entities/database]] — `daily_stock_baskets` and `daily_stock_picks` tables
- [[concepts/prompt-section-splitting]] — frozen header/mutable strategy/frozen footer prompt structure
