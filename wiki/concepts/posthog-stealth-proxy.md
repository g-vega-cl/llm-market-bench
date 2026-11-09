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

- **Deferred Declarative Initialization**: Initializing PostHog via the declarative component wrapper `<PostHogProvider apiKey={...} options={{ ... }}>` inside `__root.tsx` ensures the SDK is lazy-loaded out of the critical rendering path. As documented in [[concepts/performance-auditing-strategy]], top-level synchronous initialization was avoided because it bundled `posthog-js` into `main.js` and caused Lighthouse unused JavaScript penalties.
- **SSR & Hydration Safety**: The provider dynamically manages client-side activation without emitting tracking script tags in the initial server-rendered HTML payloads, protecting FCP and LCP scores.
- **Session Recording & Privacy Masking**: Session recording is enabled with strict client-side privacy controls (`session_recording: { maskAllInputs: true, maskTextSelector: '[data-ph-mask]' }`). The recording chunk (`recorder.js`) is loaded lazily via the same-origin asset rewrite proxy (`/p/static/*`) without blocking initial paint. Surveys remain disabled (`disable_surveys: true`) to strip unused survey code.
- **Proxy Caching Override Awareness**: Dynamic feature scripts (like `dead-clicks-autocapture.js?v=1.434.17`) and recording assets are fetched via the same-origin `/p/static/*` rewrite proxy. Because Netlify forwards the upstream headers of the proxied destination, the custom `Cache-Control` header defined in `netlify.toml` is overridden by PostHog's asset CDN headers, resulting in a short 4-hour Cache TTL.

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
- **Synchronous `before_send` Drop**: To eliminate the race condition where short-lived crawlers terminate and flush events before `/p/decide/` remote config loads, `apps/web/src/utils/posthog-filter.ts` implements a synchronous `before_send` lifecycle filter.
- **Complete Discard via `return null`**: In PostHog, Error Tracking tracks all `$exception` events regardless of `$exception_level`. Merely downgrading severity to `'warning'` still creates issues and triggers weekly error digests. Instead, `posthogBeforeSend` returns `null` when a CefSharp scanner exception signature (`Object Not Found Matching Id` and `MethodName:`) is detected. This completely drops the event at the SDK level, preventing transmission, ingestion, and spurious Error Tracking issues. Genuine application exceptions pass through intact.
- **Console Warning Handler**: A top-level client listener on `window.addEventListener('unhandledrejection')` prevents default browser error logging for CefSharp host bridge rejections, issuing an informational `console.warn` instead and calling `stopImmediatePropagation()`.
- **Non-Retroactivity**: Ingested events captured prior to the filter appear in weekly digests until the issue status is set to Suppressed or the retention window expires.

## Canonical Error Tracking Standard (`posthog.captureException`)

To ensure application errors and backend service interruptions are visible in PostHog's **Error Tracking** dashboard (rather than scattered or lost among generic analytics events), the platform establishes a canonical error capture standard:

### 1. `posthog.captureException()` over Generic `posthog.capture()`

- **Dedicated Error Tracking ($exception)**: Call `posthog.captureException(err, extraProperties)`. PostHog automatically serializes the error as an official `$exception` event with stack trace, error name, and `$exception_handled: true`.
- **Automatic Grouping & Triage**: Exceptions are grouped by fingerprint and stack trace in PostHog Error Tracking, allowing engineers to assign, resolve, and monitor regression rates across releases.
- **Custom Event Contrast**: Using `posthog.capture('custom_error_name', ...)` alone is insufficient for error reporting because it only increments analytics event counts and does not appear in PostHog Error Tracking.
- **Dual-Capture Pattern**: When monitoring user-facing feature disruptions (such as LLM endpoint outages in `ConsoleQueueCard.tsx`), pair `posthog.captureException(err, properties)` for issue tracking with an optional `posthog.capture('agent_chat_endpoint_error', properties)` for dashboard trend graphs.

```typescript
const err = new Error(`Agent Q&A LLM Outage: All endpoints unavailable for question "${latestAnswered.message}"`);
err.name = 'AgentLLMOutageError';

// 1. Official Error Tracking issue creation ($exception event)
posthog.captureException(err, {
    feature: 'agent_chat_queue',
    question: latestAnswered.message,
    author: latestAnswered.display_name,
    user_id: latestAnswered.user_id,
    error_type: 'llm_endpoints_unavailable',
});

// 2. Custom analytics event for dashboard trend lines
posthog.capture('agent_chat_endpoint_error', {
    question: latestAnswered.message,
    error_type: 'llm_endpoints_unavailable',
});
```

### 2. Client-Side Deduplication

When capturing errors inside reactive React components or lifecycle hooks, always guard against re-render duplicate submissions using a ref (e.g. `trackedErrorIdRef.current !== item.id`), ensuring a persistent error state is reported exactly once per occurrence.

### 3. Route Error Boundary Integration (`DefaultCatchBoundary`)

TanStack Router's internal catch boundary isolates page, loader, and rendering errors without bubbling them to `window.onerror`. To prevent caught exceptions from becoming invisible in production, `apps/web/src/components/ui/DefaultCatchBoundary.tsx` hooks directly into PostHog via `usePostHog()`. When rendered, it records `posthog.captureException(err, { source: 'DefaultCatchBoundary', is_root, pathname, route_id })` guarded by a deduplication ref.

## Server-Side Exception Autocapture & Request Middleware

Server-side failures (server functions, SSR loaders, unhandled promise rejections in the Node runtime) are captured by the `posthog-node` client rather than the browser SDK.

### `enableExceptionAutocapture`

`apps/web/src/utils/posthog-server.ts` initializes the singleton `posthog-node` client with `enableExceptionAutocapture: true` alongside `flushAt: 1` and `flushInterval: 0`, so uncaught server exceptions and unhandled rejections are reported immediately without batching delay. The client targets `VITE_PUBLIC_POSTHOG_HOST` directly (no `/p` proxy — server-to-server traffic is not subject to ad blockers).

### `src/start.ts` Request Middleware

`apps/web/src/start.ts` exports `startInstance = createStart(() => ({ requestMiddleware: [...] }))` with two middlewares:

1. **`createCsrfMiddleware({ filter: ({ handlerType }) => handlerType === 'serverFn' })`** — CSRF protection applied to server-function requests.
2. **`posthogExceptionAutocapture`** — a `createMiddleware().server(...)` handler that calls `getPostHogClient()` before `await next()`, guaranteeing the server-side PostHog client is initialized for every request so exception autocapture is active.

`routeTree.gen.ts` registers the start instance's config type (`config: Awaited<ReturnType<typeof startInstance.getOptions>>`) in the `@tanstack/react-start` module augmentation, so the middleware chain is type-checked against the router.

No duplicate global error listeners are added — browser-caught render errors continue to flow through `DefaultCatchBoundary` and the root error boundary.

## Source Map Uploads (Error Tracking Symbolication)

Production stack traces are minified without source maps. `apps/web/vite.config.ts` wires the `@posthog/rollup-plugin` (devDependency `@posthog/rollup-plugin`) to upload hidden source maps to PostHog Error Tracking during the production build.

### Build Configuration

- **`build.sourcemap: 'hidden'`** — emits `.map` files without a `//# sourceMappingURL` comment, so maps are never served to browsers.
- **Plugin options** — `personalApiKey: process.env.POSTHOG_API_KEY`, `projectId: process.env.POSTHOG_PROJECT_ID`, `host: process.env.POSTHOG_HOST`, and `sourcemaps: { enabled: posthogUploadEnabled, deleteAfterUpload: true }`.
- **Upload gating** — `posthogUploadEnabled = Boolean(posthogApiKey?.startsWith('phx_') && posthogProjectId)`. Upload only runs when a valid personal API key (`phx_` prefix) and project ID are present; otherwise the build proceeds normally with no upload. A non-`phx_` key logs `PostHog source map upload skipped: POSTHOG_API_KEY must be a personal API key.`
- **`deleteAfterUpload: true`** — local `.map` artifacts are removed after a successful upload so they are never published to the CDN.

### Environment Variables

| Variable | Scope | Purpose |
| :--- | :--- | :--- |
| `POSTHOG_API_KEY` | Build only (Netlify env) | Personal API key (`phx_`) with Error Tracking / source-map upload write access |
| `POSTHOG_PROJECT_ID` | Build only (Netlify env) | PostHog project ID receiving the symbol sets |
| `POSTHOG_HOST` | Build only (Netlify env) | PostHog app host for the uploader |
| `VITE_PUBLIC_POSTHOG_PROJECT_TOKEN` | Build + runtime | Public project token used by the browser and server SDKs |
| `VITE_PUBLIC_POSTHOG_HOST` | Build + runtime | Public ingestion host used by the browser and server SDKs |

`apps/web/.env.example` documents the three build-only keys (`POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`, `POSTHOG_HOST`) with placeholder values. `apps/web/netlify.toml` carries a comment documenting that these must be configured in Netlify environment variables for production source-map uploads, and that the deployed app also reads `VITE_PUBLIC_POSTHOG_PROJECT_TOKEN` / `VITE_PUBLIC_POSTHOG_HOST` at build and run time. Netlify supplies the repository and commit metadata used for release identity.

Uploaded symbol sets are visible at `https://us.posthog.com/project/<project_id>/error_tracking/configuration`; captured stack traces resolve against them after the next production deploy.

## Identity resolution and session lifecycle

To accurately track conversion funnels without splitting user profiles or leaking sessions across shared devices, the application standardizes on a client sync lifecycle:

- **Anonymous Tracking**: Unauthenticated visitors receive a device-scoped UUID from `posthog-js`, stored under `ph_<token>_posthog` cookies and `localStorage`. All initial pageviews and clicks are tracked under this anonymous distinct ID.
- **Centralized Synchronization (`PostHogAuthSync`)**: In `apps/web/src/routes/__root.tsx`, the `PostHogAuthSync` component sits inside `PostHogProvider` and monitors the route context `user`. When a user authenticates via password, signup, or Google OAuth redirect, the component checks `posthog.get_distinct_id() !== user.id`. If different, it executes `posthog.identify(user.id, { email: user.email })`.
- **Automatic Person Merging**: Calling `posthog.identify()` with the Supabase `user.id` (UUID) causes PostHog to issue an `$identify` event with `$anon_distinct_id` set to the previous visitor UUID. PostHog automatically merges the anonymous person record into the identified profile on ingestion.
- **UUID over Email**: The application strictly avoids using raw email strings as primary distinct IDs to avoid profile fragmentation when emails change or differ in casing. Email is stored as a person property.
- **Client Session Reset on Logout**: In `apps/web/src/routes/logout.tsx`, `LogoutComponent` calls `posthog.reset()` on the client before completing server-side signout. This generates a fresh anonymous distinct ID, clearing identified person attributes and preventing subsequent anonymous actions from corrupting the previous account history.

## Testing

- `apps/web/src/components/ui/DefaultCatchBoundary.test.tsx` verifies that `DefaultCatchBoundary` records exceptions to PostHog with route context and deduplicates consecutive captures on re-render.
- `apps/web/src/utils/posthog-filter.test.ts` verifies detection of CefSharp unhandled rejections across `$exception_list`, `$exception_values`, and `$exception_message`, confirming that scanner errors are dropped completely (`return null`) while legitimate errors and analytics events pass unchanged.
- `apps/web/src/routes/-__root.test.tsx` tests that `PostHogProvider` initializes with `/p`, enables session recording with privacy masking, sets `disable_surveys: true`, configures `before_send: posthogBeforeSend` dropping scanner errors, and verifies that `PostHogAuthSync` identifies users with UUID and email properties while avoiding redundant calls.
- `apps/web/src/routes/-logout.test.tsx` verifies that `LogoutComponent` triggers `posthog.reset()` before executing signout and navigation.

## Related

- [[entities/web-app]] — Dashboard where analytics are collected
- [[concepts/observability-standard]] — Traceback hardening and LLM audit tracking
- [[concepts/performance-auditing-strategy]] — Deferred third-party SDK initialization and bundle budget rules
- [[concepts/release-and-canary-deployments]] — PostHog SDK boundaries and feature-flag release flow
- [[sources/web-deployment-source]] — Netlify deployment configuration
