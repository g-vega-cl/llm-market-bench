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
- **Lab** (`/lab`): 3-block experimental directory (`apps/web/src/routes/lab.tsx`) indexing all specialized research, telemetry, and audit routes with descriptions, linking to **Retired Agents** (`/retired-agents`, `apps/web/src/routes/retired-agents.tsx`), a dedicated page for frozen historical portfolios.

The topbar is a single non-wrapping row (`flex items-center`, no `flex-wrap`). The left cluster holds the `B` logo and the three nav items; the right cluster (`ml-auto shrink-0`) holds only the login/logout control. The authenticated user's email is **not** rendered in the navbar — the email badge that previously linked to `/profile` has been removed, so the logout link stays on the same row regardless of email length.

## Homepage Benchmark Moves (Live Quote Merging)

The homepage's inline S&P 500 benchmark trough computes `todayPct` and `weekPct` from the SPY benchmark history via `calculateBenchmarkMoves` in `apps/web/src/routes/index.tsx`. To keep the benchmark accurate during the trading session — before the EOD bar is persisted — the calculation merges a live intraday quote into the historical series.

- **Live quote resolution** — the route loader prefers the latest live tape bar (`fetchLatestIntradayBars`) whose Eastern date matches today, falling back to `fetchLatestBenchmarkQuote('SPY')` (reads `market_data_cache`). Both are gated to today's Eastern date via `getEasternDate` (`apps/web/src/utils/date.ts`), which converts a timestamp to a `YYYY-MM-DD` string in `America/New_York` and avoids UTC day-rollover errors.
- **Merge rules** (`mergeLatestBenchmarkQuote`) — a live quote is appended when its date is newer than the latest history point; it replaces the same-day bar only when the market is open (`isRegularMarketHours()`); a stale quote dated earlier than the latest history point is ignored. When the market is closed, the official EOD close is preserved and never overwritten by a stale tick.
- **Safe history query** — `fetchBenchmarkHistory` now appends `T23:59:59.999Z` to a date-only `endDate` and skips the `.lte()` filter entirely when `endDate` is empty, avoiding invalid range queries.

This ensures the homepage benchmark reflects intraday SPY movement during market hours while showing the official close after hours.

## Specialized lab routes

- **Autoresearch Arena** (`/autoresearch`): Renders the Unified Risk-Adjusted Z-Score with $\sigma$ unit suffix, baseline comparisons, and step-by-step arithmetic drawers (`ScoreBreakdown.tsx`, `ScoreCalculation.tsx`, see [[concepts/risk-adjusted-z-score]]).
- **Daily Predictions** (`/daily-predictions`): Independent model tabs with strict track isolation and 4-pillar composite ratchet scores. See [[entities/daily-market-predictor]].
- **Portfolio Detail Pages** (`/portfolios/:id` and `/renko`): Real-time portfolio analysis, performance charts, current positions, and recent trades audit trail in Eastern Time (`ET`).
- **Retired Agents** (`/retired-agents`): Dedicated archive page (`apps/web/src/routes/retired-agents.tsx`) listing every frozen, inactive portfolio (`!p.is_active`) with its owner name and total equity, each linking to its `/portfolios/$portfolioId` detail page. It replaces the former inline **Retired Agent Archive** table that lived inside the `/lab` Audits block. The route loader calls `fetchPortfolios()` via a `createServerFn` and filters to inactive portfolios; the `RetiredAgentsView` component renders an empty state ("No retired agents.") when none exist. The `/lab` directory links to it from the "Audits, Benchmarks & Retired Archives" category.
- **Companies** (`/companies`, `/companies/$ticker`): Institutional company & sector research dossier explorer (`apps/web/src/features/companies/`). The directory (`CompaniesPage.tsx`, `fetch-companies.ts`) supports search by ticker/name/sector, verdict filter pills, and equal-height summary cards (verdict + conviction, spot price, mention count). The dossier page (`CompanyDossierPage.tsx`, `fetch-company-dossier.ts`) renders a verdict banner, economic moat / valuation / options cards, a thesis falsification panel, full Markdown analysis via `MarkdownContent`, and a historical research timeline. It is reachable from `/lab` and from `/generated-newsletters` ("Explore Company Dossiers →"). See [[entities/company-research-reports]].
- **Investment Chat Gateway** (`/chat`): Conversational research interface with live database query tools and memory search. See [[entities/investment-chat-gateway]].
- **AI Memories Page** (`/memories`): Searchable archive of market consensus events, economic calendar catalysts, lessons, and resolved trades. See [[concepts/memory-feedback]].

## Architecture

- Built with TanStack Start and React Router v7 SSR.
- Uses TanStack Query for data fetching with SSR-safe QueryClient.
- Homepage (`/`) utilizes `useWindowFocusRefresh` (`apps/web/src/features/home/hooks/useWindowFocusRefresh.ts`) to invalidate TanStack Router loaders via `router.invalidate()` on window focus and document visibility restoration (throttled to 5s), keeping market feeling, active portfolios, barometer, and tape synchronized without background CPU polling drain, while reloading PostHog flags and capturing telemetry.
- Styled with Tailwind CSS v4 and `@llm-market-bench/ui-design-system`.

## Auth / DB client separation

The web app uses two strictly separated Supabase client families (see [[concepts/auth-db-client-separation]]):

- **Auth client** — `apps/web/src/lib/auth.ts` (`getAuthServerClient`) and `apps/web/src/lib/auth-client.ts` (`getAuthBrowserClient`) talk to **Supabase Cloud** for password login, Google OAuth, session cookies, and `auth.getUser()`. `assertValidAuthUrl` rejects any URL containing `benchify-archive-db` to prevent `PGRST125` auth misrouting. `getAuthServerClient()` resolves its URL/key from `SUPABASE_AUTH_URL` / `SUPABASE_AUTH_ANON_KEY`, falling back through `SUPABASE_URL` / `SUPABASE_ANON_KEY` and then the `VITE_SUPABASE_AUTH_*` / `VITE_SUPABASE_*` build-time variables.
- **DB client** — `apps/web/src/lib/db.ts` (`getDbServerClient`, `getDbAdminClient`, `getDbBrowserClient`) talks to the **self-hosted PostgREST archive DB** (`https://benchify-archive-db.clvg.uk`) for all data reads/writes, using stateless `createClient` options (`persistSession: false`, `autoRefreshToken: false`, `detectSessionInUrl: false`). `getDbAdminClient()` is an explicit dedicated export used for privileged server-side operations (chat schema introspection, `chat_memories` writes, and `agent_chat_queue` audience submissions) to prevent bundler parameter folding optimizations from dead-code eliminating service_role branches.

All feature data fetchers import `getDbServerClient` / `getDbBrowserClient` from `~/lib/db`; auth routes import `getAuthServerClient` from `~/lib/auth`. The former `~/lib/supabase` and `~/lib/supabase-client` modules have been removed.

### Auth resilience in the root route

`fetchUser` (the root route's `createServerFn`) wraps `auth.getUser()` in a `try/catch` and returns `null` (guest) on any thrown error, missing user, or missing email, logging a `console.warn` rather than propagating. `RootDocument` reads the route context defensively (`context?.user`) so it renders safely even when the router is in an error state and the context is undefined. Together these keep a transient Auth-service failure from crashing the root route — the app degrades to an unauthenticated render instead.

## Related

- [[entities/autoresearch-arena]]
- [[concepts/risk-adjusted-z-score]]
- [[entities/daily-market-predictor]]
- [[entities/investment-chat-gateway]]
- [[entities/company-research-reports]]
- [[entities/live-agent-trader]]
- [[entities/design-system]]
- [[concepts/auth-db-client-separation]]
- [[concepts/vertical-slice-islands]]
- [[concepts/zero-frontend-compute]]
- [[concepts/tanstack-query]]
- [[concepts/type-safety]]
