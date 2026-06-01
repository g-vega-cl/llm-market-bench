---
tags: [observability, analytics, ad-blocker, proxy, posthog]
category: concept
---

# PostHog Stealth Proxy

A three-layer same-origin reverse proxy architecture that prevents browser ad blockers from blocking PostHog analytics by routing all client-side telemetry through `/p` on the application's own domain. Layered with a custom React context and `requestIdleCallback` deferral so the heavy `posthog-js` runtime never appears on the critical render path.

## Problem

Browser extensions and privacy-focused browsers commonly block requests to known analytics domains like `us.i.posthog.com` and `us-assets.i.posthog.com`. This causes loss of product analytics, error tracking, and session recordings in production. Separately, `posthog-js` and its autoload scripts (`exception-autocapture.js`, `dead-clicks-autocapture.js`, `web-vitals.js`, `array/*/config.js`) add ~30 KiB of always-on JavaScript to the LCP path that can degrade Core Web Vitals.

## Solution: Three-Layer Architecture

### Layer 1: Client Configuration

The `PostHogLazyBoundary` in `__root.tsx` mounts inside the root layout. When it eventually calls `posthog.init(apiKey, config)`, it passes `api_host: '/p'` (relative path) instead of the full PostHog URL. This ensures all SDK requests go to the same origin as the app. `__root.tsx` does **not** statically `import` anything from `@posthog/react` — see the lazy loading layer below for why that matters.

### Layer 2: Local Development Proxy

`vite.config.ts` proxies paths under `/p` to the appropriate PostHog endpoints:
- `/p/static/*` → `https://us-assets.i.posthog.com/static/*` (asset ingestion)
- `/p/array/*` → `https://us-assets.i.posthog.com/array/*` (event arrays)
- `/p/*` → `https://us.i.posthog.com/*` (API requests)

Each proxy rule uses `changeOrigin: true` and `secure: false` for seamless forwarding.

### Layer 3: Production Edge Proxy

`netlify.toml` defines Netlify Edge CDN redirects with `status=200` (server-side rewrite) for the same path patterns. These are invisible to the browser and cannot be blocked by client-side extensions.

### Server-Side Exception

Server-side tracking (`posthog-server.ts`) connects directly to `https://us.i.posthog.com` without the proxy, since server-to-server traffic runs in Netlify Functions and is immune to ad blockers.

## Lazy Client Loading (2026-06-01)

To slash client-side bundle size and eliminate unneeded third-party network activity, the wrapper was rewritten to drop the static `import` of `@posthog/react` (which itself statically imports `posthog-js`) and to defer the actual `posthog.init()` call until the browser is idle.

### Why bypass `@posthog/react` entirely

A static `import { usePostHog } from '@posthog/react'` anywhere in the codebase is enough to pull 30+ KiB of `posthog-js` into the main bundle, even if the value is only consumed in a single component. Vite's tree-shaker cannot eliminate it because the wrapper's source code is `import posthogJs from 'posthog-js'` at module top-level. The fix: implement a thin custom React context (`PostHogContext`) inside `src/lib/posthog-client.tsx` and provide a `useAnalytics()` hook that reads from that context. `useAnalytics()` returns a noop until the real client is in scope, so call sites stay simple and safe.

```ts
// src/lib/posthog-client.tsx (sketch)
const PostHogContext = createContext<PostHogLike | null>(null);

export function useAnalytics(): PostHogLike {
    const ctx = useContext(PostHogContext);
    if (initStarted && ctx) return ctx;
    return NOOP_ANALYTICS; // safe noop before init
}

export async function initPostHog(): Promise<PostHogLike | null> {
    if (typeof window === 'undefined') return null;
    if (posthogInstance) return posthogInstance;
    if (initPromise) return initPromise;
    initPromise = (async () => {
        const mod = await import('posthog-js');           // ← only fetched on idle
        const posthog = mod.default as unknown as PostHogLike;
        const { apiKey, config } = getPostHogInitConfig();
        if (apiKey) posthog.init(apiKey, config);
        posthogInstance = posthog;
        return posthog;
    })();
    return initPromise;
}
```

`PostHogLazyBoundary` schedules `initPostHog()` on `requestIdleCallback` (with a `setTimeout(2000)` fallback) inside a `useEffect`, then renders a real provider wrapping the children. Until the boundary's `useState` flips, children are rendered as plain `<>{children}</>` — no provider, no context, no leak of the lazy module into the SSR HTML.

### Disabled Features

`getPostHogInitConfig()` in `posthog-client.tsx` returns a config that explicitly disables heavy feature modules:
- `disable_session_recording: true` — prunes the bulky `posthog-recorder.js` script (~49 KiB).
- `disable_surveys: true` — skips the survey bundle.
- `capture_exceptions: false` — no extra `/static/exception-autocapture.js` request.
- `capture_dead_clicks: false` — no extra `/static/dead-clicks-autocapture.js` request.
- `defaults: '2025-05-24'` — pins feature defaults to a snapshot that does not flip new heavy modules on retroactively.

### Proxy Caching Headers

Because the versioned tracking assets (e.g. `dead-clicks-autocapture.js?v=1.364.1`) are served via Netlify's dynamic proxy redirect (`status = 200`), they default to short or missing cache lifetimes. To prevent browser re-downloads that block the main thread, `netlify.toml` defines explicit, long-term CDN caching headers for `/p/static/*` (`Cache-Control = "public, max-age=31536000, immutable"`), accelerating LCP and TTI.

### Bundle Impact

The combined stealth + lazy approach reduces the client-side JavaScript transport weight by **~178 KiB**:
- **~30 KiB** removed from the main bundle (no static `posthog-js` import via `@posthog/react`).
- **~49 KiB** removed via `disable_session_recording: true` (no `posthog-recorder.js`).
- **~99 KiB** removed via the disabled autocapture flags (no `exception-autocapture.js`, `dead-clicks-autocapture.js`, `web-vitals.js`, `array/*/config.js`).
- **`main-*.js` shrank from 554 KB to 376 KB** — a 32% reduction in the homepage main bundle.

## Testing

Vitest unit tests in `src/lib/posthog-client.test.ts` (5 cases) and `src/routes/-__root.test.tsx` (2 cases) assert:
- `posthog.init()` is never called at module import time
- `capture_exceptions: false`, `capture_dead_clicks: false`, `disable_session_recording: true`, `disable_surveys: true`
- `api_host: '/p'` is the configured value
- The boundary is mounted in the root layout but does not crash when the idle callback never fires (jsdom)
- `__root.tsx` does not statically `import` anything from `@posthog/react`

## Related

- [[entities/web-app]] — Dashboard where analytics are collected
- [[concepts/observability-standard]] — Traceback hardening and LLM audit tracking
- [[concepts/performance-auditing-strategy]] — Performance budget and 10-fix homepage optimization
- [[sources/web-deployment-source]] — Netlify deployment configuration
