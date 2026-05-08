---
tags: [source, web, design, visuals]
category: source
source: docs/web/DESIGN_SYSTEM.md
---

# Source: Web Design System

"Bloomberg Terminal Meets Wired Magazine" — data-dense but readable, motion with purpose.

Key details:

- **Typography**: Space Grotesk (headlines), Satoshi (body), JetBrains Mono (data/mono)
- **Colors**: Electric Blue (#2563EB), Neon Green (#16A34A, BUY), Alert Red (#DC2626, SELL), Deep Purple (#9333EA, AI), Cyber Yellow (#CA8A04, catalysts)
- **Semantic gradients**: electric, success, alert, catalyst, ai — used for heroes, signals, insights
- **Primitives**: Button (5 variants), Card (5 variants + accent borders), Badge (3 variants, severity levels)
- **Patterns**: SectionHeading, ConfidenceBar, StatPill, MetricTile, EmptyState, HeroBackground, Agent Pills, Timeline
- **Motion**: slide-up, scale-in, staggered delays (100-500ms), float, pulse-glow, live-dot — all respect prefers-reduced-motion
- **Accessibility**: WCAG AA (4.5:1), aria labels, focus states, prefers-reduced-motion
- **Design philosophy**: Dynamically-colored elements map `colorScheme` directly to physical Tailwind class names — no token abstraction layer
