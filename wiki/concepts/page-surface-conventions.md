---
tags: [web, design-system, layout, page-layout, design-spec, conventions]
category: concept
---

# Page Surface Conventions

Two structural rules from `.agents/rules/design-spec.md` govern how a page owns its outer surface: how it opts into or out of `PageLayout` padding (§3.4), and whether it carries a visible page title (§4a). Both decay silently when left as prose, so both are enforced by `apps/web/src/test/page-surface-conventions.test.tsx`.

## PageLayout rhythm is opted out, never overridden

`PageLayout` (from `@llm-market-bench/ui-design-system`) emits base padding when `withPadding` is true (the default): `px-6 md:px-12 py-8 md:py-12`.

A page with its own vertical rhythm must **opt out** by passing `withPadding={false}` and writing its complete horizontal and vertical padding itself — as `/renko` and `PortfolioDetailPage` already did. It must **never** override the base padding through `className` while `withPadding` is true: `cn` is bare clsx, so both declarations survive and stylesheet order decides the winner (`.py-8` follows `.py-6`, so the base wins and the page's intent is silently lost).

When opting out, the page must re-declare its own horizontal padding (`px-6 md:px-12` or `p-0`), because opting out removes the base `px-6 md:px-12` too.

```tsx
// Correct — owns its rhythm, base padding never emitted
<PageLayout className="px-6 md:px-12 py-6 space-y-6" maxWidth="xl" withPadding={false}>

// Wrong — base py-8/md:py-12 survives and wins
<PageLayout className="py-6 space-y-6" maxWidth="xl">
```

### Pages that opt out

- `apps/web/src/features/autoresearch/pages/AutoresearchPage.tsx` — `px-6 md:px-12 py-12 space-y-12`
- `apps/web/src/features/autoresearch/pages/BacktestAutoresearchPage.tsx` — `px-6 md:px-12 py-12 space-y-12`
- `apps/web/src/features/market-overview/pages/MarketOverviewPage.tsx` — `px-6 md:px-12 pt-8 pb-24 space-y-16`
- `apps/web/src/features/memories/pages/EventChainPage.tsx` — header `px-6 md:px-12 py-6 flex flex-col gap-4`
- `apps/web/src/features/today/pages/TodayPage.tsx` — `px-6 md:px-12 py-6 space-y-6`

Pages that keep the default rhythm simply omit padding tokens from `className` (e.g. `CompaniesPage`, `CompanyDossierPage`, `GeneratedNewslettersPage`, `MemoriesPage`).

## Page titles: action surfaces vs browse surfaces

A page's job decides whether it carries a visible title block.

- **Action surfaces** (`/personality`, `/build`, `/chat`) carry **no page-level title block** — no eyebrow, no title, no description above the first control. The page name survives as exactly one `sr-only` `<h1>` matching the route `<title>`, in **every render branch** the route can reach (a panel that swaps components, or a route that mounts one straight from loader data, needs its own). Section headings below the fold may keep their one-line subtitles.
- **Browse surfaces** keep a visible title — an `h1` or a `SectionHeading` — plus at most one description line.

## Primary action front & center

Putting no visible title on an action surface only works if the user's primary task actually sits at the top. On mobile (`360px`), stacking a multi-card stepper, status banner, or template catalog above a text input pushes the input and primary CTA below the fold.

Section 4b of `.agents/rules/design-spec.md` therefore establishes **action-first ordering**:

1. **Top slot = active task & primary CTA**: Place only a compact status strip (`BuilderStatusStrip`) and any immediate blocker/prompt (`BuilderErrorBanner`, parked browser draft, or active clarifying question + options) above the primary input or action card.
2. **Supporting scaffolding below**: Place multi-step roadmaps (`BuilderStepper`), starter template chips (`BuilderStarterChips`), earlier conversation turns (`BuilderMessageHistory`), signed-out parking notices, and secondary links **below** the primary input/CTA.
3. **Every step & sub-state**: In `/build`, Step 1 (`BuilderChatPanel` describe + clarifying/parked sub-states), Step 2 (`BuilderAlignmentCard`), and Step 3 (`CompiledBotWorkspace`) all keep the next required user action above `BuilderStepper`. `/personality` follows the same rule by opening straight into Act 1 Q1 above the fold.

### Action-surface files

`ACTION_SURFACE_FILES` in the test is a deliberate literal list; adding an action surface means editing the test and the spec section in the same change:

- `apps/web/src/features/personality/PersonalityQuizPage.tsx`
- `apps/web/src/features/recipes/builder/BuilderChatPanel.tsx`
- `apps/web/src/features/recipes/builder/CompiledBotWorkspace.tsx`
- `apps/web/src/features/chat/ChatPage.tsx`

## Enforcement

`apps/web/src/test/page-surface-conventions.test.tsx` walks every non-test `.tsx` file under `apps/web` and asserts:

1. **Padding opt-out** — every `<PageLayout>` opening tag that sets a padding token (`p-*`/`px-*`/`py-*`/`pt-*`/`pr-*`/`pb-*`/`pl-*`, variant prefixes stripped) also passes `withPadding={false}`, and re-declares horizontal padding when it does.
2. **No base-padding collision** — rendering `<PageLayout withPadding={false} className="px-6 md:px-12 py-6">` emits `px-6`/`py-6` and never `py-8`/`md:py-12`.
3. **Action-surface titles** — each file in `ACTION_SURFACE_FILES` contains exactly one `<h1>` and its class tokens include `sr-only` (exact match, so `not-sr-only` cannot pass).

The source scan reads class strings from `className="..."`, `className={cn(...)}`, and template literals; unquoted identifiers (`styles.shell`) are invisible to it, so the spec forbids composing padding that way.

## Related

- [[entities/design-system]] — `PageLayout`, `SectionHeading`, and the typography tiers
- [[concepts/cumulative-layout-shift]] — zero-flash hydration and reserved-dimension guarantees
- [[entities/web-app]] — the routes these surfaces live on
