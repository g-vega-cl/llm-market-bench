---
tags: [web, stale-data, refresh, router, posthog, performance]
category: concept
---

# Window Focus Refresh

Window focus refresh keeps dashboard data fresh without background polling. When the user returns to the tab — either by focusing the browser window or by making a hidden tab visible again — the app re-runs the current route's loaders so stale portfolio values, market feeling, barometer, and tape snapshots are replaced with current data.

The mechanism lives in the reusable hook `apps/web/src/features/home/hooks/useWindowFocusRefresh.ts` and is wired into the homepage route component (`apps/web/src/routes/index.tsx`).

## The Problem It Solves

SSR/hybrid-SSR loaders populate the page once. A user who leaves the tab open for minutes or hours would otherwise read a frozen snapshot (a stale Fed decision, an old P/E, an outdated tape). Interval polling would fix staleness but costs constant CPU, network, and battery on every idle tab — the opposite of the project's performance posture (see [[concepts/performance-auditing-strategy]]). Focus refresh is event-driven: work happens only at the moment the user could actually observe it.

## Mechanics

### Triggers

Two listeners are registered on mount:

1. `window` `focus` — the browser window regains focus.
2. `document` `visibilitychange` — the tab transitions between hidden and visible.

A `visibilitychange` firing while `document.hidden === true` is ignored, so backgrounding a tab never triggers a refresh.

### Throttle

Both triggers funnel into one handler guarded by a monotonic timestamp (`lastRefreshRef`). A refresh fires only when `Date.now() - lastRefreshRef >= throttleMs`, with `throttleMs` defaulting to `5000` (5 seconds). Because the ref is initialized to `Date.now()` at mount, an immediate focus in the first five seconds after page load is suppressed — the first paint is already fresh.

### Latest-Callback Semantics

The `onRefresh` callback is stored in a ref and updated on every render, so the listener always invokes the newest closure while the effect only re-subscribes when `enabled`, `throttleMs`, or the `posthog` client actually change.

### PostHog Synchronization

When a `posthog` client is supplied, each successful refresh also:

- calls `posthog.reloadFeatureFlags()` so feature-flag evaluation (e.g. the homepage background experiment, see [[entities/shader-background]]) reflects flag changes made while the tab was backgrounded, and
- captures the analytics event `window_focus_refreshed` with `{ path: '/' }`.

Either method is optional and invoked defensively, so a partial or missing client never breaks the refresh path. Identity and session lifecycle behavior are documented in [[concepts/posthog-stealth-proxy]].

### Opt-Out and Cleanup

Passing `enabled: false` skips listener registration entirely (both listeners are also skipped when `window` is undefined, i.e. during SSR). The effect cleanup removes both listeners, so unmounted routes never fire refreshes.

## Route Wiring

`RouteComponent` in `apps/web/src/routes/index.tsx` attaches the hook:

```tsx
const router = useRouter();
const posthog = usePostHog();

useWindowFocusRefresh({
    onRefresh: () => {
        router.invalidate();
    },
    posthog,
});
```

`router.invalidate()` re-runs the active route's loaders, so every datum the homepage loader assembles — market feeling, active portfolios, benchmark barometer, and intraday tape bars — is refetched through the existing server functions. No bespoke refetch logic is added, and the refresh inherits the same caching and fallback semantics described in [[entities/web-app]] and [[concepts/rendering-strategies]].

## Testing

- `apps/web/src/features/home/hooks/useWindowFocusRefresh.test.ts` covers focus-triggered refresh, visibility-triggered refresh, the hidden-document guard, throttle suppression and re-arm, PostHog flag reload plus telemetry capture, listener cleanup on unmount, and the `enabled: false` opt-out. Timers are faked so the 5-second throttle is exercised deterministically.
- `apps/web/src/routes/-index.test.tsx` renders `RouteComponent` with mocked router and PostHog hooks and asserts that a focus event (after the cooldown) calls `router.invalidate()` exactly once alongside `reloadFeatureFlags()` and the `window_focus_refreshed` capture.

## Related

- [[entities/web-app]] — the homepage route that consumes the hook
- [[concepts/posthog-stealth-proxy]] — feature flag reload and telemetry conventions
- [[concepts/rendering-strategies]] — loader and hybrid-SSR data flow the refresh re-invokes
- [[concepts/performance-auditing-strategy]] — why event-driven refresh beats interval polling
