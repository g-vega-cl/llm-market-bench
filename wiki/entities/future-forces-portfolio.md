---
tags: [portfolio, system, future-forces, catalysts, thematic, luna, alpaca]
category: entity
---

# Multi-Horizon Thematic Forces & Catalysts Portfolio (`sys-future-forces`)

The **Multi-Horizon Thematic Forces Portfolio** (`sys-future-forces`) is an automated, institutional-grade thematic strategy designed to capture unpriced, medium-to-long term structural forces across a **2 to 24 month horizon**.

Unlike high-frequency intraday trading or weekly sector momentum that react to market microstructure noise, this portfolio identifies and accumulates high-conviction equity expressions before consensus Wall Street earnings models price in the underlying inflection.

---

## Investment Philosophy & The 7 Canonical Archetypes

Candidate forces must qualify under one of seven distinct market phenomena:

1. **Geopolitical & Energy Chokepoints**: Maritime transit friction and regional escalations that disrupt global commodity flows (e.g., Persian Gulf / Strait of Hormuz tensions driving tanker charter rates (`FRO`, `STNG`) and domestic Permian shale arbitrage (`FANG`)).
2. **Government Priorities & Industrial Policy**: Non-discretionary statutory appropriations and defense transformations (e.g., Pentagon Replicator initiative for autonomous attritable drone systems (`AVAV`, `KTOS`) or naval shipbuilding backlogs (`HII`)).
3. **The Sleeping Giant (Narrative Disconnect)**: Franchise compounders trading at trough valuation multiples due to transient PR embarrassment or exaggerated disruption fear (e.g., Alphabet `GOOGL` in early 2024 at ~18x forward P/E despite TPU and DeepMind supremacy).
4. **The Latent Distribution Turn-On**: Massive R&D and open-source models perceived as unprofitable cash burn until an incumbent activates its captive distribution layer (e.g., Meta `META` with Llama, Advantage+ AI ad conversion, and AI agent integration).
5. **The Inevitable Attack Surface Toll Road**: Technological revolutions that exponentially expand corporate risk and compliance mandates (e.g., autonomous AI coding agents expanding enterprise software attack surfaces 10x, making real-time telemetry non-discretionary (`CRWD`, `PANW`, `NET`)).
6. **The Clinical-to-Cultural S-Curve TAM Explosion**: Breakthrough treatments that transition from narrow clinical indications to viral consumer adoption and multi-year supply shortages (e.g., GLP-1s with `NVO` and `LLY`).
7. **Fixed Mega-Events & Contract Deadlines**: Discrete, scheduled world events driving localized economic squeezes (e.g., Airbnb `ABNB` and Booking `BKNG` for the 2026 FIFA World Cup in North America).

---

## Execution Guardrails & Risk Management

### 1. The 2-Month Floor (60 to 720 Days)
The strategy enforces a minimum 60-day horizon floor to eliminate intraday and weekly headline whipsaws. Positions are given adequate runway for real-world supply contracts, quarterly earnings beats, and legislative markups to manifest in reported fundamentals.

### 2. Adversarial Sentinel Audit (OpenAI Luna)
- **Model**: OpenAI Luna (`gpt-5.6-luna`) configured with `reasoning_effort="medium"`.
- **Sentinel Role**: Daily post-market scan comparing active holdings against breaking real-world news and regulatory filings.
- **Thesis Death & Invalidation**: If explicit invalidation criteria are triggered (such as a demilitarization accord, loss of major contract, or host city municipal short-term rental bans), the sentinel marks the force as `invalidated` and triggers immediate liquidation.

### 3. Market Hours Execution & Alpaca Auditability (Zero Backfilling)
- **No Out-of-Market Fills**: Liquidations and buys execute **strictly during regular market hours (09:30–16:00 ET)**. If an invalidation occurs when markets are closed, the force status is set to `pending_liquidation` and executes at the next market open.
- **Alpaca Paper Broker Mirroring**: Every order executes through `Portfolio.execute_trade` and mirrors as a limit order to the Alpaca paper broker API. All trades are live, auditable, and timestamped in real time with 5 bps slippage, with zero retroactive backfilling.

---

## Architecture & Codebase Map

- **Analytics Engine**: [`apps/engine/analytics/future_forces.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/analytics/future_forces.py) (`evaluate_future_force`, `audit_force_invalidation`, deterministic guardrails).
- **Execution Engine**: [`apps/engine/execution/future_forces.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/execution/future_forces.py) (`compute_future_forces_rebalance_orders`, `execute_force_invalidation`).
- **Scheduled Task**: [`apps/engine/tasks/future_forces_task.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tasks/future_forces_task.py) (`--audit-sentinel`, `--rebalance`, `--dry-run`).
- **Tools**:
  - `get_future_forces`: Deterministic query for active forces across horizons and archetypes.
  - `research_future_force`: Adversarial research tool using `gpt-5.6-luna` with thinking.
- **Web UI**:
  - [`FutureForceCards.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/portfolios/components/FutureForceCards.tsx): Visual cards with countdowns, invalidation alerts, and live position PnL.
  - [`StrategyExplainer.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/portfolios/components/StrategyExplainer.tsx): 4-pillar institutional strategy breakdown.
- **Database Schema**: `public.future_forces` table in `supabase/migrations/20260925100000_create_future_forces.sql`.

---

## Related
- [[concepts/system-portfolios]] — Mechanical System Portfolio catalog
- [[entities/frontier-tech-portfolio]] — Small-Cap Frontier Technology Supercycle portfolio
- [[entities/historical-analogs]] — Historical market analog precedent engine
