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

To slash client-side bundle size, eliminate unneeded third-party network activity, and prevent render-blocking on the critical paint path, the application uses deferred SDK initialization:
- **Deferred Declarative Initialization**: Initializing PostHog via the declarative component wrapper `<PostHogProvider apiKey={...} options={{ ... }}>` inside `__root.tsx` ensures the SDK is lazy-loaded out of the critical rendering path. As documented in [[concepts/performance-auditing-strategy]], top-level synchronous initialization was avoided because it bundled `posthog-js` into `main.js` and caused Lighthouse unused JavaScript penalties.
- **SSR & Hydration Safety**: The provider dynamically manages client-side activation without emitting tracking script tags in the initial server-rendered HTML payloads, protecting FCP and LCP scores.
- **Pruned Features**: Session recording and surveys are explicitly disabled (`disable_session_recording: true`, `disable_surveys: true`) to strip the download of `posthog-recorder.js` (~49 KiB) and survey chunks.
- **Proxy Caching Override Awareness**: Dynamic feature scripts (like `dead-clicks-autocapture.js?v=1.364.1`) are fetched via the same-origin `/p/static/*` rewrite proxy. Because Netlify forwards the upstream headers of the proxied destination, the custom `Cache-Control` header defined in `netlify.toml` is overridden by PostHog's asset CDN headers, resulting in a short 4-hour Cache TTL.

## Error Tracking & Security Scanner Suppression

Web telemetry is frequently probed by automated security sandboxes (notably **Microsoft 365 Defender / Outlook "Safe Links"** crawlers originating from Azure data centers such as Boydton, VA and Des Moines, IA). 

### The CefSharp Bridge Artifact
These crawlers run in headless **CefSharp** (.NET Chromium Embedded Framework) environments and inject host objects into the page to monitor DOM changes and detect phishing:
1. The scanner executes an injected script that calls `.update(p1, p2, p3, p4)` on an internal C# host object (`Id: 2`).
2. Once the scan determines the URL is safe, the host process immediately terminates the session and disposes the host object.
3. Pending asynchronous callbacks in the browser continue executing and attempt to call `.update()` again, producing an unhandled rejection:
   `"Non-Error promise rejection captured with value: Object Not Found Matching Id:2, MethodName:update, ParamCount:4"`
4. Because `capture_exceptions: true` is enabled in `__root.tsx`, PostHog listens to `window.onunhandledrejection` and captures these synthetic scanner errors.

### Suppression Strategy
- **Zero App Code Overhead**: Rather than bloating client bundles with custom interception code or risking email deliverability by blocking security crawlers at the WAF, the platform relies on PostHog's native **Error Tracking Suppression Rules**.
- **Active Rule**: A suppression rule configured on `properties.$exception_message` drops incoming exceptions where the message contains `Object Not Found Matching Id` and `MethodName:update`.
- **Remote Config Lifecycle (`posthog-js#2327`)**: PostHog SDK fetches suppression rules asynchronously from `/p/decide/`. Exceptions thrown in the earliest milliseconds before remote config resolves can occasionally be transmitted client-side before the server-side ingestion rule drops them.
- Non-Retroactivity: Suppression rules only apply to future ingested events. Historical events captured before rule creation remain in ClickHouse and appear in weekly digests until the issue status is set to Suppressed or the retention window expires.

## Identity resolution and session lifecycle

To accurately track conversion funnels without splitting user profiles or leaking sessions across shared devices, the application standardizes on a client sync lifecycle:

- **Anonymous Tracking**: Unauthenticated visitors receive a device-scoped UUID from `posthog-js`, stored under `ph_<token>_posthog` cookies and `localStorage`. All initial pageviews and clicks are tracked under this anonymous distinct ID.
- **Centralized Synchronization (`PostHogAuthSync`)**: In `apps/web/src/routes/__root.tsx`, the `PostHogAuthSync` component sits inside `PostHogProvider` and monitors the route context `user`. When a user authenticates via password, signup, or Google OAuth redirect, the component checks `posthog.get_distinct_id() !== user.id`. If different, it executes `posthog.identify(user.id, { email: user.email })`.
- **Automatic Person Merging**: Calling `posthog.identify()` with the Supabase `user.id` (UUID) causes PostHog to issue an `$identify` event with `$anon_distinct_id` set to the previous visitor UUID. PostHog automatically merges the anonymous person record into the identified profile on ingestion.
- **UUID over Email**: The application strictly avoids using raw email strings as primary distinct IDs to avoid profile fragmentation when emails change or differ in casing. Email is stored as a person property.
- **Client Session Reset on Logout**: In `apps/web/src/routes/logout.tsx`, `LogoutComponent` calls `posthog.reset()` on the client before completing server-side signout. This generates a fresh anonymous distinct ID, clearing identified person attributes and preventing subsequent anonymous actions from corrupting the previous account history.

## Testing

- `src/routes/-__root.test.tsx` tests that `PostHogProvider` initializes with `/p`, sets `disable_surveys: true`, and verifies that `PostHogAuthSync` identifies users with UUID and email properties while avoiding redundant calls.
- `src/routes/logout.test.tsx` verifies that `LogoutComponent` triggers `posthog.reset()` before executing signout and navigation.

## Related

- [[entities/web-app]] — Dashboard where analytics are collected
- [[concepts/observability-standard]] — Traceback hardening and LLM audit tracking
- [[concepts/performance-auditing-strategy]] — Deferred third-party SDK initialization and bundle budget rules
- [[sources/web-deployment-source]] — Netlify deployment configuration
