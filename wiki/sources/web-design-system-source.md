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

---

## Primitives

### Badge
- **Variants:** `solid`, `soft`, `outline`, `glass`
- **Options:** `showDot` (boolean) to render an indicator dot
- **Sizes:** `xs`, `sm`, `md`
- **Color schemes:** `accent`, `success`, `danger`, `info`, `warning`, `neutral`
- **Severity:** `high`, `medium` (overrides colorScheme when provided)
- **Radius:** `full`, `lg`, `md`

### Button (contains LoadingSpinner)
- **LoadingSpinner sizes:** `sm`, `md`

### Card
- **Variants:** `default`, `outlined`, `glass`, `glass-warning`
- **Padding:** `none`, `sm`, `md`, `lg`
- **Gradients:** `electric`, `success`, `alert`, `catalyst`, `ai`
- Note: `accentBorder` and `accentBorderColor` props have been removed in favor of semantic `colorScheme`.

### Select
- Standard select component with full styling and design token integration.

### Input / Label
- Unchanged.

## Patterns

### LoadingBoundary
- Uses LoadingSpinner with `size="md"`.

### SectionHeading & HeroBackground
Both accept a `gradient` prop with allowed values: `electric`, `success`, `catalyst`, `ai`.

## Severity Mapping in Application Code

- `AuditCard`: maps ` CRITICAL` → `high`, `LOW` → `medium`
- `FutureCatalysts` uses threshold: importance >=8 → `high`, else `medium`

---

## Related
- [[entities/web-app]]
- [[concepts/project-linting]]
