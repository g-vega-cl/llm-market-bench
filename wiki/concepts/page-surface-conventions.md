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

### Shells that write their own box

`BotSceneShell` (`apps/web/src/features/recipes/components/BotSceneShell.tsx`) does not use `PageLayout` at all. It wraps the tab panel in a hand-written `relative z-10 mx-auto flex w-full max-w-[calc(80rem+3rem)] flex-col gap-6 px-6 pb-8 md:pb-12` box, for two reasons specific to a shell that sits under a `SceneStage`:

- `SceneStage` centres a `max-w-7xl` box inside its own `px-6`, so the panel has to be one `max-w-7xl` **plus** that padding wide for its card edge to land on the back link's edge instead of 24 px to the right.
- `PageLayout`'s `maxWidth` presets would emit a competing `max-w-*` utility, and `cn` is bare clsx (no tailwind-merge), so stylesheet order rather than intent would pick the winner.

The spirit of the opt-out rule is preserved: the shell declares its complete horizontal and vertical padding, and no page rendered inside it adds padding of its own.

## Page titles: action surfaces vs browse surfaces

A page's job decides whether it carries a visible title block.

- **Action surfaces** (`/personality`, `/build`, `/chat`) carry **no page-level title block** — no eyebrow, no title, no description above the first control. The page name survives as exactly one `sr-only` `<h1>` matching the route `<title>`, in **every render branch** the route can reach (a panel that swaps components, or a route that mounts one straight from loader data, needs its own). Section headings below the fold may keep their one-line subtitles.
- **Browse surfaces** keep a visible title — an `h1` or a `SectionHeading` — plus at most one description line.

## Hub and detail pages

A bot surface with a header card carries **one purpose**, and the **chip row is the navigation**: Overview · Performance · Behaviour · Live Runs · Blueprint (last one owner-only). Each chip is a real page with its own URL.

- **Hubs claim the page, detail tabs claim the section.** `BotStageSubNav` (`apps/web/src/features/recipes/components/BotStageSubNav.tsx`) takes `currentMode: 'page' | 'item' | 'none'`, which replaced the old `markCurrent` boolean. On the Overview hub the active chip's href *is* the current URL, so it claims `aria-current="page"`. On a detail tab the chip still reads as the current section but its href points at the hub, so `currentMode="item"` emits `aria-current="true"` — the section is announced without claiming a URL the page does not own. `currentMode="none"` leaves the active chip unmarked.
- **Detail pages carry their own `sr-only` `<h1>`.** `BotSceneShell` requires a `sectionTitle` and renders `<h1 className="sr-only">{recipeName} — {sectionTitle}</h1>` as the first child of its scene card (for example `AI Capex Radar — Performance & positions`, `Momentum Alpha — Run traces & portfolio`). The hub owns the visible heading; a detail page still needs a document heading, and the repo convention is exactly one `sr-only` `<h1>`.
- **The back link names its destination.** `← {recipeName}` carries `aria-label="Back to {recipeName} {Overview|Live Runs}"`, so the link announces where it goes instead of only the bot name.
- **Detail pages own their own feedback.** The Performance and Behaviour panels own the Enable Live and Run Backtest buttons, so the notices the hub card renders have to exist on the detail page too. `BotSceneShell`'s `alerts` slot renders them under the sub-nav, inside the scene: `LiveSwitchConfirmation` when the owner is already at the live cap (without it the toggle parks in `confirming` and the button is a silent no-op), `StudioAlertSlot` for backtest/schedule quota and execution errors, and a `role="alert"` block for a fork error. `WaitlistPledgeModal` stays outside the shell.
- **Panel ownership is exclusive.** Performance owns equity/benchmark, the open book and closed trades; Behaviour owns tool usage, action mix and exits; Live Runs owns run traces. A block rendered on two tabs is a bug, not redundancy.
- **The Live Runs hub is retired.** `/recipes/live/$recipeId` redirects to `/recipes/live/$recipeId/runs`; it used to duplicate the Overview card plus a link to the traces it summarised.
- **Editors stay one page.** Blueprint opens on the editor: chips, one compact status + name/save line, then blocks. Splitting an editor costs a click per edit.
- **Empty tabs explain themselves.** A bot with no run history still shows Behaviour, saying which run fills it — a chip that opens onto a blank page is worse than one that says why.
- **Strip content** stays per tab: Overview → equity, net return, win rate, open positions. `BotSummaryStrip` (`apps/web/src/features/recipes/components/BotSummaryStrip.tsx`) lays those tiles out on an intrinsic `grid-cols-[repeat(auto-fit,minmax(min(100%,11rem),1fr))]` grid rather than `grid-cols-2 lg:grid-cols-4`, so the four-up row appears at whatever container width fits four tracks instead of at a viewport breakpoint ([[concepts/fluent-responsive-design]]).

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
- [[entities/recipe-studio]] — the bot hub, detail tabs, and `/build` that these rules govern
- [[concepts/fluent-responsive-design]] — the intrinsic grid `BotSummaryStrip` uses instead of a `lg:` breakpoint
