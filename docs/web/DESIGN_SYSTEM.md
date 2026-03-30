# Design System: AI Wall Street Dashboard

This document outlines the design system, visual language, and component patterns used throughout the AI Wall Street dashboard.

## 1. Design Philosophy

**"Bloomberg Terminal Meets Wired Magazine"**

Our design combines:
- **Financial Gravitas**: Trust, precision, authority
- **Tech-Forward Energy**: AI, real-time, cognitive
- **Editorial Storytelling**: Narrative flow, not just data cards

### Core Principles

1. **Data-Dense but Readable**: Show rich information without overwhelming
2. **Visual Hierarchy**: Clear distinction between critical vs. nice-to-know
3. **Motion with Purpose**: Animations that inform, not distract
4. **Distinctive Typography**: Custom fonts that stand out from generic SaaS
5. **Color with Meaning**: Every color signals specific semantic meaning

---

## 2. Typography

### Font Stack

| Usage | Font | Weights | Source |
|-------|------|---------|--------|
| **Headlines** | Space Grotesk | 400, 500, 600, 700 | Google Fonts |
| **Body** | Satoshi | 300, 400, 500, 700, 900 | Google Fonts |
| **Data/Mono** | JetBrains Mono | 400, 500, 600 | Google Fonts |

### Type Scale

```css
/* Display / Hero */
text-7xl / text-8xl  →  72px / 96px  (H1, Page Titles)
text-6xl             →  60px          (Section Headers)

/* Headlines */
text-3xl             →  30px          (Section Titles)
text-2xl             →  24px          (Card Titles)
text-xl              →  20px          (Subtitle)

/* Body */
text-lg              →  18px          (Lead paragraphs)
text-base            →  16px          (Body copy)
text-sm              →  14px          (Secondary text)

/* Micro */
text-xs              →  12px          (Captions, badges)
text-[10px]          →  10px          (Labels, timestamps)
text-[9px]           →  9px           (Tags, metadata)
```

### Letter Spacing

- **Headlines**: `-0.02em` (tight, modern)
- **Body**: `normal`
- **Uppercase Labels**: `0.1em` (improved readability)
- **Tracking-Widest**: `0.2em` (for micro-labels)

---

## 3. Color System

### Primary Colors

| Name | Hex | Usage |
|------|-----|-------|
| **Electric Blue** | `#2563EB` | Primary actions, links, hero gradients, trust signals |
| **Neon Green** | `#16A34A` | BUY signals, positive metrics, live indicators, gains |
| **Alert Red** | `#DC2626` | SELL signals, rejections, warnings, losses |
| **Deep Purple** | `#9333EA` | AI cognition, consensus insights, agent avatars |
| **Cyber Yellow** | `#CA8A04` | Catalysts, countdown timers, attention grabbers |

### Neutral Palette

| Name | Hex | Usage |
|------|-----|-------|
| **Void 950** | `#020617` | Deep backgrounds (dark mode) |
| **Zinc 950** | `#09090B` | Card backgrounds (dark mode) |
| **Zinc 900** | `#18181B` | Primary text (dark mode) |
| **Zinc 500** | `#64748B` | Secondary text |
| **Zinc 400** | `#94A3B8` | Tertiary text, placeholders |
| **Zinc 200** | `#E4E4E7` | Borders (light mode) |
| **Zinc 100** | `#F4F4F5` | Card backgrounds (light mode) |
| **Zinc 50** | `#FAFAFA` | Page background (light mode) |

### Semantic Gradients

```css
/* Electric Gradient - Primary actions, heroes */
gradient-electric: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)

/* Success Gradient - BUY signals, positive metrics */
gradient-success: linear-gradient(135deg, #16A34A 0%, #22C55E 100%)

/* Alert Gradient - SELL signals, warnings */
gradient-alert: linear-gradient(135deg, #DC2626 0%, #EF4444 100%)

/* Catalyst Gradient - Horizon Watch, countdowns */
gradient-catalyst: linear-gradient(135deg, #CA8A04 0%, #EAB308 100%)

/* AI Gradient - Cognitive insights, agent branding */
gradient-ai: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)
```

---

## 4. Component Patterns

### Cards

**Base Card:**
```tsx
<div className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-xl transition-all duration-300 card-lift">
  {/* Content */}
</div>
```

**Card Variants:**
- **Standard**: White/dark background with subtle shadow
- **Gradient Border**: `border-reveal` class for hover-activated gradient borders
- **Glass**: `glass` class for backdrop blur overlays
- **Section-Specific**: Left border color coding (green=trades, purple=insights, yellow=catalysts)

### Badges & Pills

**Importance Badges:**
```tsx
/* Critical */
<span className="px-3 py-1 bg-alert-red-50 dark:bg-alert-red-950/20 text-alert-red-600 dark:text-alert-red-400 text-[9px] font-black uppercase tracking-widest rounded-lg">
  CRITICAL
</span>

/* High */
<span className="px-3 py-1 bg-cyber-yellow-50 dark:bg-cyber-yellow-950/20 text-cyber-yellow-600 dark:text-cyber-yellow-400 text-[9px] font-black uppercase tracking-widest rounded-lg">
  HIGH
</span>

/* Medium */
<span className="px-3 py-1 bg-electric-blue-50 dark:bg-electric-blue-950/20 text-electric-blue-600 dark:text-electric-blue-400 text-[9px] font-black uppercase tracking-widest rounded-lg">
  MEDIUM
</span>
```

**Agent Pills:**
```tsx
<div className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg">
  <span className="text-lg">🟢</span> {/* OpenAI */}
  <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">
    OpenAI
  </span>
</div>
```

### Buttons

**Primary Button:**
```tsx
<button className="px-6 py-3 bg-electric-blue-600 hover:bg-electric-blue-700 text-white font-bold rounded-xl transition-all card-lift">
  Action Text
</button>
```

**Secondary Button:**
```tsx
<button className="px-6 py-3 bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-800 hover:border-electric-blue-500 text-zinc-900 dark:text-white font-bold rounded-xl transition-all card-lift">
  Secondary Action
</button>
```

---

## 5. Motion & Animation

### Animation Classes

```css
/* Page Load */
.animate-slide-up    → Fade in + translateY(30px → 0)
.animate-scale-in    → Fade in + scale(0.95 → 1)
.animate-slow-fade   → Simple fade in (1s)

/* Staggered Reveals */
.animate-stagger-1   → 100ms delay
.animate-stagger-2   → 200ms delay
.animate-stagger-3   → 300ms delay
.animate-stagger-4   → 400ms delay
.animate-stagger-5   → 500ms delay

/* Continuous */
.animate-float       → Gentle vertical motion (±10px, 3s)
.animate-pulse-glow  → Pulsing glow effect (2s)
.animate-shimmer     → Loading shimmer (2s)

/* Live Indicators */
.live-dot            → 8px green dot with pulse animation
```

### Hover Effects

**Card Lift:**
```css
.card-lift {
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
}
.card-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
}
```

**Border Reveal:**
```css
.border-reveal::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.border-reveal:hover::before {
  opacity: 1;
}
```

---

## 6. Layout Patterns

### Today Page Structure

```
┌─────────────────────────────────────────┐
│  Market Status Hero (Full-width)        │
│  - Gradient background                  │
│  - Market status + AI sentiment         │
│  - Quick stats badges                   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  AI Cognitive Synthesis                 │
│  - Consensus meter                      │
│  - Agent avatars                        │
│  - Gradient insight cards               │
└─────────────────────────────────────────┘
              ↓
┌──────────────┬──────────────┐
│  Newsletter  │  Newsletter  │
│  Card        │  Card        │
└──────────────┴──────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Market Execution & Guardrails          │
│  - Activity stats pills                 │
│  - Expandable trade cards               │
│  - Agent attribution                    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Horizon Watch (Timeline)               │
│  - Vertical timeline line               │
│  - Event cards with countdowns          │
│  - Scenario analysis                    │
└─────────────────────────────────────────┘
```

### Spacing System

- **Section Gap**: `space-y-24` (96px between sections)
- **Card Gap**: `gap-4` (16px between cards in grids)
- **Internal Padding**: `p-6` (24px) for standard cards
- **Page Padding**: `px-6 md:px-12 py-12` (responsive horizontal, 48px vertical)

### Grid Systems

**2-Column Grid (Newsletters):**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  {/* Cards */}
</div>
```

**Responsive Grid (Market Updates):**
```tsx
<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
  {/* Cards */}
</div>
```

---

## 7. Component Examples

### Stat Badge
```tsx
<div className="flex items-center gap-3 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-xl border border-white/20">
  <span className="text-2xl">📰</span>
  <div>
    <div className="text-2xl font-black text-white">12</div>
    <div className="text-[10px] text-electric-blue-200 uppercase tracking-wider font-bold">
      Newsletters
    </div>
  </div>
</div>
```

### Countdown Timer
```tsx
<div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-cyber-yellow-100 to-amber-100 dark:from-cyber-yellow-900/30 dark:to-amber-900/30 text-cyber-yellow-700 dark:text-cyber-yellow-300 text-xs font-black rounded-lg border border-cyber-yellow-200 dark:border-cyber-yellow-800">
  <span className="text-lg">⏱️</span>
  <span className="font-mono">2d 14h 35m</span>
</div>
```

### Timeline Event
```tsx
<div className="relative pl-20">
  {/* Timeline Dot */}
  <div className="absolute left-6 top-6 w-5 h-5 rounded-full border-4 border-white dark:border-zinc-950 shadow-lg bg-gradient-to-br from-cyber-yellow-500 to-amber-600 z-10" />
  
  {/* Card */}
  <div className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm">
    {/* Content */}
  </div>
</div>
```

---

## 8. Accessibility

### Color Contrast
- All text meets **WCAG AA** standards (4.5:1 minimum)
- Large text (18px+) meets **3:1** minimum
- Interactive elements have visible focus states

### Motion Preferences
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Screen Reader Support
- All interactive elements have descriptive labels
- Icons used decoratively are marked `aria-hidden`
- Expandable sections use `aria-expanded` and `aria-controls`

---

## 9. Dark Mode

All colors are defined with dark mode variants:

```css
/* Light Mode */
bg-white dark:bg-zinc-900
text-zinc-900 dark:text-zinc-100
border-zinc-200 dark:border-zinc-800

/* Gradient Backgrounds */
from-electric-blue-100 dark:from-electric-blue-950/30
to-deep-purple-100 dark:to-deep-purple-950/30
```

---

## 10. Files & Locations

```
apps/web/
├── src/
│   ├── styles/
│   │   └── app.css          # Main design system (CSS variables, utilities)
│   ├── components/
│   │   ├── today/           # Today page components
│   │   │   ├── MarketStatusHero.tsx
│   │   │   ├── AgentInsights.tsx
│   │   │   ├── TradeActivity.tsx
│   │   │   ├── FutureCatalysts.tsx
│   │   │   └── NewsletterFeed.tsx
│   │   └── ui/              # Reusable UI primitives
│   └── routes/
│       └── index.tsx        # Today page composition
└── docs/
    └── web/
        ├── README.md        # Architecture overview
        └── DESIGN_SYSTEM.md # This file
```

---

## 11. Best Practices

### DO ✅
- Use semantic color names (electric-blue, not "blue-600")
- Apply motion with purpose (inform, don't distract)
- Maintain visual hierarchy (headlines > body > micro)
- Test in both light and dark modes
- Use proper typography scale (don't hardcode font sizes)

### DON'T ❌
- Use generic system fonts (Arial, Inter)
- Add animations without purpose
- Create new color values (use the design system)
- Hardcode spacing values (use Tailwind scale)
- Ignore dark mode compatibility

---

**Last Updated:** March 27, 2026  
**Version:** 2.0 (Major redesign with custom typography and color system)
