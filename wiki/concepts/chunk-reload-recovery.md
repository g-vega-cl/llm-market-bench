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

## Proactive Prevention: Idle-Time Route Warmup

Rather than reacting to failed chunk fetches after the user clicks a link, the application eliminates chunk 404s proactively using **Idle-Time Route Warmup** (`useIdleRouteWarmup` in `apps/web/src/routes/__root.tsx`).

### Implementation

When the root route mounts in the browser, it schedules background prefetching of all core application routes using `requestIdleCallback` (with a `setTimeout` fallback):

```tsx
// apps/web/src/routes/__root.tsx
export function useIdleRouteWarmup() {
    const router = useRouter();

    useEffect(() => {
        if (typeof window === 'undefined') return;

        const win = window as Window & {
            requestIdleCallback?: (cb: () => void, options?: { timeout: number }) => number;
            cancelIdleCallback?: (id: number) => void;
        };

        const schedule =
            typeof win.requestIdleCallback === 'function'
                ? (cb: () => void) => win.requestIdleCallback?.(cb, { timeout: 2000 }) ?? 0
                : (cb: () => void) => window.setTimeout(cb, 50);

        const cancel =
            typeof win.cancelIdleCallback === 'function'
                ? (id: number) => win.cancelIdleCallback?.(id)
                : (id: number) => window.clearTimeout(id);

        const handle = schedule(async () => {
            for (const path of PRELOAD_WARMUP_ROUTES) {
                try {
                    await router.preloadRoute({ to: path as never });
                } catch {
                    // Non-blocking background warmup
                }
            }
        });

        return () => cancel(handle);
    }, [router]);
}
```

### Why Idle Warmup Eliminates 404s

1. **Pre-Populated Browser Module Cache**: During browser idle time, `router.preloadRoute()` downloads and compiles all route chunks (`/portfolios`, `/lab`, `/companies`, `/today`, `/audits`, `/autoresearch`, `/chat`, etc.).
2. **Atomic Deploy Invariance**: If a new deployment publishes 5 minutes later, the user's active session already holds the compiled route modules in memory. Subsequent navigation executes instantly from memory with zero outbound HTTP requests for JS chunks.
3. **Zero Main-Thread Congestion**: Running under `requestIdleCallback` ensures initial page rendering, data hydration, and interactive metrics (FCP, LCP, INP) are completely uninhibited.

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

## Clean Error Boundary & Transparent Telemetry

In `apps/web/src/components/ui/DefaultCatchBoundary.tsx`:

1. **Zero Muting or Masking**: All exceptions are transparently captured to PostHog error tracking via `captureException(error, { tags: { ... } })`. Telemetry is never dropped, muted, or hidden.
2. **Standard Error Presentation**: If an unhandled error occurs, `DefaultCatchBoundary` renders the design system `ErrorComponent` with a descriptive message and clear user actions:
   - **Try Again**: Re-executes the route loader or boundary reset.
   - **Back / Home**: Safe fallback navigation links.
3. **No Disruptive Banner**: No synthetic reload spinners, reload counts, or auto-reload countdowns.

---

## Testing & Verification

- `apps/web/src/routes/-__root.test.tsx`: Verifies that `useIdleRouteWarmup` registers an idle callback and calls `router.preloadRoute` across all warmup routes. Also verifies that `vite:preloadError` does **not** call `preventDefault()`.
- `apps/web/src/utils/chunk-reload.test.ts`: Verifies `setupVitePreloadErrorHandler` attaches cleanly and preserves `defaultPrevented === false`.
- `apps/web/src/components/ui/DefaultCatchBoundary.test.tsx`: Verifies that `DefaultCatchBoundary` captures chunk errors to PostHog without rendering auto-reload banners or triggering loops.
- `apps/web/src/test/netlify-config.test.ts`: Verifies that immutable caching headers are declared in `netlify.toml`.

---

## Related

- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR architecture
- [[concepts/posthog-stealth-proxy]] — Client exception capture and PostHog ingestion
- [[entities/web-app]] — The TanStack Start client dashboard
