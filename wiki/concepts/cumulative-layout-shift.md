---
tags: [ui, ux, layout, performance, design-system]
category: concept
---

# Cumulative Layout Shift (CLS) Prevention

Cumulative Layout Shift (CLS) measures visual stability by tracking unexpected layout shifts during a page's lifecycle. In financial and analytical dashboards like Benchify, layout stability is critical: traders and analysts rapidly scan timeframes, macro indicators, and model decisions. A sudden layout jump—caused by a skeleton collapsing, a slow query unmounting a table, or a network reconnect refetching data—disorients user attention and risks accidental clicks.

Benchify enforces a strict zero-layout-shift standard across all data loading and transition lifecycles.

## Tiered Loading Hierarchy: SSR First, Voxel Skeletons Over Spinners

Benchify separates hydrated transitions from cold client fetches so neither causes layout whiplash or unanchored blank screens:

1. **Hydrated & Transitional Views (Zero Loader)**: Prefer SSR pre-hydration with silent Suspense (`fallback={null}`) and `keepPreviousData` on timeframe or tab switches. When data already exists, never replace it with a placeholder.
2. **Cold / Uncached Feeds (Layout-Matched Voxel `Skeleton`)**: When a feed or panel has no cached data yet and must display a loading state, **skeleton placeholders are preferable to a single spinner** because they preserve the expected layout of the feed. Users can start scanning the structure immediately, and real content swaps in with less visual jump.
3. **Zero Spinners (`LoadingSpinner` / `animate-spin` Banned)**: Standalone spinning icons provide zero structural preview and induce layout jumps when replaced by multi-card grids or tables. The `LoadingSpinner` primitive has been removed from `@llm-market-bench/ui-design-system` entirely. All loading indicators standardize on the `Skeleton` primitive and `LoadingBoundary` (with `Button[isLoading]` using a pulsing Voxel pixel square + `aria-busy="true"`).

### The `Skeleton` Primitive

`Skeleton` (`packages/ui-design-system/src/primitives/Skeleton.tsx`) is the canonical cold-load placeholder:

| Prop | Values | Meaning |
| :--- | :--- | :--- |
| `variant` | `'text' \| 'block' \| 'card'` | Single text line(s), a rectangular block, or a multi-line card slot |
| `lines` | number (default `3`) | Placeholder line count for `text` / `card` variants |

Every variant renders `aria-hidden="true"` with `data-slot="skeleton"` (and `data-slot="skeleton-line"` per line), `rounded-none`, `bg-voxel-trough` / `bg-voxel-elevated`, and `animate-pulse motion-reduce:animate-none`. Line widths cycle through `w-2/3`, `w-full`, `w-4/5`, `w-5/6` so a card placeholder reads as prose rather than a solid bar. The legacy `.skeleton` shimmer CSS class in `apps/web/src/styles/app.css` has been deleted — there is exactly one skeleton implementation.

### Skeleton Discipline (Avoiding Height-Mismatch Whiplash)

To prevent the classic skeleton failure mode (arbitrary heights snapping when data resolves):

- Build placeholders with `Skeleton` (`rounded-none`, `bg-voxel-trough` / `bg-voxel-elevated`, `motion-reduce:animate-none`, `aria-hidden="true"`).
- Mirror the exact fluid CSS Grid tracks (`repeat(auto-fit, minmax(min(100%, 18rem), 1fr))`) and approximate card/line counts of the target feed.
- Wrap the placeholder region in `aria-busy="true"` (and `role="status"` with an `aria-label` when the region is a named loading state) so assistive technology announces the pending load without a spinner.

## Core Architectural Invariants

Benchify mandates the following design and querying rules to eliminate layout shifts:

### 1. Silent Suspense Fallbacks for Hydrated Boundaries

When components are wrapped in React `<Suspense>` alongside SSR pre-hydration (e.g., [`apps/web/src/features/today/pages/TodayPage.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/today/pages/TodayPage.tsx)), use silent fallbacks so server-hydrated markup renders without double-render flicker:

```tsx
{/* Silent Suspense for SSR-hydrated sections */}
<Suspense fallback={null}>
    <AgentInsights memories={data.memories} />
</Suspense>
```

For unhydrated client-only feeds, wrap with `LoadingBoundary`, which renders a 3-card Voxel `Skeleton` grid by default or a caller-provided layout-matched `fallback`:

```tsx
<LoadingBoundary isLoading={isLoading} loadingText="Loading feed">
    <Feed items={items} />
</LoadingBoundary>

// or with a layout-matched placeholder
<LoadingBoundary isLoading={isLoading} fallback={<Skeleton variant="card" lines={4} />}>
    <Feed items={items} />
</LoadingBoundary>
```

`LoadingBoundary` renders `role="status"`, `aria-busy="true"`, and `aria-label={loadingText ?? 'Loading content'}` on its wrapper, and never emits an SVG spinner.

### 2. Stale-While-Revalidate with `keepPreviousData`

When toggling timeframes (e.g., 7D, 30D, All-Time in [`apps/web/src/features/leaderboard/pages/LeaderboardPage.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/leaderboard/pages/LeaderboardPage.tsx)), the user expects uninterrupted visibility of the current table.

Using TanStack Query's `placeholderData: keepPreviousData` ensures the current dataset remains rendered while the new timeframe fetches in the background:

```tsx
const { data, isLoading } = useQuery({
    queryKey: ['leaderboard', timeframe],
    queryFn: () => fetchLeaderboard(timeframe),
    placeholderData: keepPreviousData,
});

// Table never unmounts during timeframe transitions;
// layout-matched Voxel Skeleton grid only shows on cold starts when zero models exist
{isLoading && models.length === 0 ? (
    <div className="flex flex-col gap-6" aria-busy="true">
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch">
            <Skeleton variant="card" lines={4} />
            <Skeleton variant="card" lines={4} />
            <Skeleton variant="card" lines={4} />
        </div>
        <Skeleton variant="block" className="h-48" />
    </div>
) : (
    <LeaderboardTable models={models} />
)}
```

### 3. Resilient In-Memory Fallbacks on Network Disconnect

Network interruptions, offline states, or server database timeouts must never wipe out hydrated client views:

- Server fetch functions (e.g. [`apps/web/src/features/today/api/fetch-today-data.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/today/api/fetch-today-data.ts), [`apps/web/src/features/concepts/api/fetch-concepts.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/concepts/api/fetch-concepts.ts), [`apps/web/src/features/home/api/fetch-barometer.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/home/api/fetch-barometer.ts)) retain their last valid in-memory payload (`cachedTodayData`, `cachedConcepts`, `cachedMarketFeeling`).
- If an upstream query fails, the function returns the cached state rather than returning an empty array (`[]`) or `null`.
- On cold starts with no cache available, functions throw an error so TanStack Query retries via exponential backoff rather than treating network failure as an empty database.

### 4. Exponential Backoff & Jitter

Configured in [`apps/web/src/lib/query-client.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/lib/query-client.tsx):

- Retries use exponential backoff with full randomized jitter ($1000 \times 2^{\text{attempt}} + \text{rand}(0, 500)\text{ms}$, capped at 10s).
- Non-retriable client errors (`400`, `401`, `403`, `404`) are skipped immediately to prevent retry thrashing.
- On reconnection, TanStack Query's `onlineManager` automatically triggers background revalidation without clearing the display.

### 5. Intrinsic Grid & Container Sizing

Fluid layout rules prevent cards from shifting horizontally or wrapping unexpectedly when adjacent cards hydrate:

- Combine CSS Grid with `repeat(auto-fit, minmax(min(100%, 15rem), 1fr))` so column boundaries are established intrinsically by parent container width rather than by asynchronous children.
- Use `min-w-0` on flex items and `min-h-[...]` baselines on multi-card sections to stabilize the vertical rhythm.

### 6. Tab Anchor Stability & Sibling Invariance

When users navigate between model, track, or asset tabs (e.g. switching between baseline and champion models on `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx`), primary decision and hero cards must maintain invariant vertical positioning across tabs:

- **Primary Anchor Stability**: Anchor components such as `HeroPredictionCard` (`apps/web/src/features/daily-predictions/components/HeroPredictionCard.tsx`) and `PredictionsTable` (`apps/web/src/features/daily-predictions/components/PredictionsTable.tsx`) must never be shoved downward or displaced when switching to a tab that possesses extra metadata.
- **Auxiliary Card Placement**: Tab-specific supplementary sections (such as the retired champion `CuratedManifestCard`, removed with the four-regime track) must be placed underneath the primary table and hero blocks rather than inserted above them.
- **Zero Whiplash on Tab Transitions**: Placing auxiliary panels at the bottom ensures the user's primary visual focal points (metrics overview, latest prediction outlook, predictions table) remain rock-solid and visually stable across tab clicks, avoiding disorienting vertical layout shifts.

### 7. Secondary UI Query Settlement Gating

Secondary action buttons (such as `Reset to Top 5` or `Reset Crosshair`) and volatile derived badges (such as per-portfolio daily percentage moves) must never flash or render during in-flight fetches, `keepPreviousData` background refetches, or React transition states. A button that appears for one frame and then disappears — or a percentage that briefly shows a stale value — reads as instability in a financial dashboard.

Gate these elements with `isQuerySettled(queries, isTransitionPending)` from [`apps/web/src/lib/query-client.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/lib/query-client.tsx):

```tsx
const isQueriesSettled = isQuerySettled([listQuery, comparisonQuery]);
const isChartSettled = isQueriesSettled && !isPending;

<PortfolioComparisonChart ... isSettled={isChartSettled} />
<PortfolioCard todayPct={isQueriesSettled ? todayPctMap.get(portfolio.id) : undefined} />
```

The helper returns `true` only when every supplied query has valid data and is not `isFetching`, `isPending`, or `isPlaceholderData`, and no React transition is pending. Crucially, **primary chart and container chrome stay stably mounted** while secondary affordances are gated — the gating removes transient elements rather than swapping layout, so it never itself introduces a shift. See [[concepts/tanstack-query]] for the full helper semantics.

### 8. No Optimistic Updates

Mutations must wait for confirmed server responses with in-flow pending feedback (`Button[isLoading]`, which renders a pulsing Voxel pixel square plus `aria-busy="true"`) and explicit `ErrorCard` feedback on failure. Speculative `onMutate` cache rewrites and optimistic rollback machinery are prohibited: a value that renders, reverts, and re-renders is a layout shift by another name, and showing unconfirmed state on financial views is worse than a brief pending indicator.

### 9. Zero SSR/CSR Render Divergence or Post-Mount Visual Flash (Mandatory)

Routes must **never** render one visual state during SSR and then switch to another on client hydration inside `useEffect` (whether layout geometry, time-of-day palettes, `localStorage` preferences, or asynchronously sized canvases). Post-hydration state jumps count as avoidable SSR/CSR visual instability (CLS when DOM dimensions, controls, or copy shift; visible sky/theme flash even on fixed stages):

- **Resolve initial visual state in the route loader**: Compute time-sensitive or deterministic state on the server inside the route `loader` and seed client state via lazy `useState` initialization rather than mutating inside a mount `useEffect` (e.g., `initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et')` in `apps/web/src/routes/index.tsx` and `apps/web/src/routes/personality.tsx`, consumed by `useDioramaStage(initialAtmosphere)` in `apps/web/src/features/home/backdrop/useDioramaStage.ts`).
- **Match SSR CSS pixel-for-pixel to canvas/JS layers**: Background gradients rendered by SSR CSS classes (`.scene-atmosphere-*` in `apps/web/src/styles/app.css`) must match the exact linear stops, horizon glow, and vignette stops painted by `bakeSky` in `apps/web/src/features/home/backdrop/garden-renderer.ts` so canvas reveal never flashes a different sky color.
- **Contain canvases inside SSR-sized boxes**: Mount interactive canvas layers as `position: absolute; inset: 0` inside SSR-constrained `SceneStage` containers (using Tailwind `min-h-80` / `min-h-svh` and standard `<body className="min-h-svh flex flex-col">` flow, never `dvh` or custom CSS `calc(...)` height rules) and transition `opacity` (`opacity-0` -> `opacity-100`, disabled under `prefers-reduced-motion`) after the first frame paints so canvas readiness never alters document flow.

## Related

- [[concepts/core-web-vitals]] — p75 LCP, INP, and CLS targets and 3-tier JS loading model
- [[concepts/rendering-strategies]] — Full SSR, Hybrid SSR, and SSR/CSR symmetry rules
- [[concepts/living-scene-backdrops]] — Cedar Sanctuary `SceneStage` and zero-flash loader hydration
- [[entities/design-system]] — UI primitive library, theme conventions, and layout governance
- [[concepts/fluent-responsive-design]] — Breakpoint-free intrinsic responsive layouts
- [[concepts/zero-frontend-compute]] — Keeping the presentation layer clean of heavy client math
- [[concepts/tanstack-query]] — Query settlement gating and SSR-safe QueryClient setup
