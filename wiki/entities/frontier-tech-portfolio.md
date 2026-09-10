---
tags: [portfolio, system, frontier-tech, small-cap, supercycles]
category: entity
---

# Frontier Technology Supercycle Portfolio (`sys-frontier-tech`)

The **Frontier Technology Supercycle Portfolio** is an automated investment strategy designed to catch long-term technological super cycles in their pre-explosion gestation phase (similar to pre-2022 LLMs, pre-2017 crypto, or pre-2021 GLP-1 therapeutics).

Rather than purchasing large-cap tech incumbents after a technology has entered mainstream media hype, the strategy screens and accumulates public small-cap pure-play equities and critical bottleneck suppliers.

---

## Architecture & Investment Philosophy

### 1. 5-Point Supercycle Gestation Rubric
A candidate frontier theme must satisfy at least 3 of 5 qualitative and quantitative inflection criteria:
1. **Cost Curve Deflation / Scaling Laws**: Verifiable exponential decline in per-unit cost (for example, cost per FLOP, per base pair synthesized, or per gigabit optical link) or rapid performance doubling.
2. **Identifiable Pure-Play Enablers**: Tradable public equities focused primarily on the bottleneck hardware, materials, or tooling needed for the technology to function.
3. **Talent & Mindshare Migration**: Accelerating scientific pre-prints (arXiv), developer activity (GitHub), or academic citations.
4. **Regulatory or Government Catalysts**: Targeted government mandates, subsidies, defense research contracts, or fast-track regulatory clearances.
5. **Early Enterprise Pilot Validation**: Initial non-trivial commercial pilots, production-grade partnerships, or enterprise purchase agreements.

### 2. Small-Cap Exchange & Liquidity Filters
Candidate pure plays must pass four quantitative sanity checks to prevent illiquid penny stock risk:
- **Exchanges**: Major US exchanges only (NASDAQ, NYSE, AMEX). OTC and pink sheets are excluded.
- **Market Cap**: Minimum $100M threshold.
- **Liquidity**: Minimum $1M average daily dollar trading volume.

### 3. Anti-Overpaying & Solvency Guardrails
To avoid buying the top of retail hype cycles and ensure speculative pure plays survive the gestation period:
- **Solvency Runway**: Companies must possess at least 18 months of cash runway (`Cash / Annual Operating Expenses >= 1.5`), unless already profitable.
- **Anti-Parabolic Pump Filter**: The engine rejects any stock trading higher than 150% of its 200-day simple moving average (`price / ma200 <= 1.50`).

### 4. Venture Power-Law Position Sizing
- **Allocation**: Sized between 2% and 4% (default 3.0%) of total portfolio equity per qualifying pure play across 5 to 8 themes.
- **Retention**: Holdings ride through multi-year price volatility without tight stop losses. As Bessembinder (2018) documented, extreme winners drive net market returns.
- **Exit Discipline**: Positions are liquidated only upon fundamental thesis death (insolvency, exchange delisting, or invalidation of the core technological thesis).

---

## Implementation Components

- **Analytics (`apps/engine/analytics/frontier_tech.py`)**: Implements `evaluate_supercycle_rubric`, `evaluate_stock_guardrails`, and `evaluate_thesis_death`.
- **Execution (`apps/engine/execution/frontier_tech.py`)**: Computes rebalance orders, retentions, and liquidations for `sys-frontier-tech`.
- **Scheduled Task (`apps/engine/tasks/frontier_tech_task.py`)**: Runs monthly via GitHub Actions (`.github/workflows/frontier-tech.yml`) on the 1st of every month at 14:00 UTC. Also exposes CLI flags (`--mode`, `--dry-run`, `--target-weight`).
- **Database Schema (`supabase/migrations/20260910140000_create_frontier_themes.sql`)**: Stores active themes, pure-play tickers, and rubric scores in `frontier_themes`.
- **Web Interface (`apps/web`)** :
  - `FrontierThemeCards.tsx`: Renders visual theme cards detailing thesis, catalysts, constituent tickers, and weight.
  - `PositionsTable.tsx`: Displays theme tag chips next to constituent holdings.
  - `StrategyExplainer.tsx`: Explains the 5-point rubric and power-law sizing pillars.

---

## Related
- [[concepts/system-portfolios]] — mechanical system portfolio strategies
- [[entities/sector-predictor-arena]] — weekly sector prediction arena
- [[entities/database]] — Supabase database schema
