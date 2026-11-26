---
tags: [entity, web, dashboard, frontend]
category: entity
---

# Web App

TanStack Start dashboard in `apps/web` providing real-time portfolio telemetry, trade audit trails, and LLM cognitive synthesis. The frontend is organized into vertical feature slices and styled with the Matcha & Cedar Voxel design system.

## Primary topbar routes

The global navigation bar in `apps/web/src/routes/__root.tsx` exposes strictly 3 top-level destinations:

- **B** (`/`): The home destination is rendered as a compact `B` logo button (`font-mono`, `h-9 w-9`) carrying `aria-label="Home"`. `/` is a single-screen call to action (`apps/web/src/features/home/pages/HomeCtaPage.tsx`) built on the design-system `SceneStage` primitive (`variant="hero"`, `motionRole="reactive"`): an eyebrow, the headline "Build your own trading bot.", a concise 1-sentence subheadline, and an open-sky 3-CTA stack (`data-testid="home-cta-actions"`): one accent CTA into `/lab` (`Start building`), a secondary `Take the investing style test` button into `/personality` (`data-testid="take-personality-test"`), and a tertiary underlined link (`See how the published bots are doing`) into `/leaderboard`. The route loader resolves the US Eastern market session atmosphere (`resolveAtmospherePhase(new Date(), 'market-et')`) server-side so SSR and CSR agree on first byte without flashes or CLS, and exposes accessible foreground HUD controls in the `SceneStage` `controls` slot via `SceneHudControls`. Behind it sits `GardenBackdrop.tsx` — the panoramic **Cedar Sanctuary** floating voxel ridge across the dynamic Matcha & Cedar atmospheres with 4-plane depth parallax, portrait-mobile vertical framing, a 1.1s stepped upward entrance reveal, extended top atmospheric sky vignettes, and calm micro-life. See [[entities/recipe-studio]], [[concepts/living-scene-backdrops]], and [[concepts/cumulative-layout-shift]].
- **Recipes** (`/recipes`): Rendered as a list/scroll SVG icon (`h-9 w-9`) with `aria-label="Recipes"`. The route is public: anonymous visitors get the template gallery, signed-in users get the **My Bots dashboard**. Portfolios is reached from the `/lab` "Audits, Benchmarks & Retired Archives" block (`/portfolios`).
- **Lab** (`/lab`): Rendered as a conical flask SVG icon (`h-9 w-9`) with `aria-label="Lab"`. 3-block experimental directory indexing all specialized research, telemetry, and audit routes, linking to **Retired Agents** (`/retired-agents`). The builder lives at `/build` and is linked from the homepage and gallery.

The topbar is a single non-wrapping row. The left cluster holds the `B` logo and the three nav items; the right cluster (`ml-auto shrink-0`) holds only the login/logout control, a square icon button (`h-9 w-9 shrink-0`) rendering an inline `LoginIcon` / `LogoutIcon` SVG with `aria-label` and `title`.

## Specialized lab routes

- **Recipe Builder** (`/build`): Conversational strategy compiler (`apps/web/src/features/recipes/builder/`). Describe a bot in plain English, get a validated Push v2 recipe, then backtest or go live. The primary entry point for creating new strategies. Steps 1–2 sit on `SceneStage` with the canvas-free `CedarRidgeBackdrop`; once compiled, `CompiledBotWorkspace` transitions onto the fixed dot-matrix `GlobalBackground` inside `PageLayout`. A `/build?recipeId=<id>` request `beforeLoad`-redirects to `/recipes/$recipeId`, so the builder is always a fresh describe flow; after saving an unsaved bot, the workspace navigates to `/recipes/$recipeId`. See [[concepts/living-scene-backdrops]] and [[entities/recipe-studio]].
- **My Bots Dashboard** (`/recipes`): Signed-in users see their saved strategies with live controls, backtest history, and alerts. Anonymous visitors see the read-only template gallery. Each bot card links to `/recipes/$recipeId` (Overview) and `/recipes/$recipeId/edit` (Blueprint).
- **Bot Overview** (`/recipes/$recipeId`): Public-capable **Overview tab** for `is_public`/`is_template` bots. `BotStageHeader` (`SceneStage` + `CedarRidgeBackdrop` + the `Overview | Performance | Behaviour | Live Runs | Blueprint` chip row) plus `BotSummaryStrip` (Total Equity, Net Return, Win Rate, Open Positions); the card carries no panel and no `→` link, and it owns the owner actions (Run Backtest, Enable Live, Turbo). Loads via `fetchRecipeOverviewFn` (30s bounded public cache). Non-owners get a read-only view with `Fork to My Bots`.
- **Performance tab** (`/recipes/$recipeId/performance`): Performance & Equity (`PerformanceOverviewBlock` + `PerformanceChart` + benchmark selector), then Open Positions + Recent Closed Trades + Recent Backtests & Strategy DNA, under `BotSceneShell` (page-level world, `← Overview` back link, bot name + live badge row).  
- **Behaviour tab** (`/recipes/$recipeId/behavior`): `BotBehaviorsBlock` — tool usage, action mix, ticker focus, exit reasons and the latest decision — or an empty state naming the run that will fill it. Same `fetchRecipeOverviewFn` loader as Performance.
- **Live Runs tab** (`/recipes/live/$recipeId/runs`): the paginated run traces only (prompt, tool calls, output per scheduled turn). `/recipes/live/$recipeId` is retired and 307s here. The paper portfolio and closed trades live on Performance.
- **Blueprint Editor** (`/recipes/$recipeId/edit`): Owner-only Blocks & Tools / Prompt Editor (`RecipeEditPage`) under the same `BotSceneShell` chips, with a single compact status + name/save line and no hero card — the editor is the page. A non-owner renders an `ErrorCard`.
- **Live Recipe Backtest** (`/recipes/backtest/$jobId`): Day-by-day streaming view of a running backtest (`RecipeBacktestPage.tsx`), polling `fetchRecipeRunDetailFn` every 1.5s. Header links: `← Bot Overview` → `/recipes/$recipeId` and `Edit Blueprint` → `/recipes/$recipeId/edit` (a `live_turn` job links to `/recipes/live/$recipeId`).
- **Investing Style Diagnostic** (`/personality`): 16-question investing-personality quiz in four acts that scores four axes into a four-letter type code, matches the visitor to one of 16 archetypes, and recommends the mapped starter recipe with a `Build this bot` link into `/build?idea=`. Shareable results live at `/personality/t/<CODE>`.
- **Autoresearch Arena** (`/autoresearch`): Renders the Unified Risk-Adjusted Z-Score with $\sigma$ unit suffix, baseline comparisons, and step-by-step arithmetic drawers.
- **Daily Predictions** (`/daily-predictions`): Independent model tabs with strict track isolation and 4-pillar composite ratchet scores.
- **Portfolio Detail Pages** (`/portfolios/:id` and `/renko`): Real-time portfolio analysis, performance charts, current positions, and recent trades audit trail in Eastern Time (`ET`).
- **Retired Agents** (`/retired-agents`): Dedicated archive page listing every frozen, inactive portfolio (`!p.is_active`).
- **Companies** (`/companies`, `/companies/$ticker`): Institutional company & sector research dossier explorer.
- **Investment Chat Gateway** (`/chat`): Authenticated conversational research interface with live database query tools and memory search. Anonymous visitors get a 307 to `/login?redirect=/chat` from the route `beforeLoad`; chat server functions independently reject guests.
- **AI Memories Page** (`/memories`): Searchable archive of market consensus events, economic calendar catalysts, lessons, and resolved trades.

## Private routes

- **LLM Proxy Logs** (`/llm-logs`): Owner-only viewer for the free LLM proxy audit trail. `beforeLoad` redirects an anonymous visitor to `/login` with `/llm-logs` as the return path, the component renders `<NotFound />` for a signed-in user outside the `isAllowedLlmLogsEmail` allowlist, and `fetchLlmLogsFn` re-checks the caller server-side. The route head declares `robots: noindex, nofollow`.

## Architecture

- Built with TanStack Start and React Router v7 SSR.
- Uses TanStack Query for data fetching with SSR-safe QueryClient.
- The homepage (`/`) renders `HomeCtaPage` on `SceneStage` (`variant="hero"`, `motionRole="reactive"`). Its route loader resolves the US Eastern market session atmosphere server-side. The panoramic Cedar Sanctuary backdrop (`GardenBackdrop.tsx`) caches voxel face extraction once per session, bakes offscreen layers per viewport size and atmosphere phase, disposes superseded canvases, and animates at a 30fps cap. See [[concepts/living-scene-backdrops]] and [[concepts/cumulative-layout-shift]].
- Root route (`apps/web/src/routes/__root.tsx`) installs `useIdleRouteWarmup()`, which delegates to `warmRouteChunks(router, signal)` in `apps/web/src/utils/route-warmup.ts` inside a `requestIdleCallback`. It resolves every path in `PRELOAD_WARMUP_ROUTES` plus `DYNAMIC_WARMUP_SAMPLE_PATHS` through `router.getMatchedRoutes()` and calls `router.loadRouteChunk()` — never `preloadRoute()` — so route JS chunks are compiled into the browser module cache without executing `loader` or `beforeLoad` handlers. See [[concepts/chunk-reload-recovery]].
- Route-level errors are handled by `DefaultCatchBoundary` (`apps/web/src/components/ui/DefaultCatchBoundary.tsx`). Dynamic chunk failures render `ChunkRecoveryView` and claim a single reload slot via `claimChunkReloadAttempt()`, reporting telemetry to PostHog before dispatching `reloadAtTarget(targetHref)`.
- Hashed build assets under `/assets/*` are served with `Cache-Control: public, max-age=31536000, immutable` and `X-Content-Type-Options: nosniff`.
- Netlify deploys (`apps/web/netlify.toml`) use a fail-safe `[build] ignore` exclude-list so backend-only and docs-only commits skip Netlify builds.
- Styled with Tailwind CSS v4 and `@llm-market-bench/ui-design-system`.

## Auth / DB client separation

The web app uses two strictly separated Supabase client families (see [[concepts/auth-db-client-separation]]):

- **Auth client** — `apps/web/src/lib/auth.ts` (`getAuthServerClient`) and `apps/web/src/lib/auth-client.ts` (`getAuthBrowserClient`) talk to **Supabase Cloud** for Google OAuth, session cookies, and `auth.getUser()`. `assertValidAuthUrl` rejects any URL containing `benchify-archive-db` to prevent `PGRST125` auth misrouting.
- **DB client** — `apps/web/src/lib/db.ts` (`getDbServerClient`, `getDbAdminClient`, `getDbBrowserClient`) talks to the **self-hosted PostgREST archive DB** (`https://benchify-archive-db.clvg.uk`) for all data reads/writes, using stateless `createClient` options. `getDbAdminClient()` is an explicit dedicated export used for privileged server-side operations.

All feature data fetchers import `getDbServerClient` / `getDbBrowserClient` from `~/lib/db`; auth routes import `getAuthServerClient` from `~/lib/auth`.

### Auth resilience and dedicated `/signup`

`fetchRootContext` (the root route's `createServerFn` in `apps/web/src/routes/__root.tsx`) wraps `auth.getUser()` in a `try/catch` and returns `user: null` (guest) alongside `publicConfig` on any thrown error, missing user, or missing email, logging a `console.warn` rather than propagating. `RootDocument` reads the route context defensively (`context?.user`, `context?.publicConfig`) so it renders safely even when the router is in an error state. `apps/web/src/routes/signup.tsx` renders `<Auth mode="signup" />` directly (rather than redirecting anonymous visitors to `/login`) with explicit Google account-creation copy and `/login` cross-links.

## Related

- [[entities/recipe-studio]]
- [[entities/personality-quiz]]
- [[entities/autoresearch-arena]]
- [[concepts/risk-adjusted-z-score]]
- [[entities/daily-market-predictor]]
- [[entities/investment-chat-gateway]]
- [[entities/company-research-reports]]
- [[entities/live-agent-trader]]
- [[entities/llm-logs]]
- [[entities/design-system]]
- [[concepts/living-scene-backdrops]]
- [[concepts/auth-db-client-separation]]
- [[concepts/chunk-reload-recovery]]
- [[concepts/core-web-vitals]]
- [[concepts/vertical-slice-islands]]
- [[concepts/zero-frontend-compute]]
- [[concepts/tanstack-query]]
- [[concepts/type-safety]]
