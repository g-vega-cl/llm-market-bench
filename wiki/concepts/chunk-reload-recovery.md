---
tags: [web, deployment, resilience, chunks, vite, error-handling]
category: concept
---

# Dynamic Chunk Failure & Idle Route Warmup

The web app is a code-split TanStack Start SPA/SSR hybrid: every route and heavy visualization library is emitted as a content-hashed chunk (`index-[hash].js`, `vendor-d3-[hash].js`). When a new deployment is published while a user still has a tab open, Netlify atomic deploys publish new chunk hashes. Stale browser tabs attempting to navigate to previously unvisited routes can encounter dynamic-import failures (`Failed to fetch dynamically imported module`).

This concept documents the proactive architecture that prevents dynamic import 404s, why legacy auto-reload hacks were deprecated, and how clean error telemetry is preserved.

---

## The Flaw of Auto-Reload & `preventDefault`

In previous iterations, the application attempted to intercept dynamic import failures via Vite's `vite:preloadError` event by calling `event.preventDefault()` and triggering an automated `window.location.reload()`:

```ts
// DEPRECATED ANTI-PATTERN - DO NOT RESTORE
window.addEventListener('vite:preloadError', (event) => {
    event.preventDefault(); // CAUSES UNCAUGHT CRASH
    triggerChunkReload();
});
```

### The `Cannot read properties of undefined (reading 'component')` Trap

1. Vite's runtime client wraps dynamic imports in `baseModule().catch(handlePreloadError)`.
2. When a chunk fetch fails (e.g. 404 or network drop), Vite dispatches `vite:preloadError`. If `event.defaultPrevented` is true, Vite skips rethrowing the error.
3. In JavaScript, a `.catch()` block that does not throw or return a value automatically resolves the promise with `undefined`.
4. TanStack Router's `lazyRouteComponent` awaited the dynamic import and attempted to access `comp = res['component']`.
5. Because `res` resolved to `undefined` instead of rejecting, the router threw a fatal `TypeError: Cannot read properties of undefined (reading 'component')`.

Furthermore, automated reloads resulted in broken user experiences (jarring page flashes, disruptive "Updating application..." banners, race conditions with background mutations, and circuit-breaker lockouts).

---

## Proactive Prevention: Idle-Time Chunk Warmup

Rather than executing background data loaders across every route or reacting only after a user clicks a link, the application warms route JS modules proactively using **Idle-Time Chunk Warmup** (`useIdleRouteWarmup` in `apps/web/src/routes/__root.tsx`, backed by `PRELOAD_WARMUP_ROUTES`, `DYNAMIC_WARMUP_SAMPLE_PATHS`, and `warmRouteChunks` in `apps/web/src/utils/route-warmup.ts`).

### Implementation

When the root route mounts in the browser, it schedules background module loading across `PRELOAD_WARMUP_ROUTES` (type-checked against `FileRoutesByTo` via `as const satisfies readonly (keyof FileRoutesByTo)[]`) using `requestIdleCallback` (with a `setTimeout` fallback). The allowlist covers `/`, `/portfolios`, `/lab`, `/recipes-demo`, `/recipes`, `/profile`, `/leaderboard`, `/companies`, `/how-it-works`, `/audits`, `/autoresearch`, `/autoresearch-backtest`, `/daily-predictions`, `/daily-predictions-backtest`, `/ai-predictions`, `/market-overview`, `/reasoning`, `/memories`, `/concepts`, `/cause-and-effect`, `/generated-newsletters`, `/earnings-audit`, `/barometer-audit`, `/renko`, `/retired-agents`, `/chat`, `/login`, and `/signup`. Redirect-only `/today` and `/logout` are deliberately excluded.

`DYNAMIC_WARMUP_SAMPLE_PATHS` maps dynamic `FileRoutesByTo` keys to concrete sample paths so parameterized routes are warmed too: `/portfolios/$portfolioId` → `/portfolios/_`, `/companies/$ticker` → `/companies/_`, `/recipes/backtest/$jobId` → `/recipes/backtest/_`, and `/memories/chain/$memoryId` → `/memories/chain/_`. Dynamic child routes live in nested route directories (`companies/$ticker.tsx`, `personality/t/$code.tsx`) rather than dot-notation filenames so Vite emits clean chunk names without `._` segments, and `apps/web/scripts/verify-build-assets.mjs` fails the build if any manifest-referenced client chunk is missing or uses a `._` filename.

```tsx
// apps/web/src/utils/route-warmup.ts
export async function warmRouteChunks(
    router: WarmupRouterLike,
    signal?: AbortSignal,
): Promise<void> {
    if (isDataSaverEnabled()) return;
    const seenRouteIds = new Set<string>();
    const paths: readonly string[] = [
        ...PRELOAD_WARMUP_ROUTES,
        ...Object.values(DYNAMIC_WARMUP_SAMPLE_PATHS),
    ];

    for (const path of paths) {
        if (signal?.aborted) return;
        await warmMatchedPath(router, path, seenRouteIds, signal);
    }
}
```

`warmMatchedPath` resolves each path through `router.getMatchedRoutes(path)` and hands every matched route to `warmSingleRoute`, which skips already-seen route ids, skips any route declaring `route.options.preload === false`, and calls `router.loadRouteChunk(route)` inside a `try/catch` so a single failing chunk never aborts the sweep. Between successfully warmed chunks it yields via `yieldToIdleFrame` (`requestIdleCallback` with a 500 ms timeout, falling back to `setTimeout(0)`), which also removes its `abort` listener and cancels the pending idle/timeout handle when the signal fires.

`useIdleRouteWarmup` owns an `AbortController`, passes its `signal` into `warmRouteChunks`, and aborts it in the effect cleanup alongside the idle-callback cancel — so unmounting the root route stops the sweep mid-flight.

### Why Chunk-Only Warmup Eliminates 404s Without NetworkError Noise

1. **Pre-Populated Browser Module Cache**: During browser idle time, `router.loadRouteChunk(route)` downloads and compiles allowlisted route JS chunks into memory.
2. **Zero Unrequested Loader Traffic**: Unlike `router.preloadRoute()`, `loadRouteChunk()` never runs route `loader` or `beforeLoad` handlers, avoiding unrequested `_serverFn` and Archive DB fetches that would otherwise abort with Firefox `TypeError: NetworkError when attempting to fetch resource.` on navigation.
3. **Atomic Deploy Invariance & Zero Main-Thread Congestion**: Active sessions already hold compiled route modules in memory, and running under `requestIdleCallback` leaves FCP, LCP, and INP uninhibited.
4. **Data-Saver Respect**: `isDataSaverEnabled()` reads `navigator.connection.saveData` and short-circuits the entire sweep on metered connections.

---

## Immutable CDN Asset Caching

All hashed build assets under `/assets/*` are configured with 1-year immutable caching in `apps/web/netlify.toml` and `apps/web/public/_headers`:

```toml
[ [headers] ]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
    X-Content-Type-Options = "nosniff"
```

This guarantees that once an asset is fetched, proxy caches and browser disk caches serve it indefinitely without revalidation 404s.

---

## Bounded Chunk Recovery & Transparent Telemetry

In `apps/web/src/components/ui/DefaultCatchBoundary.tsx`:

1. **Telemetry Before Reload**: All exceptions—including dynamic chunk failures—are transparently captured to PostHog Error Tracking via `posthog.captureException(err, { source: 'DefaultCatchBoundary', is_root, pathname, route_id, chunk_error, auto_reloaded })` *before* any page reload is dispatched so requests are never aborted mid-flight. Telemetry is never dropped or suppressed. The whole report-and-dispatch sequence runs inside a `window.setTimeout(..., 0)` macrotask (cleared on effect cleanup) so the parent `PostHogProvider`'s `useEffect` `init()` completes on cold root-level errors before storage is claimed or telemetry is sent.
2. **Claim-Then-Dispatch Self-Healing (`chunk-reload.ts`)**: When `isDynamicChunkError(error)` detects a stale deployment chunk error (e.g. Chromium `Failed to fetch dynamically imported module` or Firefox `error loading dynamically imported module`), `DefaultCatchBoundary` atomically claims the slot via `claimChunkReloadAttempt()` (returning `'reloading' | 'circuit_open'`), reports `auto_reloaded` truthfully to PostHog, transitions the attempt to `dispatched`, and then invokes `reloadAtTarget(targetHref)`.
   - `claimChunkReloadAttempt()` delegates to `shouldAllowReloadAttempt`, which reads state through `readReloadState`. That helper **fails closed** (`count: Number.POSITIVE_INFINITY`) whenever the stored timestamp or count is non-finite, negative, or otherwise corrupted (`NaN`), and also fails closed when `sessionStorage` is unavailable, throws `SecurityError` on property access, or throws `QuotaExceededError` on write. A reload can therefore never loop infinitely.
   - The counter resets once `now - lastTs > cooldownMs` (default 60 s), so a genuine second deploy later in the session can still self-heal.
   - `reloadAtTarget(url?)` enforces same-origin safety: a missing URL, a cross-origin URL, or a same-origin URL whose `origin + pathname + search` match the current location all call `location.reload()` (so `#hash` URLs never stall on a hash jump); a different same-origin path assigns `window.location.href`. Any `URL` parse failure falls back to `location.reload()`.
   - `triggerChunkReload()` is now a thin wrapper: it calls `claimChunkReloadAttempt(options)` and returns `false` on `'circuit_open'`, otherwise invokes `options.reloadFn ?? reloadAtTarget`.
3. **Chunk Recovery Presentation (`ChunkRecoveryView`)**: Chunk errors never render the generic `ErrorComponent`. Instead the boundary renders a recessed `.voxel-trough` status line plus a `Reload Page` ghost button, with copy driven by the `ChunkRecoveryPhase` (`checking` → `reloading` → `dispatched` | `circuit_open`): `Checking application update…`, `Updating application to latest version…`, and `Unable to load the latest application update. Please reload the page.` when the circuit breaker suppresses a repeat reload within the cooldown window.
4. **Standard Error Presentation**: For non-chunk errors, `DefaultCatchBoundary` renders the design system `ErrorComponent` with Try Again and Back/Home navigation actions.

---

## Testing & Verification

- `apps/web/src/utils/route-warmup.test.ts`: Verifies `PRELOAD_WARMUP_ROUTES` includes `/recipes-demo`, `/recipes`, and `/profile`, that `DYNAMIC_WARMUP_SAMPLE_PATHS` covers `/portfolios/$portfolioId`, and that `/today` and `/logout` are excluded. Asserts `warmRouteChunks` warms allowlisted and dynamic route chunks via `loadRouteChunk` while never calling `preloadRoute`, `loader`, or `beforeLoad`, skips a route declaring `preload: false`, and stops warming remaining routes once an `AbortSignal` aborts.
- `apps/web/src/routes/-__root.test.tsx`: Verifies `useIdleRouteWarmup` resolves `/recipes-demo` through `getMatchedRoutes`, warms it via `loadRouteChunk`, and never invokes `preloadRoute` or the route `loader`.
- `apps/web/src/utils/chunk-reload.test.ts`: Verifies `isDynamicChunkError`, `claimChunkReloadAttempt` fail-closed behavior on corrupted `NaN`/negative storage values, on a throwing `setItem` (`QuotaExceededError`), and on a `sessionStorage` getter that throws `SecurityError`; verifies the cooldown reset after 61 s; verifies `reloadAtTarget` reloads for a same-page `#hash` URL, ignores cross-origin URLs (reloading instead of navigating), and navigates for a different same-origin path; and verifies `setupVitePreloadErrorHandler` preserves `defaultPrevented === false`.
- `apps/web/src/components/ui/DefaultCatchBoundary.test.tsx`: Verifies that under `StrictMode` a chunk error renders `Checking application update…`, triggers exactly one bounded reload, reports `chunk_error: true` / `auto_reloaded: true` to PostHog before reload, then transitions to the circuit-open copy with `auto_reloaded: false` on a second chunk error within cooldown. Also verifies non-chunk errors render `ErrorComponent`, deduplicate consecutive captures for the same error instance, normalize string errors into `Error` instances, and fall back to `console.error` when `captureException` is unavailable.
- `apps/web/src/test/netlify-config.test.ts`: Verifies that immutable caching headers are declared in `netlify.toml`.

---

## Related

- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR architecture
- [[concepts/posthog-stealth-proxy]] — Client exception capture and PostHog ingestion
- [[concepts/state-machines]] — `ChunkRecoveryPhase` lifecycle registry
- [[entities/web-app]] — The TanStack Start client dashboard
