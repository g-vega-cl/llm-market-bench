# Design System Consolidation

**Goal**: Make the existing design system consistently used across all 9 pages before any visual refresh.

**Date**: 2026-05-14

---

## Current State: 9 Pages

| Page | PageLayout | SectionHeading | DS Imports | Issues |
|------|-----------|---------------|-----------|--------|
| TodayPage | ❌ | ❌ (no page heading) | ✅ (sub-comps) | Manual bg/padding, no page title |
| MarketOverview | ❌ | ❌ (raw `<h2>`) | ✅ | Raw h2s in SectorPerformance, CorrelationHeatmap, UncorrelatedPairs |
| PortfoliosPage | ❌ | ✅ | ✅ | Raw `<h2>` for "Retired Agents" subsection |
| PortfolioDetail | ❌ | ✅ | ✅ | Raw `<h1>` for portfolio name, manual padding |
| MemoriesPage | ❌ | ✅ | ✅ | Custom border-b header + inner max-w-5xl wrapper |
| AuditsPage | ❌ | ✅ | ✅ | Raw `<h2>` for sub-sections |
| ReasoningPage | ❌ | ❌ | ❌ ZERO | Raw spinner, raw button, raw badge, blue/teal colors (not semantic), no DS at all |
| CauseAndEffect | ❌ | ✅ | ✅ | Light page, mostly fine |
| ConceptsPage | ❌ | ❌ | ❌ ZERO | `text-gray-*` not zinc, `border-gray-*`, raw h1 |

## Fixes (6 items)

### 1. Fix Satoshi font (it's not loading)

**Problem**: `--font-body: "Satoshi"` is declared but no font file or import exists. Everything falls back to system-ui.

**Fix**: Satoshi is on Fontshare. Add to `apps/web/src/styles/app.css`:
```css
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&display=swap');
```

**File**: `apps/web/src/styles/app.css` (line 11, after existing @import)

### 2. Adopt PageLayout everywhere

**Problem**: PageLayout is exported but 0/9 pages use it. Every page hand-rolls its own padding/max-width.

**Approach**: Update PageLayout to be more flexible, then migrate each page.

**PageLayout changes** (`packages/ui-design-system/src/layouts/PageLayout.tsx`):
- Make `min-h-screen` optional (or allow override via className)
- Current pattern: `min-h-screen` + inner `mx-auto max-w-* px-* py-*`
- Add ability to skip min-h-screen for hero pages

**Page migrations** (each page gets `import { PageLayout }` and wraps content):

| Page | Pattern |
|------|---------|
| PortfoliosPage | Replace manual div → `<PageLayout>` |
| PortfolioDetailPage | Replace manual div → `<PageLayout>` |
| MemoriesPage | Replace manual div + inner wrapper → `<PageLayout maxWidth="md">` |
| AuditsPage | Replace manual div → `<PageLayout>` |
| ReasoningPage | Replace manual div → `<PageLayout>` |
| CauseAndEffectPage | Replace manual div → `<PageLayout>` |
| ConceptsPage | Replace manual div → `<PageLayout>` |
| TodayPage | Add `<PageLayout withPadding={false}>` below hero |
| MarketOverviewPage | Add `<PageLayout withPadding={false}>` below hero |

### 3. Replace all raw headings with SectionHeading

**Locations**:

| File | Line | Current | Fix |
|------|------|---------|-----|
| MarketOverviewPage.tsx | 292 | `<h2> Sector Performance` | `<SectionHeading gradient="electric">` |
| CorrelationHeatmap.tsx | 71 | `<h2> Correlation Heatmap` | `<SectionHeading gradient="ai">` |
| UncorrelatedPairs.tsx | 57 | `<h2> Top Uncorrelated Pairs` | `<SectionHeading gradient="success">` |
| PortfolioDetailPage.tsx | 77 | `<h1> {owner_name}` | `<SectionHeading gradient="electric">` |
| ConceptsPage.tsx | 23 | `<h1> Concept Cluster Map` | `<SectionHeading gradient="ai">` |
| ReasoningPage.tsx | 62 | Inline gradient `<h1>` | `<SectionHeading gradient="electric">` |
| TodayPage (TodayPage.tsx) | n/a | No heading | Add `<SectionHeading>` for page title if appropriate |

### 4. Fix ReasoningPage — zero DS usage

**Problem**: ReasoningPage uses no DS components at all. Has raw spinners, raw buttons, raw badges, inline gradient text, non-semantic colors.

**Fixes**:
- Loading state: Replace raw spinner div → `<LoadingBoundary>` or `<LoadingSpinner>`
- Error state: Replace raw div → `<ErrorCard>`
- Tab buttons and "Load More" button: Replace → `<Button>` components
- Category badges: Replace → `<Badge>` components  
- Page heading: Replace inline gradient h1 → `<SectionHeading>`
- Color classes: Replace `text-blue-*`/`text-teal-*` → semantic tokens (`text-accent`, etc.)

### 5. Fix ConceptsPage — gray → zinc, add DS imports

**Problem**: Uses `text-gray-500`, `border-gray-100`, `text-blue-600`, `text-red-600`, `bg-gray-400`.

**Fixes**:
- `text-gray-500` → `text-zinc-500`
- `border-gray-100` → `border-zinc-200 dark:border-zinc-800`
- `text-blue-600` → `text-accent`
- `text-red-600` → `text-danger`
- `bg-gray-400` → `bg-zinc-400`
- Add `<SectionHeading>` for the page title
- Add `PageLayout` wrapper

### 6. PortfoliosPage — raw "Retired Agents" h2

**Fix**: Replace line 176 `<h2 className="text-lg font-semibold...">Retired Agents</h2>` with a consistent subsection class or small SectionHeading variant.

---

## Files Changed

| File | Changes |
|------|---------|
| `apps/web/src/styles/app.css` | Add Satoshi @import |
| `packages/ui-design-system/src/layouts/PageLayout.tsx` | Make min-h-screen optional |
| `apps/web/src/features/today/pages/TodayPage.tsx` | Add PageLayout |
| `apps/web/src/features/market-overview/pages/MarketOverviewPage.tsx` | PageLayout + SectionHeading for SectorPerformance |
| `apps/web/src/features/market-overview/components/CorrelationHeatmap.tsx` | SectionHeading |
| `apps/web/src/features/market-overview/components/UncorrelatedPairs.tsx` | SectionHeading |
| `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` | PageLayout + subsection heading |
| `apps/web/src/features/portfolios/pages/PortfolioDetailPage.tsx` | PageLayout + SectionHeading for h1 |
| `apps/web/src/features/memories/pages/MemoriesPage.tsx` | PageLayout |
| `apps/web/src/features/audits/pages/AuditsPage.tsx` | PageLayout |
| `apps/web/src/features/reasoning/pages/ReasoningPage.tsx` | PageLayout + all DS components (Button, Badge, ErrorCard, LoadingBoundary, SectionHeading) |
| `apps/web/src/features/cause-and-effect/pages/CauseAndEffectPage.tsx` | PageLayout |
| `apps/web/src/features/concepts/pages/ConceptsPage.tsx` | PageLayout + SectionHeading + gray→zinc migration |

## Validation

After changes:
1. `grep -rn "text-gray-" apps/web/src/features/` → should return zero (all zinc)
2. `grep -rn "PageLayout" apps/web/src/features/` → should show every page
3. `grep -rn "<h[12] " apps/web/src/features/` → should only show subsection h2s (no page titles)
4. `pnpm biome check` → passes
5. `cd apps/web && pnpm run build` → passes
6. `cd apps/web && pnpm run typecheck` → passes
