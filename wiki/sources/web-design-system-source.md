---
tags: [design-system, ui, primitives]
category: source
---

# Web Design System: "Bloomberg Terminal meets Wired"

This source page documents the UI design system used across the TanStack Start dashboard. It is a collection of primitives and patterns that enforce visual financial data with a high-tech, polished look.

## Recent Changes (May 2025)

The following items have been **removed** as part of a design system simplification:

- Select primitive (deleted entirely)
- Badge severity levels `critical` and `low` (now only `high` and `medium`)
- LoadingSpinner sizes `xs` and `lg` (now only `sm` and `md`)
- Card variant `elevated` (now only `default`, `outlined`, `ghost`, `glass`)
- Card props `accentBorder` and `accentBorderColor`
- Gradient `alert` removed from HeroBackground, SectionHeading, and Card gradient options

---

## Primitives

### Badge
- **Variants:** `solid`, `soft`, `outline`, `glass`
- **Options:** `showDot` (boolean) to render an indicator dot
- **Sizes:** `sm`, `md`
- **Color schemes:** `accent`, `success`, `danger`, `info`, `warning`, `neutral`
- **Severity:** `high`, `medium` (overrides colorScheme when provided)
- **Radius:** `full`, `lg`, `md`

### Button (contains LoadingSpinner)
- **LoadingSpinner sizes:** `sm`, `md`

### Card
- **Variants:** `default`, `outlined`, `ghost`, `glass`, `glass-warning`
- **Padding:** `none`, `sm`, `md`, `lg`
- **Gradients:** `electric`, `success`, `catalyst`, `ai`
- Note: `accentBorder` and `accentBorderColor` props have been removed.

### Select
- This primitive has been completely removed from the design system.

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
