---
tags: [ui, design-system, global-background, layout]
category: entity
---

# Global Background

A fixed-position background component that renders ambient glowing orbs and a dot grid pattern across the entire application. Added to the root layout for consistent visual depth, replacing per-page backgrounds like the old CSS variant and ShaderBackground on the HomePage.

## Purpose

Before `GlobalBackground`, each page managed its own backdrop — the HomePage had an A/B test choosing between a pure CSS grid/glow combo and a WebGL `ShaderBackground`. This component centralizes the effect, ensuring every route shares the same subtle visual anchor without duplication.

## Implementation

- **Position:** `fixed inset-0` with `z-[-1]` so it sits behind all content.
- **Orbs:** Three radial gradients at top-right (`rgba(0,242,254,0.1)`), bottom-left (`rgba(74,222,128,0.07)`), and center (`rgba(246,224,94,0.05)`) cast colored ambient light without overwhelming the layout.
- **Dot grid:** A repeating `radial-gradient(rgba(255,255,255,0.4) 1px, transparent 1px)` with `background-size: 24px 24px` creates a fine dot pattern at 40% opacity.
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
