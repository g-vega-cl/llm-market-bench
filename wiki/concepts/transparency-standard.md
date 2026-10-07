---
tags: [transparency, audit, scoring, tool-tracking]
category: concept
---

# 3-Domain Transparency Standard (Benchify Standard)

A unified frontend transparency layer enforced across all three prediction domains — portfolio autoresearch, daily SPY predictor, and weekly sector predictor — ensuring that every score, tool selection, reasoning block, and prompt mutation is fully auditable from a single page.

## Five Pillars

1. **Score & Math Audit** — Formula substitution bar, pillar metric tiles, and baseline delta display. Implemented via `ScoreBreakdown.tsx` and `ScoreCalculation.tsx` for portfolio trading (rendering the Unified Risk-Adjusted Z-Score in $\sigma$ units, see [[concepts/risk-adjusted-z-score]]), `DailyScoreBreakdown.tsx` for daily SPY predictions (4-pillar score), and `SectorScoreBreakdown.tsx` for weekly sector calls (multi-pillar score).
2. **Cognitive Toolbox** — Dynamic registry inspection (`CognitiveToolboxCard.tsx`) showing enabled/total tools badges, parent variant deltas, and individual capability tags. Uses the canonical tool registry at `packages/config/tools.json`.
3. **Modular Reasoning Blocks** — Active thematic prompt blocks displayed via `PromptBlocksCard.tsx` with parent deltas. The known block catalog is defined inline.
4. **Meta-Researcher Rationale & Conviction** — Unified `ResearchRationaleCard.tsx` showing change description, hypothesis, analytical reasoning, confidence gauge (0–100%), and durable track memory insight.
5. **Segmented Prompt Inspector** — Triple-band visualization via `splitPromptSections` (frozen header, mutable strategies, frozen output schema) making immediate the boundary between system constraints and auto-researcher mutations.

## Domains

| Domain | Route | Score Component | Score Formula & Units |
|--------|-------|-----------------|----------------------|
| Portfolio Autoresearch | `/autoresearch` | `ScoreBreakdown`, `ScoreCalculation`, `DailyScoreDisplay` | Unified Risk-Adjusted Z-Score ($\sigma$, [[concepts/risk-adjusted-z-score]]) |
| Daily SPY Predictor | `/daily-predictions` | `DailyScoreBreakdown` | 4-Pillar Composite (Points, [[entities/daily-score-breakdown]]) |
| Weekly Sector Predictor | `/ai-predictions` | `SectorScoreBreakdown` | Multi-Pillar Percentile + Alpha Bonus − Brier (Points) |

## Related

- [[concepts/risk-adjusted-z-score]]
- [[concepts/modular-prompt-blocks]]
- [[concepts/zero-frontend-compute]]
- [[entities/autoresearch-arena]]
- [[entities/daily-market-predictor]]
- [[entities/sector-predictor-arena]]
