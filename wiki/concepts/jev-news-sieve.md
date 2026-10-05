---
tags: [concept, jev, news, classification, catalysts, openrouter]
category: concept
---

# Jev News Sieve

The Jev news sieve is the relevance filter that separates genuine market-moving catalysts from routine corporate noise in the intraday news feed. It uses TypeSafe Jev — a structured decision API on OpenRouter — to classify each incoming headline before it reaches trading agents, keeping the signal-to-noise ratio high.

## Classification

Each event is submitted to the OpenRouter Decisions API (`https://openrouter.ai/api/alpha/decisions`) with a single `market_relevance` question of type `choice` and two criteria:

- **MARKET_MOVING** — major macroeconomic surprises (ISM PMI, CPI, jobs prints vs consensus), Fed governor rate-policy remarks, significant geopolitical developments, large-cap (> $20B) earnings/guidance shocks, major M&A, regulatory/legal interventions, or systemic liquidity shocks that alter index or sector trajectory.
- **NOISE** — routine promotional press releases, law-firm class-action solicitations, sub-$2B penny stock moves, generic technical commentary, scheduled dividend announcements, recycled opinion pieces, or news already fully priced.

## Confidence Threshold

Jev returns a `choice`, a `confidence` (normalized to a 0–100 scale), and a probability distribution. An event is treated as market-moving only when `choice == MARKET_MOVING` **and** `confidence >= 70.0`. Everything else is discarded.

## Failure Behavior

The sieve fails safe toward silence: a missing `OPENROUTER_API_KEY`, a non-200 response, or a network exception all resolve to `NOISE` with zero confidence, so no unvetted item is ever surfaced to agents.

## Where It Applies

The sieve is invoked by `evaluate_news_with_jev()` in `apps/engine/analysis/intraday_news.py` during `sync_intraday_market_news()`. Surviving items are stored in `intraday_market_news` and later rendered both to agents (via the `get_market_moving_news` tool) and to humans (via the [[entities/intraday-news-wire]] dashboard component).

## Related

- [[entities/intraday-news]]
- [[entities/intraday-news-wire]]
- [[concepts/jev-decisions-model]]
- [[concepts/catalyst-radar]]
