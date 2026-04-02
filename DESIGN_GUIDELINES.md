# Benchify Design Guidelines

## Visual Thesis

**"A Bloomberg Terminal meets academic journal"** — Discreet, information-dense, professional interfaces that prioritize readability and credibility over visual flair. Think: financial research platform, science publication, or enterprise analytics tool that you'd comfortably use in a boardroom or library.

---

## Core Principles

### 1. **Invisible Design**
The best design disappears. Users should remember the *data*, not the *interface*.
- No decorative gradients, orbs, or blur effects
- No animations that draw attention to themselves
- No visual elements that exist purely for aesthetics

### 2. **Workplace Appropriate**
Design for open tabs at work. Nothing should feel like a consumer app, game, or marketing site.
- Conservative color palette (grays, blues, whites)
- No neon colors, no high-contrast accent combinations
- No playful micro-interactions or bouncy animations

### 3. **Information Hierarchy**
Dense but scannable. Professional users need efficiency, not hand-holding.
- Typography does the heavy lifting (weight, size, color)
- Consistent spacing system (4px grid)
- Clear visual separation without excessive borders

### 4. **Credibility Through Restraint**
Every visual element should justify its existence.
- If it doesn't improve readability or usability, remove it
- Prefer understated confidence over enthusiastic design
- Trust the content to carry the page

---

## Typography

### Font Stack
```css
--font-body: 'Satoshi', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'SF Mono', Monaco, monospace;
```

**No display fonts.** No decorative typefaces. The body font should work for both UI and headings (with weight/size variation).

### Type Scale
| Element | Size | Weight | Line Height | Color |
|---------|------|--------|-------------|-------|
| Page Title | 24px | 600 | 1.2 | zinc-900 |
| Section Heading | 16px | 600 | 1.3 | zinc-700 |
| Body | 14px | 400 | 1.5 | zinc-800 |
| Caption/Meta | 12px | 400 | 1.4 | zinc-500 |
| Code/Data | 13px | 400 | 1.4 | zinc-700 |

### Typography Rules
- **No all-caps headings** (except for short labels/badges)
- **No letter-spacing** for uppercase text (tracking-wider is acceptable for small badges)
- **No gradient text** ever
- **No font-weight below 400** (light text reduces readability)
- **Line height 1.4–1.6** for body text (readability over density)

---

## Color Palette

### Primary Colors
| Name | Light | Dark | Usage |
|------|-------|------|-------|
| Background | `#ffffff` | `#09090b` | Page background |
| Surface | `#f9fafb` | `#18181b` | Cards, panels |
| Border | `#e4e4e7` | `#27272a` | Dividers, strokes |
| Text Primary | `#18181b` | `#f4f4f5` | Headings, primary text |
| Text Secondary | `#71717a` | `#a1a1aa` | Meta, captions |
| Text Tertiary | `#a1a1aa` | `#52525b` | Placeholder, disabled |

### Accent Colors (Use Sparingly)
| Name | Value | Usage |
|------|-------|-------|
| Blue | `#2563eb` | Links, active states, primary actions |
| Green | `#16a34a` | Positive values, bullish indicators |
| Red | `#dc2626` | Negative values, bearish indicators |
| Amber | `#d97706` | Warnings, neutral indicators |

### Color Rules
- **One accent color per view** (blue for navigation/primary, green/red for data)
- **No gradient backgrounds** ever
- **No colored shadows** (use `box-shadow: 0 1px 2px rgba(0,0,0,0.05)`)
- **No opacity-based color mixing** (use solid colors)
- **Dark mode is desaturated** (reduce saturation by 20-30%)

---

## Layout & Spacing

### Container Widths
| Breakpoint | Max Width | Padding |
|------------|-----------|---------|
| Mobile | 100% | 16px |
| Tablet | 100% | 24px |
| Desktop | 1024px | 32px |
| Wide | 1280px | 48px |

**No `max-w-5xl`, `max-w-7xl`** — use specific pixel values or `max-w-4xl` (896px) for reading-heavy views.

### Spacing Scale
Use Tailwind's default spacing scale. Key values:
- `gap-2` (8px) — Tight lists, inline elements
- `gap-4` (16px) — Standard component spacing
- `gap-6` (24px) — Section spacing
- `gap-8` (32px) — Large section separation
- `gap-12` (48px) — Major content divisions

### Layout Rules
- **Consistent padding** — Same padding on all sides of a container
- **Align to grid** — All elements align to 4px baseline
- **No overlapping elements** — Avoid negative margins for layout
- **No absolute positioning** for content (only for UI overlays)

---

## Components

### Cards
**Default: No cards.** Use cards only when:
- The content is interactive (clickable entire area)
- There's a clear boundary needed (table, isolated data)
- The card itself is the interaction unit

When cards are necessary:
```tsx
<div className="border border-zinc-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-zinc-900 p-4">
  {/* No shadow by default */}
  {/* No hover lift effect */}
  {/* Border only, no additional decoration */}
</div>
```

### Buttons
```tsx
// Primary
<button className="px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-md text-sm font-medium hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors">
  Action
</button>

// Secondary
<button className="px-4 py-2 border border-zinc-200 dark:border-zinc-800 rounded-md text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors">
  Cancel
</button>
```

**Button Rules:**
- No gradient backgrounds
- No shadows (except subtle hover)
- No rounded-full (use `rounded-md` or `rounded-lg`)
- No animated icons (static or subtle transition only)

### Tables
```tsx
<table className="w-full text-left border-collapse">
  <thead>
    <tr className="border-b border-zinc-200 dark:border-zinc-800">
      <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-normal">Header</th>
    </tr>
  </thead>
  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
    <tr>
      <td className="px-4 py-3 text-sm text-zinc-900">Content</td>
    </tr>
  </tbody>
</table>
```

**Table Rules:**
- No rounded corners on tables (sharp edges = serious data)
- No alternating row colors (use borders only)
- Minimal padding (dense information display)
- Uppercase headers with `tracking-normal` (no wide letter-spacing)

### Badges / Tags
```tsx
<span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
  Label
</span>
```

**Badge Rules:**
- No bright colors (use gray scale for most)
- Green/red only for positive/negative status
- No icons unless essential
- Small and unobtrusive

---

## Motion & Animation

### Philosophy
**Motion should be felt, not seen.** Animations exist to:
- Smooth transitions (prevent jarring changes)
- Indicate state changes (loading, success, error)
- Guide attention (subtle focus indicators)

### Approved Animations
```css
/* Fade in on load - 150ms */
.animate-in.fade-in.duration-150

/* Subtle scale on modal - 200ms */
.animate-in.zoom-in-95.duration-200

/* Slide up for lists - 200ms */
.animate-in.slide-in-from-bottom-2.duration-200
```

### Animation Rules
- **Duration: 150-200ms** (fast, professional)
- **Easing: `ease-out` or `cubic-bezier(0.16, 1, 0.3, 1)`** (natural deceleration)
- **No infinite animations** (no spinning, pulsing, floating)
- **No stagger delays** (everything loads together)
- **No hover transformations** (no scale, no lift, no bounce)
- **No scroll-triggered animations** (content appears when scrolled to)

---

## Content & Copy

### Tone
- **Factual, not enthusiastic** — "Market data updated" not "🚀 Market insights are live!"
- **Concise, not clever** — Direct language over wordplay
- **Consistent, not varied** — Same terminology throughout

### Copy Rules
- **No emojis** in UI (except maybe status indicators)
- **No exclamation marks** (periods are fine)
- **No marketing language** ("revolutionary", "game-changing", "unlock")
- **No design commentary** ("beautifully crafted", "stunning visuals")
- **Section headers describe function** ("Trade Activity", "Performance") not mood ("Your Trading Journey")

### Examples
| ❌ Avoid | ✅ Use |
|----------|--------|
| "🎯 Discover AI-powered insights!" | "Analysis Results" |
| "Your trading journey starts here" | "Recent Trades" |
| "Unlock the power of collective intelligence" | "Consensus Data" |
| "Beautifully visualize your portfolio" | "Portfolio Performance" |

---

## What To Avoid

### Visual Elements
- [ ] Gradient backgrounds
- [ ] Decorative blur effects / "orbs"
- [ ] Grid patterns as decoration
- [ ] Colored shadows
- [ ] Gradient text
- [ ] Rounded-full buttons/pills (unless for avatars)
- [ ] Thick borders (>1px)
- [ ] Multiple accent colors competing

### Animations
- [ ] Infinite spin/pulse/float
- [ ] Staggered entrance animations
- [ ] Hover scale/lift effects
- [ ] Parallax scrolling
- [ ] Loading skeletons that shimmer
- [ ] Progress bars with gradients

### Copy Patterns
- [ ] Emojis in headings
- [ ] Exclamation marks
- [ ] Marketing superlatives
- [ ] Metaphors ("playbook", "journey", "ecosystem")
- [ ] Aspirational language
- [ ] Design self-reference ("beautifully designed")

### Component Patterns
- [ ] Card grids for everything
- [ ] Stat strips with icons
- [ ] Logo clouds
- [ ] "Pill soup" filter bars
- [ ] Floating action buttons
- [ ] Hero sections on internal pages

---

## Litmus Tests

Before shipping a design change, ask:

1. **The Bloomberg Test**: Would this look appropriate on a Bloomberg Terminal?
2. **The Paper Test**: Would this feel at home in an academic journal?
3. **The Boss Test**: Would you be comfortable with this open when your manager walks by?
4. **The Memory Test**: Will users remember the data or the design? (Data is correct answer)
5. **The Subtraction Test**: If I remove this element, does functionality suffer? (If no, remove it)

---

## Migration Checklist

For existing pages:

- [ ] Remove gradient backgrounds
- [ ] Remove decorative blur/orbs
- [ ] Remove grid pattern overlays
- [ ] Replace `max-w-*` with flex layouts
- [ ] Remove card shadows
- [ ] Remove hover lift effects
- [ ] Remove staggered animations
- [ ] Replace gradient text with solid colors
- [ ] Reduce accent colors to one per view
- [ ] Remove emojis from copy
- [ ] Rewrite marketing copy to utility copy
- [ ] Remove infinite animations (pulse, spin, float)
- [ ] Simplify typography (no display fonts)
- [ ] Ensure dark mode is desaturated

---

## Inspiration

Look to these for reference:
- **Bloomberg Terminal** — Information density, functional design
- **Linear** — Restraint, consistent spacing, subtle interactions
- **The New York Times** — Typography hierarchy, reading experience
- **Academic journals (Nature, Science)** — Credibility, information-first
- **Enterprise software (Figma, Vercel, Raycast)** — Professional tools for professionals

---

## Version

**v1.0** — Initial guidelines  
*Last updated: 2026-04-02*
