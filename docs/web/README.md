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

## 2. Pragmatic Architecture (Routes First)

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

## 3. Project Structure

```text
apps/web/
├── src/
│   ├── routes/          # OWNERSHIP: Logic lives where it's used
│   │   ├── portfolios/
│   │   │   ├── route.tsx
│   │   │   ├── -PortfolioTable.tsx
│   │   │   └── -queries.ts # Route-local Supabase queries (prefixed with -)
│   ├── shared/          # SHARED DOMAIN: Business concepts used across routes
│   │   ├── auth/
│   │   └── portfolios/
│   ├── components/      # DESIGN SYSTEM: Pure UI primitives
│   │   ├── ui/          # Button, Card, Badge
│   │   └── layout/      # Sidebar, Header
│   ├── lib/             # INFRASTRUCTURE: Supabase clients, SEO, Utils
│   ├── hooks/           # GENERIC HOOKS: useMutation, useDebounce
│   ├── styles/          # Global CSS and Tailwind configuration
│   └── router.tsx       # Router configuration
└── vite.config.ts       # Vite and TanStack Start configuration
```

## 4. Core Workflows

### Adding a New Route
1. Create a folder in `src/routes/` (e.g., `src/routes/my-feature`).
2. Create `index.tsx` (or `route.tsx`) for the main route composition.
3. Create a `components/` subfolder for route-specific UI. Rename components with a `-` prefix (e.g., `-MyComponent.tsx`).
4. Define your data fetching in `-queries.ts`.

### SSR & Import Discipline
*   **Absolute Rule**: Routes must **never** import from other routes.
*   **SSR Safety**: Keep Loaders and `createServerFn` in routes or shared. Never perform data fetching inside `components/`.
*   **Supabase SSR**: Use `getSupabaseServerClient` for Loaders/Server Functions and `getSupabaseBrowserClient` for client-side interactions.

## 5. Development & Testing

### Local Setup
1.  Ensure you have `pnpm` installed.
2.  Install dependencies from the root: `pnpm install`.
3.  Configure `.env` in `apps/web/.env` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. or build-time variables without the prefix like `SUPABASE_URL` and `SUPABASE_ANON_KEY`
4.  Run the development server: `pnpm --filter web dev`.

### Testing
We use Vitest and React Testing Library. Tests are **colocated** next to the code they test using the `*.test.tsx` suffix.
*   Run tests: `pnpm test`
*   Full guide: [testing.md](./testing.md)

### Design Aesthetics
We follow a **"Vibrant & Fluid"** approach using Tailwind CSS 4:
*   **Fluid Typography & Spacing**: Uses `clamp()` to scale UI elements seamlessly between mobile and desktop without excessive media query classes.
*   **Layout Primitives**: Employs a "Composition-first" strategy using `.stack`, `.cluster`, and `.grid-auto-fit` to handle layouts intrinsically.
*   **Vibrant Style**: Inspired by PostHog and Duolingo, featuring bold brand colors (`#58cc02`), rounded corners, and shadow-based depth.
