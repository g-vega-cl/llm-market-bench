---
tags: [ui, design-system, interaction, accessibility, tooltips, inspection]
category: concept
---

# In-Flow Inspection (Zero Floating Tooltips)

Floating tooltips, popovers, poppers, and hover overlays are banned across `apps/web` and `@llm-market-bench/ui-design-system`. Secondary telemetry and point-level detail must render **in-flow** inside a recessed `.voxel-trough` slot, a contextual inspector bar, or a bottom drawer. This is codified as section 10 of `.agents/rules/design-spec.md` and as a mandatory bullet in `GEMINI.md`.

## Why floating overlays are banned

1. **Data occlusion** — a tooltip hovering over a chart or table hides the adjacent time-series or market values the user is trying to compare. The information being inspected is destroyed by the act of inspecting it.
2. **Visual jitter and layout flicker** — hover-triggered overlays appear and disappear on sub-pixel pointer movement, producing flicker that reads as instability in a financial dashboard.
3. **Touch and mobile failure** — hover has no equivalent on touch devices. A tooltip-only interaction is simply unreachable on a phone or tablet.
4. **Keyboard and WCAG failure** — native `title` attributes and SVG `<title>` hovers are not reliably announced, cannot be dismissed, and are not focusable. They fail keyboard accessibility standards outright.

## The mandated pattern

Secondary detail renders in a dedicated, always-present region of the layout:

- **Recessed `.voxel-trough` slot** — the same carved-slot surface used for metric tiles and formula blocks. Detail text uses Tier 3 typography (`text-xs font-normal`).
- **Contextual inspector bar** — a horizontal strip adjacent to the visualization that swaps its contents as the selection changes.
- **Bottom drawer** — for larger payloads (audit JSON, price verification blocks) that would otherwise be a modal.

### Interactive markers must be keyboard-operable

Chart markers and data points that drive the inspector are real controls, not hover targets:

```tsx
<button
  type="button"
  tabIndex={0}
  role="button"
  aria-label={`Inspect ${label} on ${date}`}
  onClick={() => setSelected(point)}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') setSelected(point)
  }}
  className="rounded-none border-boxel-bevel-hi bg-boxel-surface"
/>
```

Selection toggles or updates the trough slot; nothing floats above the canvas.

## Design-time enforcement

Agents and developers must check UI proposals against `.agents/rules/design-spec.md` **before** suggesting an interaction model in `/plan` or `/grill-me`. Banned patterns (tooltips, modals, accordions) must never be proposed during feature design or user interviews, and legacy code snippets or external library conventions are never design canon without cross-checking the spec.

## Related

- [[entities/design-system]] — boxel primitives, `.voxel-trough`, and the full rule cheat sheet
- [[entities/agent-rules]] — `GEMINI.md` mandate list
- [[concepts/fluent-responsive-design]] — layout half of the same design specification
- [[concepts/cumulative-layout-shift]] — zero layout shift standards
