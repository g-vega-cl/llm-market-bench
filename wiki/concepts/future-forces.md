---
tags: [thematic, catalysts, horizons, geopolitics, luna, forces]
category: concept
---

# Multi-Horizon Future Forces & Asymmetric Catalysts

The concept of **Future Forces** defines an investment framework designed to bridge the temporal gap between short-term noise and long-term venture investing.

---

## The Temporal Continuum

Financial markets operate on distinct information reflection cycles:

```text
┌─────────────────┬──────────────────┬────────────────────────────────────────────────────────┐
│ Horizon         │ Benchify Vehicle │ Primary Signal Driver                                  │
├─────────────────┼──────────────────┼────────────────────────────────────────────────────────┤
│ Intraday        │ sys-daily-spy    │ 09:30-16:00 ET order flow & price tape momentum        │
│ Weekly (7d)     │ sys-sector-ls    │ Relative sector rotation & macro momentum              │
│ Monthly (30d)   │ sys-sector-30d   │ Intermediate business cycle shifts                     │
│ 2 to 24 Months  │ sys-future-forces│ Unpriced catalysts, geopolitics, government priorities │
│ Multi-Year      │ sys-frontier-tech│ Small-cap pre-explosion technology gestation           │
└─────────────────┴──────────────────┴────────────────────────────────────────────────────────┘
```

---

## The Anatomy of a Future Force

A viable Future Force requires four structural pillars:

1. **Unappreciated Causal Thesis**: The market is mispricing or ignoring an imminent inflection due to consensus anchoring, cognitive bias, or transient headline distraction.
2. **Defined Milestone Catalyst**: A concrete real-world trigger (statutory procurement award, tournament kickoff, FDA expansion, earnings productization print) that forces market consensus to re-rate the asset.
3. **Explicit Transmission Mechanism**: A verifiable financial chain showing how the external force converts into GAAP earnings, gross margin expansion, or multiple re-rating.
4. **Falsifiable Thesis Invalidation Trigger**: An explicit, testable event or data point that immediately proves the hypothesis wrong, removing emotional hope from risk management.

---

## Tooling & Agent Access

Autonomous agents and analysts access and evaluate future forces via two dedicated pull tools registered in `packages/config/tools.json`:

1. `get_future_forces`:
   - **Purpose**: Deterministic retrieval of active multi-horizon market forces (2 to 24 months), catalyst milestones, candidate beneficiary tickers, and explicit falsification triggers from the PostgreSQL `future_forces` registry (falling back to vetted baselines).
   - **Parameters**: `archetype` (optional filter: `geopolitical_chokepoint`, `mega_event`, `government_agenda`, `sleeping_giant`), `max_horizon_months` (default: 24), `limit` (default: 5).
   - **Returns**: Structured markdown summary of active forces, target dates, transmission chains, and invalidation rules.

2. `research_future_force`:
   - **Purpose**: Conducts deep-dive adversarial stress-testing of candidate theses, forward catalysts, and falsification criteria using OpenAI Luna with extended thinking.
   - **Parameters**: `force_title` (required), `archetype` (required), `thesis` (required), `catalyst_event` (required), `invalidation_triggers` (required), `transmission_mechanism` (required), `tickers` (optional list), `horizon_months` (default: 3).
   - **Returns**: Adversarial red-team rubric audit including priced-in expectation assessment, falsification clarity score (1-5), and audited conviction rating.

---

## Related
- [[entities/future-forces-portfolio]] — System portfolio implementation (`sys-future-forces`)
- [[concepts/system-portfolios]] — Overview of all mechanical execution strategies
- [[concepts/thematic-rotation]] — The adjacent trade pattern and intra-cycle rotations
