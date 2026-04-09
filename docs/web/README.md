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

## 3. Pragmatic Architecture (Routes First)

We prioritize **colocation** (keeping things near their usage) to ensure the codebase remains maintainable as it grows.

### The Three Buckets

| Bucket | Folder | Purpose |
| --- | --- | --- |
| **Domain & Composition** | `src/routes/` | **Routes own everything by default.** Logic, components, hooks, and queries used only on one page stay here. *Note: Non-route files must be prefixed with `-` (e.g., `-queries.ts`) to be ignored by TanStack Router.* |
| **Shared Domain** | `src/shared/` | Business concepts (e.g., Auth, Portfolios) used across **multiple** routes. |
| **Design System** | `src/components/` | **Pure UI primitives only.** Zero domain knowledge, zero data fetching. Includes `ui/` and `layout/`. |

### Simple Decision Tree
1. **Is it purely for this page?** → Put it in the **Route** folder.
2. **Is it a generic UI primitive (e.g. Button)?** → Put it in **`components/ui`**.
3. **Is it a business component used on multiple pages?** → Put it in **`shared/`**.

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
│   ├── routes/          # OWNERSHIP: Logic lives where it's used
│   │   ├── index.tsx    # TODAY Dashboard (Root Entry Point)
│   │   ├── -today-queries.ts # Queries for the daily snapshot
│   │   ├── portfolios/
│   │   │   ├── route.tsx
│   │   │   ├── -PortfolioTable.tsx
│   │   │   └── -queries.ts # Route-local Supabase queries (prefixed with -)
│   │   ├── reasoning/
│   │   │   ├── index.tsx  # LLM research audit dashboard
│   │   │   └── -queries.ts
│   │   ├── how-it-works.tsx  # System process visualization page
│   │   ├── cause-and-effect/
│   │   │   ├── index.tsx  # Market impact & attribution UI
│   │   │   └── -queries.ts # Historical impact queries
│   ├── shared/          # SHARED DOMAIN: Business concepts used across routes
│   │   ├── auth/
│   │   └── portfolios/
│   ├── components/      # DESIGN SYSTEM: Pure UI primitives
│   │   ├── ui/          # Button, Card, Badge
│   │   └── layout/      # Sidebar, Header
│   ├── lib/             # INFRASTRUCTURE: Supabase, SEO, Utils
│   │   ├── queries.ts   # NEW: Centralized Query Options Factory
│   │   └── query-keys.ts # Type-safe Query Key Factories
│   ├── hooks/           # GENERIC HOOKS: useMutation, useDebounce
│   ├── styles/          # Global CSS and Tailwind configuration
│   └── router.tsx       # Router configuration
└── vite.config.ts       # Vite and TanStack Start configuration
```

## 6. Core Workflows

### Adding a New Route
1. Create a folder in `src/routes/` (e.g., `src/routes/my-feature`).
2. Create `index.tsx` (or `route.tsx`) for the main route composition.
3. Create a `components/` subfolder for route-specific UI. Rename components with a `-` prefix (e.g., `-MyComponent.tsx`).
4. Define your data fetching in `-queries.ts`.

### SSR & Import Discipline
*   **Absolute Rule**: Routes must **never** import from other routes.
*   **SSR Safety**: Keep Loaders and `createServerFn` in routes or shared. Never perform data fetching inside `components/`.
*   **Supabase SSR**: Use `getSupabaseServerClient` for Loaders/Server Functions and `getSupabaseBrowserClient` for client-side interactions.

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
We follow a "Rich Aesthetics" approach using Tailwind CSS 4:
*   Vibrant HSL-tailored colors with custom design tokens.
*   Glassmorphism effects for dashboard cards and overlays.
*   Subtle micro-animations for interactive elements (hover, focus, expand).
*   Custom typography scale with Space Grotesk for headlines.
*   Gradient backgrounds and border reveals for visual depth.
*   Card-lift hover effects with shadow transitions.
