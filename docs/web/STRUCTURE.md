# Pragmatic Frontend Architecture (Routes First)

This document defines a simple, scalable structure for `apps/web`. It prioritizes **colocation** (keeping things near their usage) while providing a clear home for shared code.

## The Core Principle

> **Routes own everything by default.**
> If it's used only on one page, keep it in that page's folder.

---

## Folder Ownership (The Three Buckets)

### 1. `src/routes/` (Domain Logic & Composition)
**Routes own their logic.** This includes route-specific components, hooks, queries, and types.
- **Rules**: Keep files here until they are *actually* needed by another route.
- **Example**: `src/routes/portfolios/PortfolioTable.tsx`

### 2. `src/shared/` (Shared Domain)
**Shared are for shared business concepts.** If a component or hook has domain knowledge (e.g., knows about Portfolios, Decisions, or Trades) and is used in **multiple** routes, it lives here.
- **Common Shared**: `auth`, `portfolios`, `decisions`.
- **Note**: This prevents "Route Isolation" from being broken by cross-route imports.

### 3. `src/components/` (Design System)
**Pure UI primitives only.** Zero domain knowledge, zero Supabase, zero data fetching.
- **Sub-folders**: `ui/` (Buttons, Cards, Inputs) and `layout/` (Sidebars, PageWrappers).

---

## Folder Structure (Visual Summary)

```txt
src/
├── routes/                 # OWNERSHIP: Logic lives where it's used
│   ├── index.tsx
│   └── portfolios/
│       ├── route.tsx
│       ├── PortfolioTable.tsx
│       └── queries.ts      # Route-local Supabase queries
│
├── shared/               # SHARED DOMAIN: Business concepts used across routes
│   ├── auth/
│   │   ├── components/     # e.g., Login modal
│   │   └── hooks/          # e.g., useSession
│   └── portfolios/         # e.g., PortfoliioSummaryCard
│
├── components/             # DESIGN SYSTEM: Pure UI primitives
│   ├── ui/                 # Button, Card, Badge
│   └── layout/             # Sidebar, Header
│
├── lib/                    # INFRASTRUCTURE: Supabase clients, SEO, Utils
├── hooks/                  # GENERIC HOOKS: useMutation, useDebounce
└── types/                  # GLOBAL TYPES: Database schemas
```

---

## Simple Decision Tree

1. **Is it purely for this page?** → Put it in the **Route** folder.
2. **Is it a generic UI primitive (e.g. Button)?** → Put it in **`components/ui`**.
3. **Is it a business component used on multiple pages?** → Put it in **`shared/`**.

---

## SSR & Import Discipline

* **Absolute Rule**: Routes must **never** import from other routes.
* **SSR Safety**: Keep Loaders and `createServerFn` in routes or shared. Never perform data fetching inside `components/`.
