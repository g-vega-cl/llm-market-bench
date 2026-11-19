---
tags: [web, performance, core-web-vitals, lcp, inp, cls]
category: concept
---

# Core Web Vitals & Feed Loading Strategy

Core Web Vitals are Google's standardized user-centric field metrics for loading performance, interaction responsiveness, and visual stability, defined at [https://web.dev/articles/vitals](https://web.dev/articles/vitals). Benchify targets the **Good** threshold for every metric at the **75th percentile (p75)** of real-world page loads across both mobile and desktop devices.

---

## Core Metrics & Thresholds (`web.dev/articles/vitals`)

| Metric | Full Name | Measures | Good (p75) | Needs Improvement | Poor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LCP** | Largest Contentful Paint | Loading speed of the largest above-the-fold image or text block | $\le 2.5\text{ s}$ | $2.5\text{ s} - 4.0\text{ s}$ | $> 4.0\text{ s}$ |
| **INP** | Interaction to Next Paint | Responsiveness across all click, tap, and keyboard interactions in a session | $\le 200\text{ ms}$ | $200\text{ ms} - 500\text{ ms}$ | $> 500\text{ ms}$ |
| **CLS** | Cumulative Layout Shift | Visual stability / unexpected layout shifts during page lifetime | $\le 0.1$ | $0.1 - 0.25$ | $> 0.25$ |

Evaluating at the **75th percentile (p75)** ensures that at least 75% of visits across varied devices and networks meet the Good bar without letting extreme outlier connections skew the aggregate or letting a fast median (50th percentile) mask sluggish mid-range mobile sessions.

- **INP matters most after initial load**: Long-lived financial dashboard sessions involve repeated timeframe switches, filters, table row inspections, and recipe edits. Main-thread jank compounds over a session in ways LCP alone never catches.

---

## JavaScript Loading Strategy (3-Tier Visual Priority)

Large web applications fail Core Web Vitals not just from total JavaScript size, but from allowing non-critical code to block the first useful render. Benchify organizes client JavaScript into three visual-priority tiers:

| Tier | What Belongs Here | Loading Mechanism in Benchify |
| :--- | :--- | :--- |
| **Tier 1 (First Visual Response)** | App shell, navigation bar, layout-matched `Skeleton` placeholders, critical CSS tokens | SSR document + critical CSS + minimal entry bundle (`apps/web/src/routes/__root.tsx`) |
| **Tier 2 (Above-the-Fold Complete & Interactive)** | Above-the-fold feed/table rendering, common text/card renderers, primary actions | Hybrid SSR initial slice (e.g., `.limit(5)`) + route chunks + TanStack Query hydration |
| **Tier 3 (Deferred / Off-Screen / Intent-Driven)** | Heavy charts (`d3`), secondary telemetry panels, rich composer extras, uncommon renderers, analytics SDKs, logging | `React.lazy()` + `<Suspense>`, Vite `manualChunks` (`vendor-d3` in `apps/web/vite.config.ts`), declarative `<PostHogProvider>`, and idle route warmup (`apps/web/src/utils/route-warmup.ts`) |

### Chunking & Prefetch Discipline

- **Route-level splitting**: Load secondary routes only on navigation or idle warmup (`useIdleRouteWarmup()` uses `requestIdleCallback` and `router.loadRouteChunk()`, skipping when `navigator.connection.saveData` is enabled).
- **Data-driven renderer splitting**: Load specialized view renderers (such as `d3` graph visualizations or markdown/trace viewers) only for the payload shapes present on the active surface rather than bundling every renderer into the root entry.
- **Interaction-triggered & idle prefetch**: Lazy-loaded interaction code (e.g., heavy editors or drawers) improves LCP by shrinking Tier 1–2 bytes, but can hurt INP if the first click waits for a large chunk download/parse. Prefetch high-probability secondary chunks during idle time after first paint so interaction paths stay under `200 ms`.
- **Never defeat bundler splitting**: Never call heavy third-party SDK `.init()` synchronously at module top level (see [[concepts/performance-auditing-strategy]] §4).

---

## Feed & Long-Session Performance Techniques

The following techniques map directly to LCP, INP, and CLS across data-heavy feeds and dashboards:

1. **Skeletons & Reserved Dimensions (CLS & Perceived LCP)**:
   - Use `Skeleton` (`packages/ui-design-system/src/primitives/Skeleton.tsx`) and `LoadingBoundary` matching the target CSS Grid tracks rather than spinners ([[concepts/cumulative-layout-shift]]).
   - Reserve explicit dimensions (`aspect-ratio` / `width` & `height` on media, intrinsic container sizing on charts, `isQuerySettled` gating in `apps/web/src/lib/query-client.tsx`) so late-arriving data never shifts content below.
2. **Short-Lived Caching, Revalidation, Deduplication & Cancellation (LCP & Network)**:
   - TanStack Query (`apps/web/src/lib/query-client.tsx`) deduplicates concurrent requests by query key, cancels stale in-flight fetches on rapid filter/route changes so superseded responses never overwrite newer state, and serves `placeholderData: keepPreviousData` during background revalidation.
   - Server loaders keep a last-valid in-memory payload fallback so transient disconnects never blank hydrated views.
3. **Virtualization & `content-visibility: auto` (INP on Long Sessions)**:
   - Unbounded feeds or multi-thousand-line trace views degrade INP as DOM node count grows. Bound mounted rows via pagination/windowing or virtualization (with spacer sizing to preserve scroll position), and apply CSS `content-visibility: auto` paired with `contain-intrinsic-size` on large off-screen containers so the browser skips off-screen layout and paint.
4. **Main-Thread Protection (INP)**:
   - Pre-calculate heavy financial math, joins, and statistics on the backend ([[concepts/zero-frontend-compute]]).
   - Avoid synchronous `onScroll` handlers that force layout reads (`getBoundingClientRect()`); use passive observers or framework scheduling/Web Workers for any unavoidable heavy serializable parsing, yielding between update chunks so click/tap/keyboard input is never blocked.
5. **Scroll Restoration & Cached Entities (Navigation Speed)**:
   - Rely on TanStack Router scroll restoration + normalized/shared TanStack Query cache entries so feed-to-detail-to-feed transitions render cached entity summaries immediately while revalidating in the background.
6. **Media Optimization (LCP & Bandwidth)** (when images/media appear):
   - Deliver via CDN in modern formats (`AVIF` / `WebP`) with responsive `srcset` / `sizes` and explicit aspect ratios.
   - Load the likely above-the-fold LCP asset eagerly (high priority) and apply `loading="lazy"` to off-screen media so below-the-fold images never compete with LCP.

---

## Benchify Guardrails & Deliberate Departures

Generic social-feed patterns must be evaluated against Benchify's stricter financial-UI and Voxel design invariants (`.agents/rules/design-spec.md`):

| Generic Feed Concept | Benchify Standard / Rule | Why |
| :--- | :--- | :--- |
| **Optimistic UI & offline outbox** | **Prohibited on financial/persisted mutations** (`.agents/rules/design-spec.md` §7.3, [[concepts/cumulative-layout-shift]] §8) | Speculative `onMutate` rewrites risk showing unconfirmed financial state and cause layout-shift whiplash on rollback. Use confirmed writes with `Button[isLoading]` and `ErrorCard`. |
| **Adaptive request sizing via JS viewport height** | **No JS viewport measurement for layout** (`.agents/rules/design-spec.md` §1–2); use fixed aggressive SSR bounds (`.limit(5)`) | `window.innerWidth`, `matchMedia`, and `ResizeObserver` are banned for layout/column math. CSS Grid `auto-fit` owns layout; SSR uses lean fixed slices (`limit: 5` -> `50`/`200`). |
| **Intersection Observer infinite scroll** | **Prefer Hybrid SSR + background hydration for bounded feeds** ([[concepts/performance-auditing-strategy]] §5) | Avoids custom scroll-trigger plumbing for moderate lists; reserve `IntersectionObserver` (never synchronous `onScroll`) strictly for genuinely unbounded feeds or lazy offscreen media. |
| **Lazy hover cards & floating menus** | **Banned** (`.agents/rules/design-spec.md` §10, [[concepts/in-flow-inspection]]) | Floating tooltips, popovers, and hover cards obscure financial telemetry and fail touch/keyboard accessibility. Defer heavy detail data instead into in-flow recessed `.voxel-trough` slots on click/focus. |
| **Service Worker cached reads** | **HTTP immutable assets + TanStack Query + server in-memory fallback** ([[concepts/chunk-reload-recovery]]) | Hashed `/assets/*` use `Cache-Control: public, max-age=31536000, immutable`; avoiding a custom Service Worker prevents stale financial payloads and Netlify atomic-deploy chunk skew. |

---

## Measurement & Enforcement

- **Automated CI Gate**: `.github/workflows/lighthouse.yml` runs Lighthouse CI (`lighthouserc.json`) against Netlify Deploy Previews on public routes, asserting `minScore: 0.9` across Performance, Accessibility, Best Practices, and SEO.
- **Manual Whole-Site Audits**: Run Unlighthouse against `https://www.benchify.dev` ([[concepts/performance-auditing-strategy]]) to inspect route-by-route LCP, INP/TBT, and CLS regressions.
- **Unit & Static Guardrails**: Hydration symmetry (`hydration.test.tsx`), AAA contrast & token audit (`contrast-audit.test.tsx`), and zero-load SSR loader tests (`fetch-today-data.test.ts`).

---

## Related

- [[concepts/performance-auditing-strategy]] — Lighthouse CI pipeline, SSR fetch limiting, and developer debugging guide
- [[concepts/cumulative-layout-shift]] — Voxel `Skeleton`, `keepPreviousData`, `isQuerySettled`, and no-optimistic-UI rules
- [[concepts/rendering-strategies]] — Full SSR, Hybrid SSR, and CSR tradeoffs
- [[concepts/zero-frontend-compute]] — Keeping heavy math off the client main thread
- [[concepts/tanstack-query]] — Caching, deduplication, backoff, and query settlement gating
- [[concepts/chunk-reload-recovery]] — Idle route warmup and immutable chunk caching
- [[concepts/in-flow-inspection]] — Replacing floating hover cards with in-flow `.voxel-trough` telemetry
- [[entities/design-system]] — CSS-first layout, `Skeleton`, and Voxel UI primitives
- [[entities/web-app]] — TanStack Start routes, Vite chunking, and client architecture
- [[entities/agent-rules]] — Root `GEMINI.md` and `.agents/rules/design-spec.md` governance
