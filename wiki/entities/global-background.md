---
tags: [ui, design-system, global-background, layout]
category: entity
---

# Global Background

A fixed-position background component that renders the Deep Forest Moss canvas with a subtle warm dot-grid matrix across the entire application. Added to the root layout for consistent visual depth, replacing per-page backgrounds like the old CSS variant and ShaderBackground on the HomePage.

## Purpose

Before `GlobalBackground`, each page managed its own backdrop — the HomePage had an A/B test choosing between a pure CSS grid/glow combo and a WebGL `ShaderBackground`. This component centralizes the effect, ensuring every route shares the same subtle visual anchor without duplication.

## Implementation

- **Position:** `fixed inset-0` with `z-[-1]` so it sits behind all content.
- **Canvas:** `bg-boxel-canvas` (`#141c18`, Deep Forest Moss) fills the viewport.
- **Dot grid:** A repeating `radial-gradient(rgba(242, 234, 211, 0.25) 1px, transparent 1px)` with `background-size: 20px 20px` at 20% opacity creates a fine warm (Tatami Cream) dot pattern.
- **No interactivity:** `pointer-events-none` ensures clicks pass through to the actual UI.

## Usage

Imported from the design system and rendered once in the root layout (`__root.tsx`):

```tsx
import { GlobalBackground } from '@llm-market-bench/ui-design-system';

<GlobalBackground />
{children}
```

No props are required; the component is self-contained.

## Related

- [[entities/design-system]] — the shared UI component library this belongs to
- [[entities/web-app]] — the TanStack Start dashboard where it is used
