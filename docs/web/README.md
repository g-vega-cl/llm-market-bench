# Web Application Architecture: AI Wall Street Dashboard

The frontend of AI Wall Street is a high-performance, type-safe web application built with **TanStack Start**. It provides real-time visualization of LLM trading performance, portfolio metrics, and the decision attribution trail.

## 1. Tech Stack

| Component | Technology |
| --- | --- |
| **Framework** | [TanStack Start](https://tanstack.com/start) (React 19 + Vite) |
| **Routing** | [TanStack Router](https://tanstack.com/router) (File-based) |
| **Styling** | [Tailwind CSS 4](https://tailwindcss.com/) |
| **Data Fetching** | [TanStack Query](https://tanstack.com/query) |
| **Backend** | [Supabase](https://supabase.com/) (Auth, Postgres, Real-time) |
| **Language** | TypeScript |
| **Testing** | [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/) |

## 2. Design System

### Typography
- **Headlines:** Space Grotesk (tech-forward, distinctive)
- **Body:** Satoshi (clean, modern, readable)
- **Data:** JetBrains Mono (prices, timestamps, code)

### Color Palette
| Color | Purpose | Usage |
|-------|---------|-------|
| **Electric Blue** | Trust, Intelligence | Primary actions, links, hero gradients |
| **Neon Green** | Gains, Success | BUY signals, positive metrics, live indicators |
| **Alert Red** | Losses, Warnings | SELL signals, rejections, critical alerts |
| **Deep Purple** | AI Cognition | Consensus insights, agent avatars |
| **Cyber Yellow** | Catalysts, Attention | Horizon Watch, countdown timers |

### Motion & Animation
- **Staggered Reveals:** Sections animate in with 100ms delays
- **Card Lift:** Hover effects with shadow and translateY
- **Live Pulse:** Animated dots for real-time indicators
- **Shimmer:** Loading states and gradient effects
- **Float:** Gentle vertical motion for hero elements

### Component Patterns
- **Gradient Borders:** Hover-activated reveals using pseudo-elements
- **Glass Morphism:** Backdrop blur for overlays and sticky headers
- **Badge System:** Rounded pills with color-coded importance
- **Timeline View:** Vertical connecting lines with dot markers
- **Expandable Cards:** Click-to-reveal pattern for detailed reasoning

## 3. Vertical Feature Slicing

We organize the frontend into **vertical feature slices** — self-contained modules where each feature owns its entire stack: API, queries, components, pages, and tests. Routes are thin shells that delegate to feature pages.

### The Three Layers

| Layer | Folder | Purpose |
| --- | --- | --- |
| **Feature Slices** | `src/features/<feature>/` | **Each feature owns everything it needs.** API functions, TanStack Query options, components, page composition, utilities, and tests all live in one directory. Exposes a curated public API via `index.ts`. |
| **Route Shells** | `src/routes/` | **Thin delegation layer.** File-based routes that call `createServerFn`, run a loader, and render a feature's page component. No business logic, no components, no queries. |
| **Design System** | `packages/ui-design-system/` | **Pure UI primitives only.** Zero domain knowledge, zero data fetching. Shared across all frontend apps in the monorepo. |

### Feature Slice Anatomy

Each feature in `src/features/` follows this internal structure:

```text
features/<feature>/
├── index.ts         # Public API — only what other features/routes can import
├── api/             # Server functions (createServerFn) and data-fetching logic
├── queries/         # TanStack Query options + key factories (keys.ts, options.ts)
├── components/      # Feature-specific UI components + their tests (*.test.tsx)
├── pages/           # Page-level composition — what a route renders
└── lib/             # Feature-internal utilities (optional)
```

### Decision Tree
1. **Does it belong to a specific feature?** → Put it in `features/<feature>/`.
2. **Is it a reusable UI primitive?** → Put it in `packages/ui-design-system`.
3. **Is it cross-cutting infrastructure (auth, DB client)?** → Put it in `src/lib/`.
4. **Is it a route file for TanStack Router?** → Put it in `src/routes/` as a thin shell.

## 4. TODAY Dashboard Layout

The root route (`/`) displays a comprehensive view of daily AI trading activity:

### Sections (Top to Bottom)

1. **Market Status Hero** - Full-width gradient banner with market status, AI sentiment gauge, and quick stats
2. **AI Cognitive Synthesis** - Consensus insights with agent avatars and importance scores
3. **Daily Intelligence Briefing** - Newsletter summaries in 2-column grid
4. **Market Execution & Guardrails** - Trade feed with agent attribution and expandable reasoning
5. **Horizon Watch** - Timeline of future catalysts with live countdowns

### Features

- **Auto-Refresh:** Every 5 minutes during market hours
- **Empty State:** Rotating witty messages with CTAs when no activity
- **Interactive Cards:** Click-to-expand for detailed reasoning
- **Live Indicators:** Market status, countdown timers, pulse animations
- **Agent Attribution:** Color-coded avatars showing which AI made each decision

## 5. Project Structure

```text
apps/web/
├── src/
│   ├── features/             # VERTICAL SLICES: Self-contained feature modules
│   │   ├── today/            # Market dashboard (today page)
│   │   │   ├── index.ts      # Public API exports
│   │   │   ├── api/          # fetchTodayData server function
│   │   │   ├── queries/      # Query keys + options factory
│   │   │   ├── components/   # MarketStatusHero, AgentInsights, TradeActivity...
│   │   │   ├── pages/        # TodayPage (page-level composition)
│   │   │   └── lib/          # agent-info.ts
│   │   ├── portfolios/       # Portfolio list + detail views
│   │   ├── reasoning/        # LLM reasoning audit trail
│   │   ├── memories/         # Memory chains + chain detail
│   │   ├── market-overview/  # Correlation heatmap + uncorrelated pairs
│   │   ├── cause-and-effect/ # Market impact analysis
│   │   ├── concepts/         # Concept map visualization
│   │   └── audits/           # System audit logs
│   ├── routes/               # THIN SHELLS: File-based routing, zero logic
│   │   ├── __root.tsx        # Root layout with sidebar + auth
│   │   ├── index.tsx         # → features/today/pages/TodayPage
│   │   ├── portfolios/       # → features/portfolios/
│   │   ├── memories/         # → features/memories/
│   │   ├── reasoning/        # → features/reasoning/
│   │   ├── market-overview/  # → features/market-overview/
│   │   ├── cause-and-effect/ # → features/cause-and-effect/
│   │   ├── concepts/         # → features/concepts/
│   │   └── audits/           # → features/audits/
│   ├── components/           # App-level UI (Header, Sidebar, layout)
│   │   ├── ui/               # Re-exports from packages/ui-design-system
│   │   └── layout/           # Sidebar, Header, Navigation
│   ├── lib/                  # Cross-cutting infrastructure
│   │   ├── query-keys.ts     # Global query key factories
│   │   └── supabase.ts       # Supabase client setup
│   ├── hooks/                # Generic reusable hooks
│   ├── styles/               # Global CSS + Tailwind config
│   └── router.tsx            # TanStack Router configuration
└── packages/ui-design-system/  # Shared UI primitives (monorepo package)
    └── src/
        ├── button.tsx
        ├── card.tsx
        ├── badge.tsx
        └── index.ts          # Public API for all apps
```

### Feature Public API Pattern

Each feature exposes a curated set of exports via `index.ts`. No other module should import directly from a feature's internal subdirectories — only through the public API:

```typescript
// features/today/index.ts
export { TodayPage } from './pages/TodayPage'
export { fetchTodayData } from './api/fetch-today-data'
export { todayQueries } from './queries/options'
export { todayQueryKeys } from './queries/keys'
```

### Route Shell Pattern

Routes are strictly thin delegates. They only create `createServerFn`, run a loader, and render a feature's page component:

```typescript
// routes/index.tsx
import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchTodayData } from '~/features/today/api/fetch-today-data'
import { TodayPage } from '~/features/today/pages/TodayPage'

const getTodayData = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchTodayData()
})

export const Route = createFileRoute('/')({
  loader: async () => await getTodayData(),
  component: RouteComponent,
})

function RouteComponent() {
  const initialData = Route.useLoaderData()
  const getTodayDataFn = useServerFn(getTodayData)
  return <TodayPage initialData={initialData} fetchFn={() => getTodayDataFn()} />
}
```

## 6. Core Workflows

### Adding a New Feature
1. Create a new directory in `src/features/<feature-name>/`.
2. Set up the feature slice structure:
   - `api/` — server functions (`createServerFn`) and data-fetching logic
   - `queries/` — TanStack Query options (`options.ts`) and key factories (`keys.ts`)
   - `components/` — feature-specific UI with colocated tests (`*.test.tsx`)
   - `pages/` — page-level composition component
   - `index.ts` — curated public API exports
3. Create a thin route shell in `src/routes/<route-path>/` that:
   - Creates a `createServerFn` wrapping the feature's API call
   - Runs `loader` to preload data
   - Renders the feature's page component

### Feature Isolation Rules
*   **Routes must never import from other routes.**
*   **Features may only import from other features via their `index.ts` public API.** Never reach into another feature's internal subdirectories.
*   **Components in `features/` colocate tests using `*.test.tsx`.** No `-` prefix needed — `features/` is not a TanStack Router directory.
*   **Route shells never contain business logic, components, or queries.** They are strictly delegation layers.

## 7. Development & Testing

### Local Setup
1.  Ensure you have `pnpm` installed.
2.  Install dependencies from the root: `pnpm install`.
3.  Configure `.env` in `apps/web/.env` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. or build-time variables without the prefix like `SUPABASE_URL` and `SUPABASE_ANON_KEY`
4.  Run the development server: `pnpm --filter web dev`.

### Type Safety

Frontend types are generated from the Supabase database schema for type safety. See [Type Generation Documentation](../../supabase/TYPE_GENERATION.md) for details on:
*   How to regenerate types after database migrations
*   Which tables are included/excluded
*   Importing types from `@llm-market-bench/database`

### Testing
We use Vitest and React Testing Library. Tests are **colocated** next to the code they test using the `*.test.tsx` suffix.
*   Run tests: `pnpm test`
*   Full guide: [testing.md](./testing.md)

### Design Aesthetics
See [DESIGN SYSTEM.md](./DESIGN_SYSTEM.md) for the complete design system — typography, color palette, motion, and component patterns.
