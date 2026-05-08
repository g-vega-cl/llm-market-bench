---
tags: [source, web, architecture, frontend]
category: source
source: docs/web/README.md
---

# Source: Web Application Architecture

TanStack Start frontend with feature-sliced architecture.

Key details:

- **Tech stack**: TanStack Start (React + Vite), TanStack Query, Tailwind CSS, Supabase
- **Feature slicing**: Vertical slices at `src/features/<feature>/` — each owns API, queries, components, pages, tests
- **Route shells**: Thin delegation at `src/routes/` — zero business logic
- **Three layers**: Feature Slices → Route Shells → Design System
- **Current features**: today, portfolios, reasoning, memories, market-overview, concepts, audits
- **Type safety**: Frontend types generated from Supabase schema via `@llm-market-bench/database`
