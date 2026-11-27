---
name: qa
description: Audit frontend routes and UI changes against PRODUCT.md and design-spec.md, then verify live browser behavior at 360px mobile and desktop viewports.
---

# QA & Impeccable Voxel UI Critique

Use this skill whenever creating or modifying routes, components, or styles in `apps/web/` or `packages/ui-design-system/`.

## 1. Product & design-spec critique (Impeccable pass)

Read root `PRODUCT.md` and `.agents/rules/design-spec.md` first, then audit every touched component:

1. **Product proof ("Show the receipts")**: Does the view foreground verifiable numbers, trade traces, and caveats (such as asset coverage, slippage, or pending settlement) without marketing puffery or `unslop` violations?
2. **Action vs browse hierarchy**: On action surfaces (`/build`, `/personality`, `/chat`), is the active input and primary CTA immediately visible at the top of a 360px mobile screen with a single `sr-only` `<h1>`?
3. **Voxel geometry & tokens**: Strictly `rounded-none`, 2px directional bevels (`.voxel-card`, `.voxel-trough`, `.voxel-btn`), Matcha & Cedar / Cheddar Voxel dark tokens, WCAG AAA contrast (`text-voxel-trough` on `bg-accent`), and zero `dark:` toggles or arbitrary square-bracket escapes.
4. **Typography & spacing budgets**: Strictly 3 typography tiers (`text-lg font-bold`, `text-sm font-bold`, `text-xs font-normal`), parent-owned `gap-2`/`gap-4`/`gap-6` spacing with zero exterior child margins, max 3 major vertical blocks per page, and zero nested `.voxel-card` inside `.voxel-card`.
5. **Banned UI patterns**: Zero floating tooltips, popovers, HTML `title` attributes, SVG `<title>` hovers, modals, accordions, or `animate-spin` spinners. Secondary inspections sit in-flow inside recessed `.voxel-trough` slots.
6. **Tables & query settlement**: Right-aligned numeric cells and matching `TableHead` headers (`align="right"` or `numeric`, `tabular-nums font-mono`), `Badge` for bounded enums, `isInactive` on halted/archived rows, and `isQuerySettled` gating on volatile secondary badges/controls.

## 2. Deterministic static gates

```bash
pnpm biome check
pnpm --filter web typecheck
cd apps/web && pnpm exec vitest run --maxWorkers=4 src/test/page-surface-conventions.test.tsx src/test/contrast-audit.test.tsx src/test/design-variant-budget.test.tsx
```

## 3. Live browser dogfooding (360px mobile + 1280px desktop)

Using `chromium-devtools` MCP or Playwright against the running dev/preview server:

1. **360px mobile check (`360x800`)**: Navigate to every modified route. Verify `document.documentElement.scrollWidth <= document.documentElement.clientWidth` (zero horizontal overflow), verify meta/timestamp rows wrap cleanly between `whitespace-nowrap` fragments, and confirm primary CTAs require zero horizontal scrolling.
2. **1280px desktop check (`1280x900`)**: Exercise interactive states (tab switches, `.voxel-trough` click/keyboard `Enter`/`Space` inspection, empty/error states).
3. **Console & network audit**: Confirm zero uncaught console errors, zero React hydration mismatches, and zero unexpected `4xx`/`5xx` or `PGRST205` responses.
