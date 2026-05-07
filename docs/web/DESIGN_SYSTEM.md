# Design System

## Design Philosophy

**"Bloomberg Terminal Meets Wired Magazine"** — data-dense but readable, motion with purpose, distinctive typography.

## Typography

| Usage | Font | Source |
|-------|------|--------|
| Headlines | Space Grotesk (400-700) | Google Fonts |
| Body | Satoshi (300-900) | Google Fonts |
| Data/Mono | JetBrains Mono (400-600) | Google Fonts |

Type scale: `text-7xl` to `text-[9px]`. Headlines use `-0.02em` letter spacing. Uppercase labels use `0.1em`.

## Colors

| Name | Hex | Usage |
|------|-----|-------|
| Electric Blue | `#2563EB` | Primary actions, links, hero gradients |
| Neon Green | `#16A34A` | BUY signals, positive metrics, live indicators |
| Alert Red | `#DC2626` | SELL signals, rejections, warnings |
| Deep Purple | `#9333EA` | AI cognition, consensus insights |
| Cyber Yellow | `#CA8A04` | Catalysts, countdown timers |

Dark mode: all colors defined with `dark:` variants. Backgrounds: `bg-white dark:bg-zinc-900`, text: `text-zinc-900 dark:text-zinc-100`.

## Semantic Gradients

```
electric:   linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)   → Primary actions, heroes
success:    linear-gradient(135deg, #16A34A 0%, #22C55E 100%)   → BUY signals
alert:      linear-gradient(135deg, #DC2626 0%, #EF4444 100%)   → SELL signals
catalyst:   linear-gradient(135deg, #CA8A04 0%, #EAB308 100%)   → Horizon Watch
ai:         linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)   → Cognitive insights
```

## Component Patterns

### Primitives

**Button** — Props: `variant` (solid/outline/ghost/soft/glass), `size` (sm/md/lg), `colorScheme` (accent/success/danger/info/warning/neutral), `rounded` (xl/full), `gradient` (boolean), `isLoading`, `leftIcon`, `rightIcon`.

**Card** — Composable: `Card`, `CardHeader`, `CardBody`, `CardFooter`. Props: `variant` (default/elevated/outlined/ghost/glass), `padding` (none/sm/md/lg), `gradient` (electric/success/alert/catalyst/ai), `accentBorder` (none/left/top), `accentBorderColor` (accent/success/danger/info/warning).

**Badge** — Props: `variant` (solid/soft/outline/dot), `size` (sm/md), `colorScheme` (accent/success/danger/info/warning/neutral), `severity` (critical/high/medium/low), `radius` (full/lg/md).

**Cards**: Rounded-3xl with border, subtle shadow, hover lift (`translateY(-4px)`, `0.3s cubic-bezier`).

**Badges**: Colored pills with `text-[9px] font-black uppercase tracking-widest`. Importance levels: Critical (red), High (yellow), Medium (blue).

### Patterns

**SectionHeading** — Section title with gradient decorator bar and gradient text. Props: `gradient` (electric/success/catalyst/ai/alert), `children`, `className`.

**ConfidenceBar** — Labelled progress bar (0-100%). Props: `label`, `value`, `colorScheme` (accent/success/danger/info/warning), `textStyle` (default/hero), `className`. `textStyle="hero"` switches to white/translucent palette for dark gradient backgrounds.

**StatPill** — Pill-shaped filter button with colored dot, label, and count. Props: `label`, `value`, `colorScheme` (accent/success/danger/info/warning/neutral), `isActive`, `onClick`, `className`.

**MetricTile** — Small stat card with icon, label, and value. Props: `icon`, `label`, `value`, `className`.

**EmptyState** — Empty state with emoji, title, subtitle, action buttons.

### Color-Coded Elements

Components that map a `colorScheme` prop to a specific color (e.g., `ConfidenceBar` fill, `StatPill` dot) use **inline `style={{ backgroundColor }}`** with values from `semanticTokens` exported by the design system, rather than Tailwind `bg-*` classes. This avoids Tailwind v4 class-generation issues when color tokens are defined in `@theme inline`.

### Layouts

**PageLayout** — Standard page wrapper with padding and max-width. Props: `maxWidth`, `withPadding`.

**HeroBackground** — Gradient hero banner with dot-pattern overlay and animated blur orbs. Props: `gradient` (electric/success/alert/catalyst/ai).

**Agent Pills**: Color-coded with emoji (🟢 OpenAI, 🟠 Claude, 🔵 Gemini, 🟣 DeepSeek).

**Timeline**: Vertical connecting line with dot markers, event cards with countdown timers.

**Expandable Cards**: Click-to-reveal pattern for detailed reasoning display.

## Motion

| Class | Effect |
|-------|--------|
| `animate-slide-up` | Fade in + translateY(30px→0) |
| `animate-scale-in` | Fade in + scale(0.95→1) |
| `animate-stagger-{1-5}` | 100ms–500ms staggered delays |
| `animate-float` | Gentle vertical motion (±10px, 3s) |
| `animate-pulse-glow` | Pulsing glow (2s) |
| `live-dot` | Green dot with pulse animation |

Hover effects use `card-lift` (translate + shadow) and `border-reveal` (gradient border on hover).

Hooks: `animate-slow-fade` for 1s fade-in. Always respect `prefers-reduced-motion`.

## Accessibility

- WCAG AA color contrast (4.5:1 minimum)
- `aria-expanded` / `aria-controls` on expandable sections
- `aria-hidden` on decorative icons
- Visible focus states on interactive elements
- `prefers-reduced-motion` disables all animations

## Key Files

- `apps/web/src/styles/app.css` — Design system CSS
- `packages/ui-design-system/src/` — Shared UI primitives
