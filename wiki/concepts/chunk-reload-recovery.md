---
tags: [web, deployment, resilience, chunks, vite, error-handling]
category: concept
---

# Dynamic Chunk Failure & Deployment Recovery

The web app is a code-split TanStack Start SPA/SSR hybrid: every route and heavy visualization library is emitted as a content-hashed chunk (`index-[hash].js`, `vendor-d3-[hash].js`). When a new deployment is published while a user still has a tab open, the old hashed chunks are purged from the CDN. The next client-side navigation or lazy import then requests a chunk that no longer exists and the browser throws a dynamic-import failure. This concept documents the two-layer self-healing path that turns that hard failure into a silent, single reload.

## The Failure Mode

A stale tab holds a router manifest pointing at build N assets. After build N+1 deploys, clicking a route that lazy-loads a chunk produces a `TypeError` from the module loader. Without handling, the user sees a generic "Something went wrong" error boundary and must reload manually — and the error is indistinguishable from a real application bug in telemetry.

## Layer 1 — Vite `vite:preloadError` Listener

`apps/web/src/utils/chunk-reload.ts` exports `setupVitePreloadErrorHandler(options?)`, which attaches a `window` listener for Vite's `vite:preloadError` event (dispatched automatically by Vite when a dynamically imported chunk fails to fetch). The handler calls `event.preventDefault()` — suppressing Vite's default rethrow — and then invokes `triggerChunkReload(options)`. It returns a cleanup function that removes the listener.

The handler is installed once at module scope in `apps/web/src/routes/__root.tsx`, inside the existing `if (typeof window !== 'undefined')` block, alongside the CefSharp `unhandledrejection` listener (see [[concepts/posthog-stealth-proxy]]):

```ts
if (typeof window !== 'undefined') {
    setupVitePreloadErrorHandler();
    window.addEventListener('unhandledrejection', (event) => { /* ... */ });
}
```

## Layer 2 — `DefaultCatchBoundary` Chunk-Aware Fallback

Errors that reach the router's catch boundary (rather than the preload event) are handled by `apps/web/src/components/ui/DefaultCatchBoundary.tsx`. It computes `isChunkErr = isDynamicChunkError(error)` and, when true:

1. Calls `triggerChunkReload({ targetHref: router.state?.location?.href })` inside the deduplicated `useEffect`, preserving the intended navigation destination, and records the boolean result in the `autoReloadTriggered` React state (via `useState`).
2. Captures the exception to PostHog with `chunk_error: isChunkErr` and `auto_reloaded: autoReloaded` in addition to `source`, `is_root`, `pathname`, and `route_id`.
3. Renders a self-healing state instead of the generic `ErrorComponent`: a recessed `voxel-trough` strip plus a `Reload Page` ghost button that calls `window.location.reload()`.

### Honest Fallback Messaging

The status text is conditional on whether the automatic reload actually fired (i.e. was not suppressed by the circuit breaker):

| `autoReloadTriggered` | Rendered message |
| :--- | :--- |
| `true` | `Updating application to latest version…` |
| `false` | `Unable to load the latest application update. Please reload the page.` |

When the breaker trips (an asset is persistently unavailable — adblocker or CDN failure), the UI stops pretending it is updating and instead asks the user to reload manually. The `Reload Page` button remains available in both states. Non-chunk errors keep the original `ErrorComponent` rendering path unchanged.

## Detection Signatures (`isDynamicChunkError`)

`isDynamicChunkError(error)` normalizes the input (an `Error`, a raw string, or anything else via `String(error)`) to lowercase and matches any of the browser-specific signatures. It inspects both the top-level `error.message` **and** any nested `error.cause` (an `Error` or string), so wrapped route-transition errors that bury the real dynamic-import failure in `cause` are still detected:

| Signature | Browser / Bundler |
| :--- | :--- |
| `failed to fetch dynamically imported module` | Chromium (Chrome, Brave, Edge) |
| `error loading dynamically imported module` | Firefox |
| `importing a module script failed` | WebKit / Safari |
| `loading chunk` **AND** `failed` | Webpack / Rollup chunk load failure |

Falsy input (`null`, `undefined`) and unrelated errors (`Network timeout`, `Cannot read property of undefined`) return `false`. The Webpack/Rollup `loading chunk` signature is deliberately conjunctive (requires `failed` too) so innocuous strings such as `Finished loading chunk into memory` do not over-match.

## Reload Guard (`triggerChunkReload`)

`triggerChunkReload({ targetHref?, cooldownMs?, maxRetries?, storage?, reloadFn? })` performs at most one hard reload/redirect per cooldown window and returns `true` when a reload was triggered, `false` when suppressed by the circuit breaker.

- **SSR guard** — returns `false` immediately when `typeof window === 'undefined'`.
- **Bounded Circuit Breaker** — `MAX_AUTO_RELOADS = 1` attempt per cooldown window (`DEFAULT_COOLDOWN_WINDOW_MS = 60000`). The reload attempt count is persisted in `sessionStorage` under `benchify:chunk_reload_count` and the timestamp under `benchify:last_chunk_reload_ts`. If an asset is persistently missing (adblocker, CDN failure), the breaker trips after 1 attempt, failing closed to the honest manual-reload UI to eliminate infinite reload loops. The count resets to 0 when the previous attempt falls outside the cooldown window, re-arming the auto-reload path.
- **Navigation Destination Preservation** — accepts `targetHref` (e.g. from `router.state?.location?.href`). If the target route differs from the current `window.location.href`, it redirects to `targetHref` rather than resetting the user back to the origin page.
- **Storage failure tolerance** — `getItem`/`setItem` are wrapped in `try/catch` so privacy sandboxes or quota errors fall through to a single reload attempt.
- **Idempotency** — `setupVitePreloadErrorHandler` guards against duplicate window listeners using `window.__benchify_vite_preload_bound__`; a second call returns a no-op cleanup and does not double-register. Cleanup clears the flag so the handler can be re-armed.
- **Injectable dependencies** — `storage` and `reloadFn` are overridable for tests; production defaults are `sessionStorage` and redirecting/reloading. `reloadFn` accepts an optional `url` argument (`(url?: string) => void`) and navigates to it when supplied.

## Testing

- `apps/web/src/utils/chunk-reload.test.ts` covers all detection signatures, nested error causes, string input, negative cases (including the `loading chunk`-without-`failed` non-match), first-reload success with timestamp and count persistence, circuit-breaker suppression on repeated failures, destination target preservation, re-arming after the cooldown expires, and idempotent listener registration/cleanup.
- `apps/web/src/components/ui/DefaultCatchBoundary.test.tsx` asserts a chunk `TypeError` renders the "Updating application to latest version" UI when auto-reloading, displays the honest manual reload message when the circuit breaker suppresses the reload, and captures the exception with `chunk_error: true`.
- `apps/web/src/routes/-__root.test.tsx` dispatches a synthetic `vite:preloadError` on `window` and asserts `event.defaultPrevented` is `true`.

## Related

- [[concepts/rendering-strategies]] — rendering decision matrix and the self-healing recovery rule
- [[concepts/posthog-stealth-proxy]] — `DefaultCatchBoundary` exception capture and the root-route client listeners
- [[entities/web-app]] — the TanStack Start dashboard that ships the hashed chunks
- [[concepts/release-and-canary-deployments]] — deployment/release decoupling and SPA chunk-mismatch risk
