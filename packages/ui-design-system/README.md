# @llm-market-bench/ui-design-system

Shared UI design system for the LLM Market Bench monorepo. Homegrown component library powered by Tailwind CSS v4 and the **Matcha & Cedar / Cheddar Voxel** aesthetic.

> [!IMPORTANT]
> The full design system rules, typography scale, responsive invariants, layout guidelines, and living-scene backdrop standards are codified in [`.agents/rules/design-spec.md`](../../.agents/rules/design-spec.md), [`wiki/entities/design-system.md`](../../wiki/entities/design-system.md), and [`wiki/concepts/living-scene-backdrops.md`](../../wiki/concepts/living-scene-backdrops.md).

## Philosophy

- **CSS-First Layout (Avoid JS for design)**: All layouts use declarative CSS Grid and Flexbox (`grid`, `flex`, `flex-wrap`, `items-stretch`). Zero JavaScript layout math (`ResizeObserver`, `window.innerWidth`). Zero inline `style={{ ... }}` objects for layout, typography, or colors.
- **Matcha & Cedar / Cheddar Voxel**: Tactile voxel hardware geometry (`rounded-none`, 2px directional bevels, hard 4px offset shadows, recessed `.voxel-trough` slots, and physical press `.voxel-btn`).
- **Strict 3-Combination Typography Budget**: Tier 1 (`18px Bold`), Tier 2 (`14px Bold`), and Tier 3 (`12px Normal`).
- **Parent-Owns-Spacing**: Zero manual child margins (`m-*`, `mb-*`, `mt-*`, `mr-*`, `ml-*`). Parents supply rhythm with `flex gap-*` and `grid gap-*` (`gap-2`, `gap-4`, `gap-6`).
- **WCAG AAA Contrast**: Solid Cheddar Gold tags use dark trough text (`text-voxel-trough`, never white).
- **Expressive Living-Scene Stages**: Multi-layered animated dioramas and bounded pointer/scroll parallax belong inside clipped hero and footer stages (`SceneStage`, `HeroBackground`) with opaque/semi-opaque Matcha CTA scrims (zero `backdrop-blur`), dynamic US market-session atmosphere phases (`dawn`, `daylight`, `dusk`, `after-hours`), and `prefers-reduced-motion` discipline.

## Adoption

All web app pages (Home, Today, Portfolios, Portfolio Detail, Market Overview, Memories, Reasoning, Audits, Cause & Effect, Concepts, Daily Predictions, Recipes, Lab) use the design system as their primary UI vocabulary.

## Exports

### Primitives

| Component | Props & Behavior |
|---|---|
| `Button` | Tactile `.voxel-btn` (`solid` \| `outline`) with 2px raised bevels, physical `translate(2px, 2px)` click depression, and `isLoading` Voxel pixel indicator. Tier 2 typography. |
| `Card` | Raised `.voxel-card` (`default` \| `outlined`) block with `rounded-none` geometry, stepped moss surface, and hard offset drop shadow. |
| `Badge` | Sharp `.voxel-badge` (`solid` \| `soft`) tag with optional square pixel dot indicator and built-in `gap-1.5` container spacing. |
| `Table` | Composable suite (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) inside a recessed `.voxel-trough` container with `numeric` alignment, `tone`, and `isInactive` states. |
| `Input` / `Label` | Recessed `.voxel-trough rounded-none` wrapper (`bg-voxel-trough`, `border-voxel-bevel-hi`). Tier 2 control typography. |
| `Select` | Recessed `.voxel-trough rounded-none` wrapper with design system styling and Tier 2 typography. |
| `Skeleton` | Sharp `rounded-none` Voxel trough placeholder (`text` \| `block` \| `card` variants) with reduced-motion pulse. |

### Patterns

| Component | Purpose |
|---|---|
| `SectionHeading` | Tier 1 display title with cheddar-gold square marker. |
| `SubHeading` | Tier 2 secondary heading with optional divider and right element. Zero manual margins. |
| `ConfidenceBar` | 10 discrete block segments inside a recessed `.voxel-trough` slot. |
| `StatPill` | Clickable filter pill with colored dot, label, and count. |
| `MetricTile` | Recessed `.voxel-trough rounded-none p-3` tile (`flex flex-col justify-between gap-1`). |
| `EmptyState` | Centered zero-data state with Tier 1 title, Tier 3 subtitle, and square icon box. |
| `LoadingBoundary` | Layout-preserving Voxel skeleton loading wrapper (`fallback` slot, zero spinners). |
| `ErrorCard` | Tactile error display card with Tier 2 title, Tier 3 message, and retry button. |

### Layouts

| Component | Purpose |
|---|---|
| `PageLayout` | Full-page container with max-width and declarative `flex flex-col gap-6` / `gap-8` spacing. |
| `GlobalBackground` | Deep Forest Moss canvas with subtle warm dot grid matrix. |
| `SceneStage` | Spatially contained Voxel stage for living-scene heroes (`hero`) and parallax footers (`footer`) with 4 Matcha atmosphere phases, `aria-hidden` backdrop layer, motion-role metadata, and optional `.scene-scrim` CTA panel. |
| `HeroBackground` | Sharp Voxel hero banner with CSS `.voxel-dot-matrix` texture, semantic Matcha overlays, fluid padding, and optional `atmosphere` / `backdrop` slots. |

### Utilities

| Export | Purpose |
|---|---|
| `cn` | `clsx`-based className utility (no `tailwind-merge`; always use explicit component props rather than overriding colors via `className`). |
| `resolveAtmospherePhase` / `ATMOSPHERE_PHASES` | Resolves `'dawn' \| 'daylight' \| 'dusk' \| 'after-hours'` using the US Eastern market session clock (`America/New_York`) by default or optional `'local'` visitor timezone mode. |

## Principles

- **Prefer Default System Props**: Always use closed component props (`colorScheme`, `variant`, `size`, `atmosphere`, `scrim`) rather than passing custom `className` color/typography overrides. Centralized props prevent visual fragmentation and enforce WCAG AAA contrast natively.
- **Single Unified Dark Theme**: Standardized under the single high-contrast **Matcha & Cedar / Cheddar Voxel** theme. Primitives contain zero `dark:` variants, zero `text-white`, and zero `backdrop-blur`.
- **Two-Variant Budget**: Interactive and surface primitives expose at most two style variants (`solid`/`outline`, `solid`/`soft`, `default`/`outlined`, `hero`/`footer`), enforced by `apps/web/src/test/design-variant-budget.test.tsx`.

## Usage

```tsx
import {
    Button,
    Card,
    Badge,
    SceneStage,
    SectionHeading,
    resolveAtmospherePhase,
    cn,
} from "@llm-market-bench/ui-design-system"
```

While components accept a `className` prop for occasional layout/positional adjustments, it should not be used to override base styling tokens like text colors, background colors, borders, or hover styles.

## Key Files

- `src/index.ts` — Public API barrel file
- `src/primitives/` — Low-level UI atoms
- `src/patterns/` — Composed UI patterns
- `src/layouts/` — Page shells, global canvas, and living-scene hero/footer stages
- `src/lib/` — `cn` and `atmosphere` utilities
