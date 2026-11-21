---
tags: [web, deployment, resilience, tanstack-start, error-handling, payload-shape]
category: concept
---

# Deploy-Skew Payload Tolerance

Netlify publishes atomic deploys, but a browser tab that is already open keeps running the bundle it loaded. When a new deploy changes a route loader's payload shape, that stale client can receive a payload it was not compiled against — a renamed key, a dropped array, a `null` where an object used to be. Without a guard the first property access on the missing field throws during render and the whole route falls to the error boundary, even though the page's data is otherwise fine.

This concept documents the defensive normalization layer that keeps the homepage and the live desk rendering through that skew. It is the *data-shape* counterpart to [[concepts/chunk-reload-recovery]], which handles the *module-level* failure (`Failed to fetch dynamically imported module`) that the same deploy skew produces when a stale tab navigates to a route whose chunk hash no longer exists.

## The Failure Mode

1. A user loads `/` on deploy N. The client bundle and the SSR loader payload agree.
2. Deploy N+1 ships. The loader now returns a payload with a different shape (e.g. `portfolios` moved, `desk.cards` renamed, a count field removed).
3. The stale tab re-runs the route loader — via a client-side navigation, a background refetch, or `router.invalidate()` — and receives the **new** payload into the **old** component.
4. `portfolios.filter(...)` or `desk.cards.length` throws `TypeError: Cannot read properties of undefined`, and the route renders the error boundary instead of the page.

A reload fixes it, but the user should never have to see the boundary for a payload that is merely shaped differently.

## The Pattern: Normalize at the Boundary

Every value that crosses the loader → component boundary is coerced to its expected shape before it is read. Two rules:

- **Arrays** — `Array.isArray(value) ? value : []`. A missing or non-array collection renders as an empty collection, never as a crash.
- **Numbers and nullable scalars** — `Number(value ?? 0)` for counts, and an explicit `typeof value === 'number' ? value : null` for values whose `null` is meaningful (a median that has no data yet must stay `null`, not become `0`).

Normalization happens once, at the outermost point that owns the payload, so downstream components can keep their plain, non-defensive code.

## Shared Normalizers (`apps/web/src/features/home/api/home-payload.ts`)

`normalizeDesk`, `normalizeLeaderboard`, `EMPTY_DESK`, and `getHomePayload()` live in one module shared by both public surfaces — `/` (`apps/web/src/routes/index.tsx`) and `/live-desk` (`apps/web/src/routes/live-desk.tsx`).

```tsx
function normalizeDesk(value: unknown): PublicDesk {
    const raw = (value ?? {}) as Partial<PublicDesk>;
    return {
        cards: Array.isArray(raw.cards) ? raw.cards : [],
        feed: Array.isArray(raw.feed) ? raw.feed : [],
        liveCount: Number(raw.liveCount ?? 0),
        beatSpyCount: Number(raw.beatSpyCount ?? 0),
        medianReturnPct: typeof raw.medianReturnPct === 'number' ? raw.medianReturnPct : null,
        spotlight:
            raw.spotlight && typeof raw.spotlight === 'object'
                ? (raw.spotlight as PublicDesk['spotlight'])
                : null,
    };
}
```

The signature takes `unknown` on purpose: the whole point is that the value is not trusted to match `PublicDesk`. `medianReturnPct` stays `null` when absent so `formatPct` renders its `—` unknown marker rather than a fabricated `0.00%` (see [[entities/recipe-studio]] for the desk's materialised stats).

`normalizeLeaderboard` additionally coerces the nested `worst` row through `normalizeRows([raw.worst])[0] ?? null` (its `series` array also crosses the boundary), keeps `trackedCount` `null` when absent or non-finite, defaults `windowDays` to `30`, and treats an absent payload as `degraded: true` — an unknown board, not a young one.

## Independent Degradation (`getHomePayload`)

`getHomePayload()` runs `fetchPublicDesk()` and `fetchPortfolioLeaderboard()` in a `Promise.all` where **each read degrades on its own**: a failed desk resolves to `EMPTY_DESK`, a failed leaderboard resolves to `emptyLeaderboard(true)` and logs. A missing view and an empty board are different facts, so the page can say "unavailable" instead of "young". This also keeps the front door rendering during the window before a migration has been applied.

## Component-Level Guards

`HomePlaygroundPage` and `RecipePlayground` receive already-normalized values, so they carry no defensive array checks. The remaining guards are in the pure helpers, which are also called from tests and story fixtures:

- `pickProof(leaderboard)` (`apps/web/src/features/playground/lib/proof.ts`) treats a missing payload as no rows, no worst row, `windowDays: 30`, and `degraded: false`.
- `normalizeMood(value)` (`apps/web/src/features/playground/lib/mood.ts`) returns `{ kind: 'unknown' }` for a missing row or an unrecognised direction, and `{ kind: 'stale' }` for an unparseable timestamp.
- `normalizeLaunchRow(row)` (`apps/web/src/features/playground/lib/launch-result.ts`) checks every nullable RPC column before trusting it and never returns a variant without a recipe id or a message.

## Why Not Just Reload?

A reload is the correct response to a *chunk* failure (the code itself is gone — see [[concepts/chunk-reload-recovery]]), but it is the wrong response to a *shape* mismatch. The stale bundle is still perfectly executable; only one field is missing. Forcing a reload would discard the user's scroll position, in-flight form state, and any open inspection slot for a defect the component can absorb silently. Normalization degrades the page to an empty-but-valid state; the next natural navigation picks up the new bundle.

## Testing

- `apps/web/src/features/playground/pages/HomePlaygroundPage.test.tsx` renders the page with a normalized mood, a `pickProof` result, and an empty desk, and asserts the builder, the mood sentence, the published loser, and the request form gating.
- `apps/web/src/features/playground/lib/proof.test.ts` asserts `pickProof(undefined)` does not throw and that a `degraded` payload is reported as degraded.
- `apps/web/src/features/playground/lib/launch-result.test.ts` asserts `normalizeLaunchRow(null)` still yields an `error` variant with a non-empty message.

## Related

- [[concepts/chunk-reload-recovery]] — the module-level failure the same deploy skew causes, and its bounded reload path
- [[entities/recipe-playground]] — the homepage that consumes these normalizers
- [[entities/web-app]] — the homepage and `/live-desk` routes
- [[concepts/recipe-public-stats]] — the desk payload being normalized
- [[concepts/rendering-strategies]] — loader/hybrid-SSR data flow this guard sits inside
