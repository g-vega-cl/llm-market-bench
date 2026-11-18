---
tags: [design-system, ui, governance, testing, variants]
category: concept
---

# Design Variant Budget

The Design Variant Budget is a hard cap on stylistic variety across `apps/web` and `@llm-market-bench/ui-design-system`. Every primitive exposes **at most two style variants**, and every source file stays within a two-combination typography budget and a two-treatment border budget. The rule is enforced by `apps/web/src/test/design-variant-budget.test.tsx`, which walks every `.ts`/`.tsx` file in both packages and fails the build on any violation.

## Why It Exists

Unbounded variant proliferation is the root cause of visual drift in a design system. When a primitive exposes `solid | outline | ghost | soft | glass` and a caller can also pass `gradient`, `rounded`, `radius`, and `severity` props, the same conceptual control renders a dozen different ways across pages. The result is a dashboard that reads as a patchwork rather than a single instrument.

The budget collapses each primitive to the two variants that actually carry meaning:

- **Button** — `solid` (primary action) and `outline` (secondary action).
- **Badge** — `solid` (high-emphasis state) and `soft` (low-emphasis state).
- **Card** — `default` (raised surface) and `outlined` (recessed surface).

Everything else — color, size, iconography — is a semantic token or a size step, not a stylistic variant.

## The Rules

### 1. Two variants per primitive

`Button`, `Badge`, and `Card` each declare a `variant` union with at most two members. The test reads the `variant?:` type declaration and asserts `members.length <= 2`.

### 2. Zero legacy decorative props

The primitives no longer expose `gradient`, `rounded`, `radius`, or `severity` props. `SectionHeading` no longer exposes a `gradient` prop. The test asserts these props are absent from the source.

### 3. Zero legacy theme residue

No source file may contain:

- `dark:` variant utilities (the app is single-theme dark).
- `text-white` (solid fills use `text-voxel-trough` for WCAG AAA contrast).
- `backdrop-blur` (glassmorphism is banned).
- Banned font weights: `font-light`, `font-medium`, `font-semibold`, `font-extrabold`, `font-black`.
- Banned font sizes: `text-base`, `text-xl`, `text-2xl`, `text-3xl`, `text-4xl`, `text-5xl`, `text-6xl`, `text-7xl`.

Only the three typography tiers (`text-lg font-bold`, `text-sm font-bold`, `text-xs font-normal`) are permitted.

### 4. Zero ad-hoc raw `<button>` elements

Every interactive button in `apps/web` must render through the `Button` primitive. The test greps for `<button` in `apps/web/src` and fails on any match. This guarantees keyboard semantics, the `voxel-btn` press geometry, and the `isLoading` pending state are applied uniformly.

### 5. Per-file typography budget (max two combos)

Each component file may use at most two `(size, weight)` combinations across its string literals. A file that mixes `text-lg font-bold`, `text-sm font-bold`, and `text-xs font-normal` is flagged. The intent is that a single component expresses at most a heading tier and a body tier.

### 6. Per-file border budget (max two decorative treatments)

Each component file may use at most two decorative border treatments (1px rule, 2px rule, 4px accent bar, dashed). Structural borders (`border-collapse`, `border-0`, `divide-*`, `ring*`, `outline*`) are excluded. A file that mixes a 1px rule, a 2px rule, and a 4px accent bar is flagged.

## Enforcement

`apps/web/src/test/design-variant-budget.test.tsx` runs in the standard `pnpm test` suite (and therefore in the pre-commit hook). It walks `packages/ui-design-system/src` and `apps/web/src`, skipping `node_modules`, `dist`, `coverage`, `build`, `.scratch`, `.git`, and `.netlify`, and asserts every rule above.

The test is intentionally strict: a single `dark:` class or a single raw `<button>` fails the suite. This keeps the design system from silently regressing as new pages are added.

## Related

- [[entities/design-system]] — the primitives and tokens the budget governs
- [[concepts/fluent-responsive-design]] — the layout half of the same design specification
- [[concepts/in-flow-inspection]] — the interaction half (zero floating overlays)
- [[concepts/cumulative-layout-shift]] — the loading/CLS half
- [[entities/agent-rules]] — the mandate list that references the design spec
