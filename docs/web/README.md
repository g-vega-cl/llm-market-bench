# Web Application Architecture

The frontend is a **TanStack Start** app (React + Vite) with TanStack Query for data fetching, Tailwind CSS for styling, and Supabase for auth/data.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | TanStack Start (React + Vite) |
| Routing | TanStack Router (file-based) |
| Styling | Tailwind CSS |
| Data Fetching | TanStack Query |
| Backend | Supabase (Auth, Postgres) |
| Testing | Vitest + React Testing Library |

See [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) for typography, colors, and component patterns.

## Feature Slicing

We organize the frontend into **vertical feature slices** — each feature owns its entire stack (API, queries, components, pages, tests). Routes are thin shells that delegate to feature pages.

### Three Layers

| Layer | Location | Purpose |
|--------|----------|---------|
| Feature Slices | `src/features/<feature>/` | Self-contained module: API, queries, components, pages, tests |
| Route Shells | `src/routes/` | Thin delegation: createServerFn → loader → render feature page |
| Design System | `packages/ui-design-system/` | Pure UI primitives, zero domain knowledge |

### Feature Anatomy

```
features/<feature>/
├── index.ts        # Public API — only what other features/routes import
├── api/            # createServerFn + data-fetching logic
├── queries/        # TanStack Query options (keys.ts, options.ts)
├── components/     # Feature UI + colocated tests (*.test.tsx)
├── pages/          # Page-level composition
└── lib/            # Feature-internal utilities (optional)
```

### Rules
- Routes never import from other routes
- Features only import from other features via `index.ts`
- Route shells contain zero business logic or components

## Project Structure

```
apps/web/src/
├── features/           # Vertical slices
│   ├── today/          # Dashboard (/)
│   ├── portfolios/     # Portfolio list + detail
│   ├── reasoning/      # LLM reasoning audit trail
│   ├── memories/       # Memory chains
│   ├── market-overview/# Correlation heatmap
│   ├── concepts/       # Concept map (D3.js)
│   └── audits/         # System audit logs
├── routes/             # Thin file-based route shells
├── components/         # App-level UI (sidebar, header)
├── lib/                # Cross-cutting: query-keys, supabase client
└── styles/             # Global CSS + Tailwind config
```

## Development

```bash
cd apps/web
pnpm install
pnpm dev
```

**Type Safety**: Frontend types are generated from Supabase schema via `@llm-market-bench/database`. See [../../supabase/TYPE_GENERATION.md](../../supabase/TYPE_GENERATION.md).

**Testing**: Vitest + React Testing Library with colocated `*.test.tsx` files. See [testing.md](./testing.md).

## Key Files

- `src/lib/queries.ts` — Centralized query options factory
- `src/lib/query-client.tsx` — SSR-safe QueryClient setup
- `src/router.tsx` — TanStack Router configuration
- `src/styles/app.css` — Design system CSS
