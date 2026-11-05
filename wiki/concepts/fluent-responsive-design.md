---
tags: [ui, design-system, responsive, css, layout]
category: concept
---

# Fluent responsive design

Fluent responsive design builds interfaces that adapt to available container width without explicit viewport media query breakpoints. Rigid screen breakpoints like `sm:`, `md:`, and `lg:` make components fragile when nested inside multi-column panels or sidebars. Intrinsic fluid algorithms like `flex-wrap` and `auto-fit` grids let components flow naturally across all device sizes and split-screen layouts.

The canonical, authoritative statement of these rules (together with the typography budget, boxel geometry, spacing, CLS, and overflow rules) lives in `.agents/rules/design-spec.md`. This page explains the reasoning behind the layout half of that specification.

## Core principles

### 1. Breakpoints break component isolation

Media queries evaluate viewport dimensions, not the width of the component's container. When a component that expects 1200px of viewport width is placed inside a 600px detail column next to a sidebar, viewport-based `lg:` rules trigger desktop multi-column layouts prematurely. This squashes cards into narrow strips and causes horizontal overflow.

Container-first fluid design uses the available space of the immediate parent element, eliminating layout mismatch.

### 2. Zero explicit breakpoints

Do not use viewport utility breakpoints (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) or `@media (min-width: ...)` to toggle column structures or stacking modes.

- Use `flex-wrap` for elements that should sit side by side when space allows and wrap when space is constrained.
- Use CSS Grid with `repeat(auto-fit, minmax(...))` for card grids where column counts scale smoothly with container width.

### 3. Zero hardcoded pixel layout values

Avoid hardcoded pixel values (`280px`, `340px`, `500px`) for structural layouts.

- Use relative `rem` units (`minmax(min(100%, 15rem), 1fr)`) so layout scales proportionally with user font preferences.
- Use design system spacing tokens (`p-5`, `gap-4`, `gap-6`, `basis-72`, `basis-96`).

### 4. CSS-first, not JS-first

Layout, responsive wrapping, and visual state belong to the browser's CSS layout engine. Never compute column counts, element dimensions, or stacking modes in JavaScript (`window.innerWidth`, `matchMedia`, `ResizeObserver`), and never pass layout, typography, or color values through inline `style={{ ... }}` objects. The only permitted inline style is a continuous dynamic data percentage (e.g. a progress-bar fill).

## Implementation patterns

### Proportional master-detail flexbox

For dual-pane layouts (such as experiment lineage lists paired with prompt inspectors):

```tsx
<div className="flex flex-wrap gap-6 mt-4 items-start min-w-0 w-full">
  {/* Sidebar */}
  <div className="w-full flex-1 basis-72 min-w-0">
    <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1 min-w-0">
      {/* List items */}
    </div>
  </div>

  {/* Detail pane */}
  <div className="w-full flex-[3] basis-96 min-w-0 flex flex-col gap-4">
    {/* Detail cards */}
  </div>
</div>
```

- On wide viewports, the sidebar anchors at `basis-72` (18rem). The detail pane has `flex-[3]` and absorbs extra horizontal room.
- On constrained viewports, total width exceeds available container space, prompting `flex-wrap` to stack both elements at 100% width cleanly.

### Intrinsic auto-fit subgrids

For card catalogs, tool registries, and metric tiles, express the intrinsic grid as a Tailwind arbitrary grid-track utility rather than an inline `style` object, so the layout stays declarative and consistent with the rest of the design system:

```tsx
<div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,15rem),1fr))] gap-3 items-stretch">
  {items.map((item) => (
    <div key={item.id} className="min-w-0 overflow-hidden h-full">
      ...
    </div>
  ))}
</div>
```

- When available width is 20rem, 1 column renders.
- When available width reaches 32rem, 2 columns render.
- When available width reaches 48rem, 3 columns render.
- Zero viewport media queries are evaluated.

The `minmax(min(100%, Xrem), 1fr)` track guarantees a single column never overflows a narrow container (the `min(100%, …)` floor) while still expanding to fill wider containers. Common track floors in the codebase: `10rem` (dense metric tiles), `12rem`/`14rem` (stat cards), `15rem`/`16rem` (tool and model cards), `18rem`/`20rem` (portfolio and comparison cards).

### Equal-height stretched grids

When sibling cards must share identical height (scoreboards, podiums, comparison panels, the Today page's 3-column row), pair the intrinsic grid with `items-stretch` and give each card `h-full flex flex-col justify-between`:

```tsx
<div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-6 items-stretch">
  <Card className="h-full flex flex-col justify-between gap-4">...</Card>
</div>
```

This replaces the older `items-end` / arbitrary `min-h-[...]` podium pattern: cards no longer need hardcoded heights to look aligned, and the tallest card in the row sets the shared height intrinsically.

### Fluid action toolbars

Replace breakpoint-dependent direction toggles like `flex-col sm:flex-row` with fluid flex wrapping:

```tsx
<div className="flex flex-wrap items-center justify-between gap-4">
  <SectionHeading>{title}</SectionHeading>
  <Badge variant="outline">{count} Active</Badge>
</div>
```

## Related

- [[entities/design-system]], UI primitive and pattern library
- [[concepts/cumulative-layout-shift]], Zero layout shift standards and skeleton-free transitions
- [[entities/daily-market-predictor]], Daily predictor and autoresearch workbench
- [[entities/daily-score-breakdown]], Multi-pillar composite ratchet score audit
### Mobile text rows

Rows of labels, timestamps, and handles (for example the console queue card's "Latest Answered Turn" row) must wrap as whole fragments: `flex flex-wrap items-baseline gap-x-2 gap-y-1`, `whitespace-nowrap` on each label, timestamp, and `•` separator, and `min-w-0 truncate` on handles. A `justify-between items-center` row without `flex-wrap` squeezes its groups on narrow screens and splits labels from values mid-phrase. Full rules: section 9 of `.agents/rules/design-spec.md`.

