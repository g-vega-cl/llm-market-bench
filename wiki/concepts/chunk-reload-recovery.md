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

1. Calls `triggerChunkReload()` inside the deduplicated `useEffect` and records the boolean result as `autoReloaded`.
2. Captures the exception to PostHog with `chunk_error: isChunkErr` and `auto_reloaded: autoReloaded` in addition to `source`, `is_root`, `pathname`, and `route_id`.
3. Renders a self-healing state instead of the generic `ErrorComponent`: a recessed `voxel-trough` strip reading `Updating application to latest version…` plus a `Reload Page` ghost button that calls `window.location.reload()`.

Non-chunk errors keep the original `ErrorComponent` rendering path unchanged.

## Detection Signatures (`isDynamicChunkError`)

`isDynamicChunkError(error)` normalizes the input (an `Error`, a raw string, or anything else via `String(error)`) to lowercase and matches any of the browser-specific signatures:

| Signature | Browser / Bundler |
| :--- | :--- |
| `failed to fetch dynamically imported module` | Chromium (Chrome, Brave, Edge) |
| `error loading dynamically imported module` | Firefox |
| `importing a module script failed` | WebKit / Safari |
| `loading chunk` | Webpack / Rollup chunk load failure |

Falsy input (`null`, `undefined`) and unrelated errors (`Network timeout`, `Cannot read property of undefined`) return `false`.

## Reload Guard (`triggerChunkReload`)

`triggerChunkReload({ cooldownMs?, storage?, reloadFn? })` performs at most one hard reload per cooldown window and returns `true` when a reload was triggered, `false` when suppressed.

- **SSR guard** — returns `false` immediately when `typeof window === 'undefined'`.
- **Cooldown** — `DEFAULT_COOLDOWN_MS = 15000` (15 seconds). The last reload timestamp is persisted in `sessionStorage` under `benchify:last_chunk_reload`; a call within the window returns `false` without reloading, preventing infinite reload loops when an asset is persistently unavailable.
- **Storage failure tolerance** — `getItem`/`setItem` are wrapped in `try/catch` so privacy sandboxes or quota errors fall through to a single reload attempt.
- **Injectable dependencies** — `storage` and `reloadFn` are overridable for tests; production defaults are `sessionStorage` and `() => window.location.reload()`.

## Testing

- `apps/web/src/utils/chunk-reload.test.ts` covers all four detection signatures, string input, negative cases, first-reload success with timestamp persistence, suppression inside the 15-second cooldown, re-arming after the cooldown expires, and `setupVitePreloadErrorHandler` dispatching `vite:preloadError` (asserting `defaultPrevented === true`) plus listener cleanup.
- `apps/web/src/components/ui/DefaultCatchBoundary.test.tsx` asserts a chunk `TypeError` renders the "Updating application to latest version" UI (and not "Something went wrong") and captures the exception with `chunk_error: true`.
- `apps/web/src/routes/-__root.test.tsx` dispatches a synthetic `vite:preloadError` on `window` and asserts `event.defaultPrevented` is `true`.

## Related

- [[concepts/rendering-strategies]] — rendering decision matrix and the self-healing recovery rule
- [[concepts/posthog-stealth-proxy]] — `DefaultCatchBoundary` exception capture and the root-route client listeners
- [[entities/web-app]] — the TanStack Start dashboard that ships the hashed chunks
- [[concepts/release-and-canary-deployments]] — deployment/release decoupling and SPA chunk-mismatch risk
