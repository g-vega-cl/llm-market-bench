---
tags: [entity, web, dashboard, frontend]
category: entity
---

# Web App

TanStack Start dashboard in `apps/web` providing real-time portfolio telemetry, trade audit trails, and LLM cognitive synthesis. The frontend is organized into vertical feature slices and styled with the Matcha & Cedar Boxel design system.

## Primary topbar routes

The global navigation bar in `apps/web/src/routes/__root.tsx` exposes strictly 3 top-level destinations:

- **Home** (`/` and `/today` redirect): Unified 2-block live overview (`apps/web/src/features/home/pages/HomePage.tsx`). Block 1 renders the **Live Agent Trader console** (`LiveAgentConsole.tsx`) — a 24/7 autonomous SPY trader with a 1-minute D3 candlestick tape, agent conviction bar, intraday thought trace, VWAP/RSI/trend technicals, and an audience chat-queue teaser (see [[entities/live-agent-trader]]). Block 2 renders **Active Agent Portfolios** alongside the inline S&P 500 benchmark trough, excluding mechanical `sys-*` strategies so only autonomous LLM agents appear on the Home leaderboard.
- **Portfolios** (`/portfolios`): 3-block capital allocation arena (`apps/web/src/features/portfolios/pages/PortfoliosPage.tsx`). Block 1 renders the interactive `PortfolioComparisonChart` with timeframe and benchmark controls. Block 2 renders **Active LLM Agents** using single-level boxel cards. Block 3 renders **Systematic Strategies** (`sys-*`) in a dedicated section.
- **Lab** (`/lab`): 3-block experimental directory (`apps/web/src/routes/lab.tsx`) indexing all 18 specialized research, telemetry, and audit routes with descriptions, plus the **Retired Agent Archive** for frozen historical portfolios.

## Specialized lab routes

- **Autoresearch Arena** (`/autoresearch`): Renders the Unified Risk-Adjusted Z-Score with $\sigma$ unit suffix, baseline comparisons, and step-by-step arithmetic drawers (`ScoreBreakdown.tsx`, `ScoreCalculation.tsx`, see [[concepts/risk-adjusted-z-score]]).
- **Daily Predictions** (`/daily-predictions`): Independent model tabs with strict track isolation and 4-pillar composite ratchet scores. See [[entities/daily-market-predictor]].
- **Portfolio Detail Pages** (`/portfolios/:id` and `/renko`): Real-time portfolio analysis, performance charts, current positions, and recent trades audit trail in Eastern Time (`ET`).
- **Investment Chat Gateway** (`/chat`): Conversational research interface with live database query tools and memory search. See [[entities/investment-chat-gateway]].
- **AI Memories Page** (`/memories`): Searchable archive of market consensus events, economic calendar catalysts, lessons, and resolved trades. See [[concepts/memory-feedback]].

## Architecture

- Built with TanStack Start and React Router v7 SSR.
- Uses TanStack Query for data fetching with SSR-safe QueryClient.
- Styled with Tailwind CSS v4 and `@llm-market-bench/ui-design-system`.

## Related

- [[entities/autoresearch-arena]]
- [[concepts/risk-adjusted-z-score]]
- [[entities/daily-market-predictor]]
- [[entities/investment-chat-gateway]]
- [[entities/live-agent-trader]]
- [[entities/design-system]]
- [[concepts/vertical-slice-islands]]
- [[concepts/zero-frontend-compute]]
- [[concepts/tanstack-query]]
- [[concepts/type-safety]]
