---
tags: [observability, analytics, ad-blocker, proxy, posthog]
category: concept
---

# PostHog Stealth Proxy

A three-layer same-origin reverse proxy architecture that prevents browser ad blockers from blocking PostHog analytics by routing all client-side telemetry through `/p` on the application's own domain.

## Problem

Browser extensions and privacy-focused browsers commonly block requests to known analytics domains like `us.i.posthog.com` and `us-assets.i.posthog.com`. This causes loss of product analytics, error tracking, and session recordings in production.

## Solution: Three-Layer Architecture

### Layer 1: Client Configuration

The `PostHogProvider` in `__root.tsx` uses `api_host: '/p'` (relative path) instead of the full PostHog URL. This ensures all SDK requests go to the same origin as the app.

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

## Client Loading Optimization

To slash client-side bundle size, eliminate unneeded third-party network activity, and prevent render-blocking on the critical paint path, the application uses an optimized pre-initialization pattern:
- **Immediate Client-Side Pre-Initialization**: Instead of initializing PostHog during the React render phase, the `posthog-js` SDK is pre-initialized client-side immediately upon JavaScript execution via a guard `if (typeof window !== 'undefined')` and passed directly as a client instance to `<PostHogProvider client={posthog}>`.
- **SSR & Hydration Immunity**: Because the initialization runs strictly client-side, the server-rendered HTML payloads contain zero dynamic tracking scripts, completely shielding FCP and LCP scores from render-blocking overhead while avoiding React 19 hydration mismatches.
- **No Missed Events**: Pre-initializing immediately on JS load ensures the SDK is ready as soon as the DOM hydrates, capturing the initial pageview and early user clicks with 100% reliability.
- **Pruned Features**: Session recording and surveys are explicitly disabled (`disable_session_recording: true`, `disable_surveys: true`) to completely strip the download of the bulky `posthog-recorder.js` (~49 KiB) and survey scripts, shielding the main thread.
- **Proxy Caching Override Awareness**: Dynamic feature scripts (like `dead-clicks-autocapture.js?v=1.364.1`) are fetched via the same-origin `/p/static/*` rewrite proxy. Because Netlify forwards the upstream headers of the proxied destination, the custom `Cache-Control` header defined in `netlify.toml` is overridden by PostHog's asset CDN headers, resulting in a short 4-hour Cache TTL. Client-side pre-initialization ensures these scripts download asynchronously post-hydration, protecting Core Web Vitals from this caching limit.

## Testing

A Vitest unit test in `-__root.test.tsx` mocks the PostHogProvider and verifies that `options.api_host` is set to `'/p'` when rendered on the client.

## Related

- [[entities/web-app]] — Dashboard where analytics are collected
- [[concepts/observability-standard]] — Traceback hardening and LLM audit tracking
- [[sources/web-deployment-source]] — Netlify deployment configuration
