# PRODUCT.md

## Core promise: show the receipts

Most finance products sell black-box hype, cherry-picked backtests, or unverifiable claims. Benchify flips that dynamic. A skeptical visitor should look at a leaderboard or strategy page, think "this cannot be real", and immediately find every piece of proof right on the page:

1. Exact point-in-time inputs, prompts, and tool-call traces for every model turn.
2. Full trade ledgers, cash balances, slippage assumptions, and losing streaks alongside winners.
3. External Alpaca paper-order attestations and reproducible evaluation formulas so results cannot be retroactively doctored.
4. Clear, zero-friction entry points ("Start building", starter recipes, investing style diagnostic) so a convinced visitor can test their own thesis right away.

## Audience and editorial voice

- **Reader mindset**: Quant-curious engineers, skeptical retail investors, and AI builders who spot marketing fluff immediately.
- **Voice**: Plain, concrete, opinionated, and backed by numbers. State exact returns, drawdowns, sample sizes, and failure modes. Apply `.agents/skills/unslop/SKILL.md` to all copy.
- **Design inspirations**:
  - `pudding.cool` for visual data storytelling where evidence leads.
  - `posthog.com` for high-density, tactile, developer-honest product craft.
  - `ollivere.co` and `coldemailers.com` for sharp hierarchy and personality.
  - `bettermotherfuckingwebsite.com` for speed, legibility, and zero layout bloat.

## Product guardrails for UI and feature work

- **Pair with Voxel design spec**: `PRODUCT.md` defines product intent and proof density; `.agents/rules/design-spec.md` defines the Matcha & Cedar / Cheddar Voxel visual grammar. Read both before changing any route in `apps/web`.
- **Primary action front and center**: On action routes (`/build`, `/personality`, `/chat`), keep the active input and primary CTA at the top of the 360px mobile viewport above history or explainers.
- **Proof in-flow, never hidden**: Render score breakdowns, trade reasons, and point inspections in-flow inside recessed `.voxel-trough` slots rather than hiding evidence behind banned tooltips, modals, or accordions.
- **Disclose coverage and limits**: State asset coverage (such as US equities vs international tickers), slippage, and pending-settlement states plainly near the numbers they qualify.
