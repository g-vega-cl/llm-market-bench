---
tags: [portfolio, strategy, ui, system-portfolios]
category: entity
---

# Strategy Explainer

Permanently expanded strategy description card for system portfolios. Displays the investment thesis, methodology pillars, and key references for each system portfolio strategy.

## Behavior

- **Always expanded** — The detail panel with pillar descriptions is always visible. There is no collapse/expand toggle or button.
- Previously, this component was collapsible; it was changed to permanently expanded to improve information accessibility on mobile and reduce interaction friction.

## Usage

Used in portfolio detail pages to explain the rationale behind each system portfolio strategy:

- `sys-smid-quality-compounder` — Small/Mid-Cap Quality Compounder (Asness et al.)
- `sys-sector-ls-consensus` — Sector Long/Short Consensus
- `sys-frontier-tech-supercycle` — Frontier Tech Supercycle (small-cap guardrails)
- `sys-daily-spy-close-target` — Daily SPY Close Price Target
- `sys-daily-spy-target` — Daily SPY Open-to-Close Target

See `StrategyExplainerConfig` definitions in the component source for the full list.

## Rendering

Each explainer renders:
- Emoji + title + badge + subtitle header (always visible)
- Grid of pillar cards (always visible), each containing a title and description
- Pillar grid responds to configurable column layout (`gridColsClass`, default `grid-cols-1 md:grid-cols-3`)

## Related

- [[entities/smid-compounder]] — System portfolio using this explainer
- [[entities/frontier-tech-portfolio]] — System portfolio using this explainer
- [[entities/sector-trading]] — Sector L/S system portfolio
- [[concepts/system-portfolios]] — Mechanical and rule-based systematic trading strategies
- [[concepts/zero-frontend-compute]] — All heavy computation pre-materialized; this component is pure presentational
