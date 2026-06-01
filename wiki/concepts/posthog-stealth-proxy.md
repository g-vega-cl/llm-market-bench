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

To slash client-side bundle size and eliminate unneeded third-party network activity, the `PostHogProvider` is configured to disable heavy session recording while keeping automatic click/event tracking active:
- `disable_session_recording: true` — completely prunes the download of the bulky `posthog-recorder.js` script (~49 KiB) and auxiliary survey chunks, yielding significant performance savings.
- **Autocapture & Pageviews**: Automatic click and pageview tracking remain fully enabled to capture comprehensive navigation and usage telemetry.

This reduces the client-side JavaScript transport weight by **~49 KiB**, accelerating Largest Contentful Paint (LCP) and Time to Interactive (TTI) while preserving complete autocapture and product analytics capabilities.

## Testing

A Vitest unit test in `-__root.test.tsx` mocks the PostHogProvider and verifies that `options.api_host` is set to `'/p'` when rendered on the client.

## Related

- [[entities/web-app]] — Dashboard where analytics are collected
- [[concepts/observability-standard]] — Traceback hardening and LLM audit tracking
- [[sources/web-deployment-source]] — Netlify deployment configuration
