---
tags: [design-system, ui, primitives]
category: source
---

# Web Design System: "Bloomberg Terminal meets Wired"

This source page documents the UI design system used across the TanStack Start dashboard. It is a collection of primitives and patterns that enforce visual financial data with a high-tech, polished look.

## Recent Changes

The design system standardizes on high-contrast dark primitives and patterns:

- Badge severity levels are standardized to `high` and `medium`
- LoadingSpinner sizes are `sm` and `md`
- Card variants are `default`, `outlined`, `glass`, and `glass-warning`
- Card props `accentBorder` and `accentBorderColor` are deprecated in favor of semantic glass variants
- Select is maintained as a core form primitive
- **Sharp boxel geometry is the default**: `radius="none"` / `rounded-none` replaces the previous `rounded-xl` / `rounded-2xl` / `rounded-3xl` / `rounded-full` surfaces across primitives and feature pages. Badge gained a `none` radius option, and `Input` / `Select` / `Label` were re-skinned onto the recessed `.voxel-trough` + `text-boxel-*` token set.

---

## Primitives

### Badge
- **Variants:** `solid`, `soft`, `outline`, `glass`
- **Options:** `showDot` (boolean) to render an indicator dot
- **Sizes:** `xs`, `sm`, `md`
- **Color schemes:** `accent`, `success`, `danger`, `info`, `warning`, `neutral`
- **Severity:** `high`, `medium` (overrides colorScheme when provided)
- **Radius:** `none`, `full`, `lg`, `md` (`none` is the boxel default used throughout the app)

### Button (contains LoadingSpinner)
- **LoadingSpinner sizes:** `sm`, `md`

### Card
- **Variants:** `default`, `outlined`, `glass`, `glass-warning`
- **Padding:** `none`, `sm`, `md`, `lg`
- **Gradients:** `electric`, `success`, `alert`, `catalyst`, `ai`
- Note: `accentBorder` and `accentBorderColor` props have been removed in favor of semantic `colorScheme`.

### Select
- Standard select component with full styling and design token integration. Wrapped in a recessed `.voxel-trough rounded-none` container (`bg-boxel-trough`, `border-boxel-bevel-hi`); the `<select>` uses `text-sm font-bold text-boxel-ink` and `<option>` rows use `bg-boxel-surface text-boxel-ink text-sm font-bold`.

### Input / Label
- **Input**: Recessed `.voxel-trough rounded-none` wrapper (`bg-boxel-trough`, `border-boxel-bevel-hi`, `focus-within:ring-accent/40`); inner `<input>` is `text-sm font-bold text-boxel-ink` with `placeholder:text-boxel-muted`. Error state swaps the border to `border-danger`.
- **Label**: `block text-sm font-bold text-boxel-ink uppercase tracking-wider` (Tier 2 control typography, no `mb-*` — spacing is owned by the parent).

## Patterns

### LoadingBoundary
- Uses LoadingSpinner with `size="md"`.

### SectionHeading & HeroBackground
Both accept a `gradient` prop with allowed values: `electric`, `success`, `catalyst`, `ai`.

### MetricTile / EmptyState / ErrorCard / SubHeading
- **MetricTile**: recessed `.voxel-trough rounded-none p-3` tile, `flex flex-col justify-between gap-1`, no child `mb-*` margins.
- **EmptyState**: `flex flex-col items-center gap-4`; emoji in a `w-12 h-12 voxel-trough rounded-none` box at `text-lg`; Tier 1 title (`text-lg font-bold uppercase`) and Tier 3 subtitle (`text-xs font-normal text-boxel-muted`).
- **ErrorCard**: `voxel-card rounded-none` with `border-t-danger/70 border-l-danger/70`, `flex flex-col gap-3`; `text-sm font-bold` title, `text-xs font-normal` message, `voxel-btn` Retry.
- **SubHeading**: no `mb-*` margin — vertical rhythm comes from the parent's `gap`.

## Severity Mapping in Application Code

- `AuditCard`: maps ` CRITICAL` → `high`, `LOW` → `medium`
- `FutureCatalysts` uses threshold: importance >=8 → `high`, else `medium`

---

## Related
- [[entities/web-app]]
- [[entities/design-system]]
- [[concepts/fluent-responsive-design]]
- [[concepts/project-linting]]
