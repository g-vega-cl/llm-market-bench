---
tags: [anthropic, benchmark, source, research, fsi]
category: source
---

# Source: Anthropic Financial Services Repository

Synthesis of key architecture, domain skills, and tooling patterns from Anthropic's open-source repository ([`anthropics/financial-services`](https://github.com/anthropics/financial-services)).

## Repository Summary

The repository provides reference implementations of financial agents, vertical skill plugins, and Model Context Protocol (MCP) data connectors designed for enterprise Financial Services Industry (FSI) workflows.

### Core Structure

1. **Vertical Plugins**:
   - `financial-analysis`: Core modeling, Excel auditing, DCF, comps, LBO, 3-statement models, 11 enterprise MCP connectors.
   - `equity-research`: Earnings previews, morning notes, initiating coverage, thesis tracking, sector overviews.
   - `investment-banking`: CIMs, teasers, pitch decks, buyer lists, merger models, deal tracking.
   - `private-equity`: Sourcing, screening, diligence checklists, IC memos, portfolio monitoring.
   - `wealth-management`: Client reviews, financial plans, rebalancing, tax-loss harvesting.
   - `fund-admin`: General ledger reconciliation, break tracing, accruals, roll-forwards, variance commentary.

2. **Partner Plugins**:
   - `lseg`: Fixed income relative value, swap curve strategies, FX carry, options volatility surface analysis, macro rates monitoring.
   - `spglobal`: S&P Capital IQ tear sheets, earnings previews, funding digests.

3. **MCP Integrations (11 Providers)**:
   - Daloopa, Morningstar, S&P Global (Kensho), FactSet, Moody's, MT Newswires, Aiera, LSEG, PitchBook, Chronograph, Egnyte.

4. **Agent Templates & MS365 Add-in**:
   - Managed agent templates deploying multi-agent workflows with leaf-worker subagents and Microsoft 365 add-in deployment tooling.

## Key Algorithmic & Analytical Insights

- **Options Volatility Surface & Implied Move**: LSEG plugin chains `equity_vol_surface` (ATM vol, 25d risk reversal skew, 25d butterfly smile curvature) with realized volatility ($IV - RV$) to determine rich/cheap regimes and calculate implied standard deviation moves ($\sigma_{\text{ATM}} / \sqrt{252}$).
- **Falsifiable Thesis Tracking**: Requires explicit 3–5 pillars, target price, and a dedicated *Disconfirming Evidence Ledger* with conviction state transitions (`Confirmed`, `Weakened`, `Invalidated`).
- **3-Scenario Earnings Grids**: Bull / Base / Bear frameworks parameterized by sector-specific operational drivers (SaaS ARR/RPO, Industrials Book-to-Bill, Financials NIM) and consensus vs whisper deltas.
- **Yield Curve Macro Regimes**: Classifies interest rate environments into 4 regimes (Bull Flattener, Bear Steepener, Bull Steepener, Bear Flattener) to route asset allocation.
- **Root-Cause Variance Waterfall**: Decomposes performance misses into structured variance buckets rather than unstructured narrative.

## Related

- [[concepts/anthropic-fs-insights]] — Concrete implementation roadmap and tool-packaging strategy for llm-market-bench
- [[entities/tool-registry]] — Canonical tool registry
- [[entities/daily-market-predictor]] — Daily S&P 500 predictor
- [[entities/sector-predictor-arena]] — Sector prediction arena
