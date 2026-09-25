---
description: Enforce fluent responsive layouts without explicit breakpoints or hardcoded pixel values
---

# Fluent layout and CSS overflow prevention

## Principles

Fluid and reactive layouts are substantially sturdier than explicit media query breakpoints. Explicit viewport breakpoints (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) and hardcoded pixel layout dimensions are fragile, tedious to maintain, and conflict with component-first design systems. When components are embedded inside split views, sidebars, or sub-panels, viewport media queries fail because they measure the entire screen rather than available container width.

Components must respond to the space allocated by their parent container using standard design system spacing tokens, relative `rem` units, and fluid CSS algorithms (`flex-wrap`, `auto-fit`).

## Mandatory layout rules

### 1. Zero explicit media query breakpoints

Do not use explicit Tailwind viewport breakpoints (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) or `@media (min-width: ...)` to control layout columns, stacking, or content wrapping.

- Use `flex-wrap` for elements that should sit side by side when space allows and stack when space is constrained.
- Use `repeat(auto-fit, minmax(...))` for grid layouts that should adjust column counts dynamically based on available width.

### 2. Zero hardcoded pixel values in layouts

Do not use raw pixel dimensions (`280px`, `340px`, `500px`) for layout structures.

- Use design system spacing tokens (`gap-4`, `p-5`, `basis-72`, `basis-96`).
- Use relative `rem` units (`minmax(min(100%, 15rem), 1fr)`) so dimensions scale with root typography settings.

### 3. Fluid master-detail layouts

For two-column views (such as variant lineage sidebars with inspector panes), use proportional flex wrapping:

```tsx
<div className="flex flex-wrap gap-6 mt-4 items-start min-w-0 w-full">
  {/* Sidebar */}
  <div className="w-full flex-1 basis-72 min-w-0">
    <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1 min-w-0">
      ...
    </div>
  </div>

  {/* Detail pane */}
  <div className="w-full flex-[3] basis-96 min-w-0 flex flex-col gap-4">
    ...
  </div>
</div>
```

When container space is ample, the sidebar takes its compact base (`basis-72`), while the detail pane (`basis-96`, `flex-[3]`) absorbs available width. When space is constrained, `flex-wrap` stacks them cleanly at 100% width without abrupt breakpoint jumps.

### 4. Intrinsic auto-fit subgrids

Nested cards (such as toolbox registries, discipline blocks, and metric factor tiles) must calculate columns intrinsically:

```tsx
<div
  className="grid gap-3"
  style={{
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))',
  }}
>
```

This dynamically renders 1, 2, 3, or more columns based on the container width.

### 5. Fluid action bars and headers

Card and section headers must never force row or column transitions via breakpoints. Use `flex flex-wrap`:

```tsx
<div className="flex flex-wrap items-center justify-between gap-4">
  <SectionHeading>{title}</SectionHeading>
  <Badge variant="outline">{status}</Badge>
</div>
```

### 6. Zero minimum width and pre tag text wrapping

- Every flex child and grid track must declare `min-w-0` to override the browser `min-content` default sizing on `1fr` tracks.
- Every `<pre>` tag rendering prompt text, diffs, code, or logs must include `whitespace-pre-wrap break-words`. Never rely on `overflow-x-auto` alone.
- Unbroken technical tokens (snake_case identifiers like `tool_names` or prompt variant hashes) must include `break-all`.
- Mathematical formula bars must include `wordBreak: 'break-word'`, `overflowWrap: 'anywhere'`, and `overflowX: 'auto'`.
