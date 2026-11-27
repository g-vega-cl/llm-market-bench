# Web & UI Rules (`apps/web/AGENTS.md`)

Loaded progressively when working inside `apps/web/` or `packages/ui-design-system/`. Always read root `PRODUCT.md` ("show the receipts") and `.agents/rules/design-spec.md` before changing UI components or routes.

## Zero Compute on Frontend (MANDATORY)

- `apps/web` is strictly presentation. Never compute heavy portfolio aggregations, rolling Sharpe/drawdown math, or multi-table joins on the client.
- Pre-calculate and materialize derived metrics in `apps/engine` background pipelines or PostgreSQL views/RPCs (`[[concepts/zero-frontend-compute]]`), and project explicit scalar columns to strip pgvector `embedding` egress (`[[concepts/vector-egress-stripping]]`).

## Voxel Design System & Layout Invariants

- **Primitives & Theme**: Consume `@llm-market-bench/ui-design-system` primitives (`Button`, `Card`, `Badge`, `SectionHeading`, `Table`, `Skeleton`) in the single **Matcha & Cedar / Cheddar Voxel** dark theme (`rounded-none`, 2px directional bevels, recessed `.voxel-trough` slots).
- **Banned Patterns**:
  - Zero `dark:` toggles, arbitrary Tailwind square-bracket escapes (`w-[240px]`, `bg-[#123]`), or inline `style` objects (except dynamic percentage bar widths).
  - Zero explicit viewport breakpoints (`sm:`, `md:`, `lg:`) or JS layout math (`window.innerWidth`, `ResizeObserver`). Use `flex-wrap`, `repeat(auto-fit, minmax(min(100%, Xrem), 1fr))`, `basis-72`/`basis-96`, and `min-w-0`.
  - Zero exterior child margins (`m-*`, `mt-*`, `mb-*`, `space-y-*`); spacing belongs on parent containers (`gap-2`, `gap-4`, `gap-6`, `mt-auto`/`ml-auto` only).
  - Zero floating tooltips, popovers, HTML `title` attributes, SVG `<title>` hovers, modals, accordions, or `animate-spin` spinners. Render secondary telemetry in-flow inside recessed `.voxel-trough` slots.
- **3-Tier Typography Budget**: Strictly `text-lg font-bold` (Tier 1), `text-sm font-bold` (Tier 2), and `text-xs font-normal` (Tier 3). Action routes (`/build`, `/personality`, `/chat`) use a single `sr-only` `<h1>` and place the primary CTA above history/roadmaps.
- **Data-Driven Tables & CLS Settlement**: Right-align numeric cells and matching `TableHead` headers (`align="right"` or `numeric`, `tabular-nums font-mono`), render bounded enums as `Badge`, mark halted/archived rows `isInactive`, avoid optimistic `onMutate` writes, and gate volatile secondary controls/badges with `isQuerySettled(queries, isTransitionPending)` from `apps/web/src/lib/query-client.tsx`.

## Mandatory Web Verification

Run all four checks before marking frontend changes ready:
1. `pnpm biome check` (use `--write` to auto-fix)
2. `pnpm --filter web typecheck` (Vitest and Biome strip types without checking them)
3. `cd apps/web && pnpm test --maxWorkers=4` (including `page-surface-conventions`, `contrast-audit`, and `design-variant-budget`)
4. `/qa` live browser verification at both 360px mobile width and desktop when modifying visual layouts or user flows.
