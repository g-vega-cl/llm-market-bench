# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the LLM Market Bench TanStack Start application. The following changes were made across 8 files:

- **`src/routes/__root.tsx`** — Added `PostHogProvider` wrapping the entire app inside `<body>`, configured with the Vite proxy (`/ingest`) to avoid CORS issues and support ad-blocker bypass.
- **`src/utils/posthog-server.ts`** *(new file)* — Server-side PostHog singleton using `posthog-node` for use in API/server functions.
- **`vite.config.ts`** — Added a dev-server proxy rule forwarding `/ingest` → `https://us.i.posthog.com`.
- **`src/shared/auth/components/Login.tsx`** — Added `posthog.identify()` and `posthog.capture('user_logged_in')` on successful login.
- **`src/routes/signup.tsx`** — Added `posthog.identify()` and `posthog.capture('user_signed_up')` on successful sign-up.
- **`src/routes/portfolios/$portfolioId.tsx`** — Added `posthog.capture('portfolio_viewed')` on mount via `useEffect` (approved exception: page-view event with meaningful dependency).
- **`src/routes/reasoning/index.tsx`** — Added three captures: category tab filter clicks, trace selection clicks, and load-more clicks.
- **`src/routes/memories/index.tsx`** — Added `posthog.capture('memories_load_more_clicked')` on load-more click.
- **`src/routes/concepts/components/-ConceptMap.tsx`** — Added `posthog.capture('concept_node_hovered')` inside D3 event handlers via a `useRef` pattern to safely access PostHog outside React's render cycle.
- **`src/routes/cause-and-effect/index.tsx`** — Added `posthog.capture('cause_and_effect_viewed')` on mount.

## Events instrumented

| Event name | Description | File |
|---|---|---|
| `user_logged_in` | User successfully logged in with email/password via Supabase | `src/shared/auth/components/Login.tsx` |
| `user_signed_up` | User successfully created a new account | `src/routes/signup.tsx` |
| `user_logged_out` | User initiated logout — captured on the client before redirect | `src/routes/__root.tsx` |
| `portfolio_viewed` | User navigated to a specific portfolio detail page | `src/routes/portfolios/$portfolioId.tsx` |
| `reasoning_trace_selected` | User clicked a reasoning trace to inspect its cognitive flow | `src/routes/reasoning/index.tsx` |
| `reasoning_category_filtered` | User switched the active tab/category filter on the reasoning page | `src/routes/reasoning/index.tsx` |
| `reasoning_load_more_clicked` | User clicked Load More on the reasoning traces list | `src/routes/reasoning/index.tsx` |
| `memories_load_more_clicked` | User clicked Load More on the memories list | `src/routes/memories/index.tsx` |
| `concept_node_hovered` | User hovered over a concept node in the semantic cluster map | `src/routes/concepts/components/-ConceptMap.tsx` |
| `cause_and_effect_viewed` | User visited the Cause & Effect library — top of exploration funnel | `src/routes/cause-and-effect/index.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- **Dashboard: Analytics basics** — https://us.posthog.com/project/359142/dashboard/1408285
- **Daily Active Users & Sign-ups** — https://us.posthog.com/project/359142/insights/sNwrgYYq
- **User Acquisition Funnel** (Sign Up → Login → Portfolio Viewed) — https://us.posthog.com/project/359142/insights/g8fhGW9m
- **Feature Engagement Overview** (Portfolio, Reasoning, Concepts) — https://us.posthog.com/project/359142/insights/16Ogw3Xl
- **Reasoning Category Filter Usage** (breakdown by category) — https://us.posthog.com/project/359142/insights/pwlkOzmd
- **User Retention (Weekly)** — https://us.posthog.com/project/359142/insights/VkbktqgC

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-tanstack-start/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.
