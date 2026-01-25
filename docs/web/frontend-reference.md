# Frontend Reference Guide

This document serves as a quick reference for developers working on the `apps/web` application.

## 1. Important Links

- **Architecture & Structure**: [STRUCTURE.md](./STRUCTURE.md) - *Read this first!*
- **General Architecture**: [README.md](./README.md)
- **Testing Setup**: [testing.md](./testing.md)

## 2. Core Concepts

### Route Ownership
Everything is a route. If a component is only used in one route, it folder-colocated there.
Example: `src/routes/memories/components/MemoriesList.tsx`

### Shared Domain
Concepts used across multiple routes live in `src/shared`.
Current examples: `auth`, `portfolios`.

### Design System
Pure UI primitives (no state/data fetching) live in `src/components/ui` or `src/components/layout`.

## 3. Common Workflows

### Adding a New Route
1. Create a folder in `src/routes/` (e.g., `src/routes/my-feature`).
2. Create `index.tsx` for the main route composition.
3. Create a `components/` subfolder for route-specific UI.
4. Define your `queries.ts` for data fetching.

### Running with Supabase
The frontend uses `@supabase/ssr` to handle authentication and data fetching.
- Use `getSupabaseServerClient` for Loaders and Server Functions.
- Use `getSupabaseBrowserClient` for client-side interactions.

## 4. Environment Variables
Local development requires a `.env` file in `apps/web` with:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `SUPABASE_URL` (for server-side code)
- `SUPABASE_ANON_KEY` (for server-side code)
