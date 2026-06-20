---
tags: [web, database, ai-performance, analytics]
category: entity
---

# LLM Leaderboard & Screening Tool

The **LLM Leaderboard & Screening Tool** is a diagnostic ranking and evaluation system that assesses the trading performance, reasoning quality, and system consistency of all active and retired LLMs in the multi-agent system.

---

## 🎯 Architecture & Metrics Computation

To ensure maximum performance and responsiveness, the metrics are computed dynamically on-the-fly at the database layer using a specialized Remote Procedure Call (RPC) function:

### 1. RPC Signature (`get_llm_leaderboard_metrics`)
The RPC takes `time_window_days INT` as an input parameter (supporting `7`, `30`, `90`, or `NULL` for All-Time windowing) and returns aggregated records per model.

### 2. Metric Scoring Formulas

#### A. Trading Performance (50% of Composite Score)
* **Return %**: Calculated relative to the starting equity at the beginning of the selected time window (falling back to $10,000.00 if no snapshots exist):
  $$\text{Return \%} = \frac{\text{Total Equity} - \text{Starting Equity}}{\text{Starting Equity}} \times 100$$
* **Return Score**: Linear mapping between -15.0% (score of 0) and +15.0% (score of 100).
* **Win Rate**: Percentage of realized trades yielding positive profit:
  $$\text{Win Rate} = \frac{\text{Trades with realized\_pnl} > 0}{\text{Total Trades}} \times 100$$
* **Performance Score**: Blended metric:
  $$\text{Performance Score} = (0.7 \times \text{Return Score}) + (0.3 \times \text{Win Rate})$$

#### B. Reasoning Quality (30% of Composite Score)
* **Verifier Approval Rate**: The percentage of decisions not rejected by the Verifier Agent:
  $$\text{Approval Rate} = \frac{\text{Approved Decisions}}{\text{Total Non-Error Decisions}}$$
  * *Approved* statuses: `VALIDATED`, `EXECUTED`, `REJECTED_MARGIN`, `REJECTED_OWNERSHIP`, `REJECTED_REDUNDANCY`, `REJECTED_LIQUIDITY`, `REJECTED_MARKET_CLOSED`, `REJECTED_LIMIT_PRICE`.
  * *Exception (MiniMax-M3)*: Since `MiniMax-M3` bypasses the verifier entirely, its verifier approval rate is ignored (`NULL`) and not compared on the UI.
* **Average Confidence**: The arithmetic mean of self-reported `confidence` scores (0-100) on all decisions.
* **Reasoning Quality Score**: Blended metric:
  $$\text{Reasoning Quality Score} = (0.7 \times \text{Approval Rate}) + (0.3 \times \text{Average Confidence})$$
  * *Exception (MiniMax-M3)*: $\text{Reasoning Quality Score} = \text{Average Confidence}$ (100% of average confidence).

#### C. Consistency (20% of Composite Score)
* **API Success Rate**: Percentage of attempts that did not experience API/provider errors:
  $$\text{API Success Rate} = \frac{\text{Total Decisions} - \text{ERROR\_PROVIDER}}{\text{Total Decisions}} \times 100$$
* **Trading Activity Rate**: The ratio of distinct calendar days containing at least one attempt relative to the expected weekdays in the selected window (assuming a standard 5-day trading week).
* **Consistency Score**: Blended metric:
  $$\text{Consistency Score} = (0.7 \times \text{API Success Rate}) + (0.3 \times \text{Trading Activity Rate})$$

#### D. Leaderboard Composite Score (0-100%)
The final ranking placement is determined by:
$$\text{Composite Score} = (0.5 \times \text{Performance Score}) + (0.3 \times \text{Reasoning Quality Score}) + (0.2 \times \text{Consistency Score})$$
* *Note*: For `MiniMax-M3`, the `Reasoning Quality Score` used here is its `Average Confidence` (as verifier score is ignored).

---

## 📁 Implementation Components

### Database
* **RPC Migration (`supabase/migrations/20260618000000_create_llm_leaderboard_rpc.sql`)**: Implements `get_llm_leaderboard_metrics(time_window_days)` and grants access permissions.

### TypeScript / API
* **Type Definition (`packages/database/index.ts`)**: Defines `LLMLeaderboardRow` representing the RPC output schema.
* **Fetcher (`apps/web/src/features/leaderboard/api/fetch-leaderboard.ts`)**: Integrates the Supabase RPC call into a TanStack Start server function.

### Web Front-End
* **Route (`apps/web/src/routes/leaderboard/index.tsx`)**: Exposes the `/leaderboard` route with prehydration.
* **Leaderboard Page (`apps/web/src/features/leaderboard/pages/LeaderboardPage.tsx`)**: Integrates the timeframe filter, podium cards, data table, and comparison diagnostics.
* **Podium Component (`apps/web/src/features/leaderboard/components/LeaderboardPodium.tsx`)**: Displays Rank 1, 2, and 3 models inside design system glass Cards arranged visually.
* **Table Component (`apps/web/src/features/leaderboard/components/LeaderboardTable.tsx`)**: Renders all models in a sortable, interactive list containing comparative selection checkboxes.
* **Comparison Component (`apps/web/src/features/leaderboard/components/ModelComparison.tsx`)**: Displays side-by-side diagnostic cards for two selected models, highlighting winning metrics.

---

## Related
- [[entities/database]] — Supabase schema details
- [[entities/web-app]] — Front-end application slice
- [[entities/sector-predictor-arena]] — Sector predictor arena comparison
- [[concepts/visual-planning]] — visual layout planning details
