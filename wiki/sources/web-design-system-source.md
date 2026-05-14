---
tags: [web, ui, design-system]
category: source
---

# Source: Web Design System

Synthesized from `raw/docs/web/DESIGN_SYSTEM.md` and current codebase at `packages/ui-design-system/`.

## Takeaways

- **"Bloomberg Terminal meets Wired"**: Aesthetics prioritize data density and readability with a semantic color palette (Electric Blue, Neon Green, Alert Red, Deep Purple, Cyber Yellow).
- **Fully adopted**: All 10 web app pages use the design system as their primary UI vocabulary. No page uses zero DS components (as of 2026-05-14 migration).
- **Component categories**:
  - **Primitives**: Button (5 variants), Card (5 variants), Badge (3 variants + severity), Input/Select/Skeleton, ErrorBoundary, LoadingSpinner
  - **Patterns**: SectionHeading, ConfidenceBar, StatPill, MetricTile, EmptyState, LoadingBoundary, ErrorCard
  - **Layouts**: PageLayout, HeroBackground
- **Cross-cutting consistency**: All "Load More" buttons use Button with isLoading, all error states use ErrorCard, all loading states use LoadingBoundary, all section titles use SectionHeading with semantic gradients.
- **Color consistency**: zinc palette used consistently across all pages (ReasoningPage was migrated from gray-* to zinc-*).
- **Hero deduplication**: MarketOverviewPage's hero was a raw copy-paste of HeroBackground — replaced with the actual component, removing 78 lines of duplicated code.
- **Simplicity over abstraction**: Prefers direct mapping of props to Tailwind classes rather than complex token layers, ensuring the build output is predictable and easy to debug.
- **Accessibility**: WCAG AA contrast ratios, visible focus states, aria labels.

## Related

- [[entities/web-app]]