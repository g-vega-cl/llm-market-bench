---
tags: [ui, design-system, responsive, css, layout]
category: concept
---

# Fluent responsive design

Fluent responsive design builds interfaces that adapt to available container width without explicit viewport media query breakpoints. Rigid screen breakpoints like `sm:`, `md:`, and `lg:` make components fragile when nested inside multi-column panels or sidebars. Intrinsic fluid algorithms like `flex-wrap` and `auto-fit` grids let components flow naturally across all device sizes and split-screen layouts.

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

For card catalogs, tool registries, and metric tiles:

```tsx
<div
  className="grid gap-3"
  style={{
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))',
  }}
>
  {items.map((item) => (
    <div key={item.id} className="min-w-0 overflow-hidden">
      ...
    </div>
  ))}
</div>
```

- When available width is 20rem, 1 column renders.
- When available width reaches 32rem, 2 columns render.
- When available width reaches 48rem, 3 columns render.
- Zero viewport media queries are evaluated.

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
- [[entities/daily-market-predictor]], Daily predictor and autoresearch workbench
- [[entities/daily-score-breakdown]], Multi-pillar composite ratchet score audit
