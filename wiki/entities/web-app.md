---
tags: [entity, web, dashboard, frontend]
category: entity
---

# Web App

TanStack Start dashboard in `apps/web` providing real-time portfolio telemetry, trade audit trails, and LLM cognitive synthesis. The frontend is organized into vertical feature slices and styled with the Matcha & Cedar Boxel design system.

## Primary topbar routes

The global navigation bar in `apps/web/src/routes/__root.tsx` exposes strictly 3 top-level destinations:

- **B** (`/` and `/today` redirect): The home destination is rendered as a compact `B` logo button (`font-mono`, `px-2.5`) carrying `aria-label="Home"` for accessibility. The former standalone `BENCHIFY` wordmark and separate `Home` text button have been removed — the `B` button is the sole home affordance. It leads to the unified 2-block live overview (`apps/web/src/features/home/pages/HomePage.tsx`). Block 1 renders the **Live Agent Trader console** (`LiveAgentConsole.tsx`) — a 24/7 autonomous SPY trader with a 1-minute D3 candlestick tape, agent conviction bar, intraday thought trace, VWAP/RSI/trend technicals, and an audience chat-queue teaser (see [[entities/live-agent-trader]]). Block 2 renders **Active Agent Portfolios** alongside the inline S&P 500 benchmark trough, excluding mechanical `sys-*` strategies so only autonomous LLM agents appear on the Home leaderboard.
- **Portfolios** (`/portfolios`): 3-block capital allocation arena (`apps/web/src/features/portfolios/pages/PortfoliosPage.tsx`). Block 1 renders the interactive `PortfolioComparisonChart` with timeframe and benchmark controls. Block 2 renders **Active LLM Agents** using single-level boxel cards. Block 3 renders **Systematic Strategies** (`sys-*`) in a dedicated section.
- **Lab** (`/lab`): 3-block experimental directory (`apps/web/src/routes/lab.tsx`) indexing all 18 specialized research, telemetry, and audit routes with descriptions, plus the **Retired Agent Archive** for frozen historical portfolios.

The authenticated user's email badge (linking to `/profile`) and the login/logout control are right-aligned in the topbar (`ml-auto`), keeping the left cluster reserved for the `B` logo and the three nav items.

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

## Auth / DB client separation

The web app uses two strictly separated Supabase client families (see [[concepts/auth-db-client-separation]]):

- **Auth client** — `apps/web/src/lib/auth.ts` (`getAuthServerClient`) and `apps/web/src/lib/auth-client.ts` (`getAuthBrowserClient`) talk to **Supabase Cloud** for password login, Google OAuth, session cookies, and `auth.getUser()`. `assertValidAuthUrl` rejects any URL containing `benchify-archive-db` to prevent `PGRST125` auth misrouting.
- **DB client** — `apps/web/src/lib/db.ts` (`getDbServerClient`, `getDbBrowserClient`) talks to the **self-hosted PostgREST archive DB** (`https://benchify-archive-db.clvg.uk`) for all data reads/writes, using stateless `createClient` options (`persistSession: false`, `autoRefreshToken: false`, `detectSessionInUrl: false`). `getDbServerClient({ useServiceRole: true })` is used for privileged server-side operations (chat schema introspection, `chat_memories` writes).

All feature data fetchers import `getDbServerClient` / `getDbBrowserClient` from `~/lib/db`; auth routes import `getAuthServerClient` from `~/lib/auth`. The former `~/lib/supabase` and `~/lib/supabase-client` modules have been removed.

## Related

- [[entities/autoresearch-arena]]
- [[concepts/risk-adjusted-z-score]]
- [[entities/daily-market-predictor]]
- [[entities/investment-chat-gateway]]
- [[entities/live-agent-trader]]
- [[entities/design-system]]
- [[concepts/auth-db-client-separation]]
- [[concepts/vertical-slice-islands]]
- [[concepts/zero-frontend-compute]]
- [[concepts/tanstack-query]]
- [[concepts/type-safety]]
