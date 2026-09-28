---
tags: [autoresearch, daily-score, pending, settlement, web, zero-defaults]
category: concept
---

# Pending Settlement State

When an autoresearch experiment is still **active** but no trading session has
closed yet, the daily score cannot be computed — there are no realized actual
returns to evaluate against. Rather than showing placeholder estimates, the
dashboard enters a **pending** state that explicitly surfaces "waiting for the
first close" instead of fabricating numbers.

## The `isPending` Flag

`calculateDailyMetrics` (in `apps/web/src/features/autoresearch/components/daily-score/daily-score-math.ts`)
returns `isPending: true` when **all** of the following hold:

- the experiment is active (`isActive`), and
- there are no per-portfolio actual returns, and
- there is no actual SPY return, and
- the metrics row has no explicit `portfolio_return_pct`, and
- the metrics row has no explicit `score`

When `isPending` is set, every derived figure — portfolio return, SPY return,
do-nothing return, opportunity cost, max drawdown, excess return, drawdown
penalty, and daily score — is returned as `0`. This keeps the math honest:
a genuinely unknown result is never replaced by an estimated default.

## Zero-Default Fallbacks

All fallback constants in the daily-score math are `0`. There are no
active-state placeholder values anywhere in the pipeline:

| Function | Fallback |
|----------|----------|
| `getPortfolioReturn` | `0` |
| `getSpyReturn` | `0` |
| `getDoNothingReturn` | `0` |
| `bondReturn` | `0` |
| `maxDrawdown` | `0` |

A missing value means "we do not know yet", and the UI renders that as pending
rather than as a misleading non-zero estimate.

## UI Representation

The `DailyScoreDisplay` tree threads `isPending` down to every score surface:

- **`DailyScoreOverview`** shows a `Day 1 In Progress (First Close 4:00 PM ET)`
  badge alongside the `LIVE TRACKING` indicator, and replaces the running score,
  excess return, risk-free excess, and drawdown penalty with a pulsing
  `Pending` / `Pending EOD Close` label.
- **`DailyAuditLedger`** replaces the portfolio- and do-nothing return details
  with a note that returns "will accumulate upon daily market closing settlement
  (4:00 PM ET)".
- **`DailyProgressionGrid`** marks the current checkpoint as `isInProgress` —
  rendered with an amber card and a `Pending` / `In Progress` body — while future
  days remain disabled and past days show their computed score.

## Track-Based Actuals Fetching

`useActualReturns` accepts the experiment's `track_id` and, when no constituent
portfolio IDs are available yet, falls back to resolving owner IDs from the
`AUTORESEARCH_TRACKS` map in `@repo/config/models.json`. This lets the pending
week still attribute returns to the correct track once data lands, and keeps the
component wired to the right portfolios even before the first close.

## Related

- [[entities/daily-score-breakdown]]
- [[entities/autoresearch-arena]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/auditability]]
