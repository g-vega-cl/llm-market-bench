---
tags: [web, database, ai-performance, analytics]
category: entity
---

# LLM Leaderboard & Screening Tool

The **Unified Leaderboard & Screening Tool** ranks active LLMs, active systematic portfolios (`sys-*`), and all public non-archived user bots (`strategy_recipes`) across `7 Days`, `30 Days`, `90 Days`, and `All-Time` windows.

---

## 🎯 Architecture & Metrics Computation

User-bot window metrics (`7`, `30`, `90`, `0` for All-Time) are pre-materialized by `apps/engine/recipes/public_stats.py` into `public.user_bot_leaderboard_stats` (`supabase/migrations/20261125010000_create_user_bot_leaderboard_stats.sql`). Read requests call the `STABLE` `GET`-routable RPCs (`get_leaderboard_page` and `get_llm_leaderboard_metrics`, redefined in `supabase/migrations/20261127120100_leaderboard_up_days_rpc.sql`) via PostgREST HTTP `GET`, keeping reads fast on the MiniPC read replica with zero JSONB unpacking and zero frontend compute ([[concepts/zero-frontend-compute]]).

### 1. Unified Competitor Population
* **Active LLMs**: Enforced in SQL against the active models in `packages/config/models.json` (`gpt-6-luna`, `claude-haiku-5-5`, `gemini-3.5-flash-lite`, `deepseek-flash`, `MiniMax-M3.1-Flash`).
* **System Portfolios (`sys-*`)**: Active mechanical strategies in `portfolios`, excluding `ARCHIVED_PORTFOLIO_OWNER_IDS`.
* **User Bots**: All public, non-archived, non-template, single-stage `strategy_recipes` (`is_public = TRUE AND archived_at IS NULL AND is_template = FALSE`). `strategy_recipes.is_public` defaults to `TRUE` so every user bot is publicly visible and inspectable.

### 2. Metric Scoring Formulas

#### A. Trading Performance (50% LLM / 70% System & User Bot)
* **Return %**: Calculated relative to starting equity at the beginning of the selected window (falling back to `$10,000.00` when the portfolio/bot launched after window start so day-1 returns are preserved).
* **Return Score**: Linear mapping between `-15.0%` (`0`) and `+15.0%` (`100`).
* **Win Rate**:
  * For portfolios: combined win rate across closed exit trades (`signal IN ('SELL', 'COVER') AND realized_pnl IS NOT NULL`) and currently held open positions (longs in `position_pnl` plus open `SHORT` lots in `trades`), excluding entry `BUY` rows from the denominator; `NULL` (`—` in UI; neutral `50.0` in score) when neither exists.
  * For user bots: pre-materialized combined win rate across closed `paper_trades` (`pnl_net > 0`) in the window and open `paper_positions` (`unrealized_pnl_net > 0`), or `NULL` (`—`) when neither exists.
* **Performance Score**: `(0.7 * Return Score) + (0.3 * Effective Win Rate)`.

#### B. Reasoning Quality (30% LLM only)
* **Conviction Score**: The normalised [[concepts/conviction-points]] term computed from evaluated `daily_predictions` rows over the window (LLMs only; `NULL` / `'—'` for system portfolios and user bots). Verifier approval scoring has been removed (no active verifier).
* **Average Confidence**: Arithmetic mean of self-reported `confidence` scores on `decisions` (informational only; `NULL` / `'—'` for non-LLMs).

#### C. Consistency (20% LLM / 30% System & User Bot)
* **Laplace-Smoothed Daily Return Consistency**: `((pos_days + 2) * 100) / (active_return_days + 4)` over active return sessions in the window where closing equity changed vs. the prior session (`portfolio_performance` or daily-collapsed `paper_equity_curve`), preventing single-day `100%` cliffs and defaulting to `50.0%` when `active_return_days = 0`.
* **Surfaced as Up Days**: the RPCs return `up_days` / `active_days` so `/leaderboard` can show `9/10 · 78.6%` with a one-line in-flow legend instead of a bare percentage (`supabase/migrations/20261127120100_leaderboard_up_days_rpc.sql`).

#### D. Composite Score (0–100%)
* **LLMs**: `(0.5 * Performance) + (0.3 * Conviction) + (0.2 * Consistency)`
* **System Portfolios & User Bots**: `(0.7 * Performance) + (0.3 * Consistency)` (no frozen `50.0` conviction dilution)
* **Idle Bots (zero activity)**: `0.00%` so unrun draft bots sort below active strategies.

---

## 📁 Implementation Components

### Database Migrations
* `supabase/migrations/20261125000000_unified_leaderboard_and_public_bots.sql` — Makes all non-archived user bots public by default, adds safe ISO date parser `public._safe_iso_date(TEXT)`, updates `get_llm_leaderboard_metrics` to remove verifier scoring, fix win_rate/consistency, and include sys portfolios + user bots.
* `supabase/migrations/20261125010000_create_user_bot_leaderboard_stats.sql` — Creates `public.user_bot_leaderboard_stats` with RLS/grants and one-time backfill for existing public non-archived single-stage user bots (7d, 30d, 90d, 0=All-Time windows).
* `supabase/migrations/20261125020000_materialize_leaderboard_rpc.sql` — Adds `decisions` indexes, updates `get_llm_leaderboard_metrics` to read pre-materialized `user_bot_leaderboard_stats`, includes open SHORT lots in open positions, aligns `total_trades` to closed round-trip exits, returns NULL conviction/confidence for non-LLMs, adds `get_leaderboard_page` (STABLE, GET-routable) for server-side category filtering, sorting, 10-row pagination, counts, and Top 3 podium.
* `supabase/migrations/20261127120000_leaderboard_up_days_columns.sql` — Adds `up_days` / `active_days` to `user_bot_leaderboard_stats` and backfills them from the paper equity curves.
* `supabase/migrations/20261127120100_leaderboard_up_days_rpc.sql` — Returns `up_days` / `active_days` from both leaderboard RPCs so the UI can show the counts behind the smoothed consistency rate.

### Engine Materializer (`apps/engine/recipes/public_stats.py`)
* `build_bot_leaderboard_window_rows` — Computes pre-materialized 7d/30d/90d/All-Time rows for one public user bot from `paper_cash`, `paper_positions`, `paper_trades`, `paper_equity_curve`.
* `refresh_user_bot_leaderboard_stats` — Fetches all public non-archived single-stage user bots (paginated), builds window rows, upserts into `user_bot_leaderboard_stats` on `(recipe_id, time_window_days)`.
* Called from `refresh_public_stats` after recipe stats refresh.

### Types (`packages/database/index.ts`)
* `LeaderboardEntityType = 'llm' | 'system' | 'user_bot'`
* `LLMLeaderboardRow` — adds `display_name`, `entity_type`, `portfolio_id`, `recipe_id`, `is_live`, `rank`; makes `win_rate`, `average_confidence`, `conviction_score`, `reasoning_quality_score` nullable.
* `LeaderboardCategoryCounts` — `{ all, llm, system, user_bot }`
* `LeaderboardPagePayload` — `{ rows, podium, totalCount, counts }`

### Fetcher (`apps/web/src/features/leaderboard/api/fetch-leaderboard.ts`)
* `fetchLeaderboardPage` — calls STABLE `get_leaderboard_page` RPC via `{ get: true }` with params: `timeWindowDays`, `category`, `sortBy`, `sortDir`, `page`, `pageSize`. Returns `LeaderboardPagePayload`.
* `fetchLeaderboard` — calls STABLE `get_llm_leaderboard_metrics` via `{ get: true }` for backward compatibility (homepage barometer).

### Route (`apps/web/src/routes/leaderboard/index.tsx`)
* Prehydrates page 1 (`pageSize = 10`) plus `resolveAtmospherePhase(new Date(), 'market-et')` via `Promise.all`.

### Page (`apps/web/src/features/leaderboard/pages/LeaderboardPage.tsx`)
* Renders inside `SceneStage` (`backdropMode="page"`) with `CedarRidgeBackdrop`, `SceneHudControls`.
* Category filter tabs: **All**, **LLMs**, **System**, **User Bots** (with counts from RPC).
* Timeframe switcher: 7d, 30d, 60d, 90d, All.
* Top 3 podium (`LeaderboardPodium`) with athletic 2nd/1st/3rd visual order.
* Server-paginated table (`LeaderboardTable`) — max 10 per page, sortable columns (Score, Return, Win Rate, Up Days), category-aware pagination; the Up Days cell renders `up/active · smoothed %`.
* Side-by-side comparison (`ModelComparison`) for up to 2 selected competitors.
* Living backdrop with atmosphere/motion HUD controls.

---

## Related
* [[entities/database]] — Supabase schema details
* [[entities/web-app]] — Front-end application slice
* [[concepts/living-scene-backdrops]] — `SceneStage` + `CedarRidgeBackdrop` architecture
* [[concepts/system-portfolios]] — Mechanical `sys-*` portfolios
* [[entities/design-system]] — Voxel primitives and table alignment rules
* [[concepts/zero-frontend-compute]] — Pre-materialization architecture
* [[concepts/conviction-points]] — Calibrated confidence term
* [[entities/recipe-studio]] — User bots source (`strategy_recipes`)
