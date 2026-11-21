---
tags: [web, deployment, resilience, tanstack-start, error-handling, payload-shape]
category: concept
---

# Deploy-Skew Payload Tolerance

Netlify publishes atomic deploys, but a browser tab that is already open keeps running the bundle it loaded. When a new deploy changes a route loader's payload shape, that stale client can receive a payload it was not compiled against — a renamed key, a dropped array, a `null` where an object used to be. Without a guard the first property access on the missing field throws during render and the whole route falls to the error boundary, even though the page's data is otherwise fine.

This concept documents the defensive normalization layer that keeps loader-driven pages rendering through that skew. It is the *data-shape* counterpart to [[concepts/chunk-reload-recovery]], which handles the *module-level* failure (`Failed to fetch dynamically imported module`) that the same deploy skew produces when a stale tab navigates to a route whose chunk hash no longer exists.

## The Failure Mode

1. A user loads a route on deploy N. The client bundle and the SSR loader payload agree.
2. Deploy N+1 ships. The loader now returns a payload with a different shape (e.g. `portfolios` moved, a count field removed).
3. The stale tab re-runs the route loader — via `router.invalidate()` from [[concepts/window-focus-refresh]], a client-side navigation, or a background refetch — and receives the **new** payload into the **old** component.
4. `portfolios.filter(...)` or `desk.cards.length` throws `TypeError: Cannot read properties of undefined`, and the route renders the error boundary instead of the page.

A reload fixes it, but the user should never have to see the boundary for a payload that is merely shaped differently.

## The Pattern: Normalize at the Boundary

Every value that crosses the loader → component boundary is coerced to its expected shape before it is read. Two rules:

- **Arrays** — `Array.isArray(value) ? value : []`. A missing or non-array collection renders as an empty collection, never as a crash.
- **Numbers and nullable scalars** — `Number(value ?? 0)` for counts, and an explicit `typeof value === 'number' ? value : null` for values whose `null` is meaningful (a median that has no data yet must stay `null`, not become `0`).

Normalization happens once, at the outermost point that owns the payload, so downstream components can keep their plain, non-defensive code.

## Component-Level Guards

Components that can be rendered from a payload that did not pass through a route normalizer (tests, story fixtures, a future caller) also guard locally.

### `HomePage` → `PortfoliosBlock`

```tsx
const llmPortfolios = (portfolios ?? []).filter((p) => !p.isSystem);
const safeBenchmark = benchmark ?? { todayPct: 0, weekPct: 0 };
```

The block still renders its `home-block-portfolios` card, the `SPInlineRow` benchmark trough (at a neutral `0%` / `0%`), and an empty table body when the payload arrives without `portfolios` or `benchmark`. See [[entities/web-app]] for the homepage block layout.

## Why Not Just Reload?

A reload is the correct response to a *chunk* failure (the code itself is gone — see [[concepts/chunk-reload-recovery]]), but it is the wrong response to a *shape* mismatch. The stale bundle is still perfectly executable; only one field is missing. Forcing a reload would discard the user's scroll position, in-flight form state, and any open inspection slot for a defect the component can absorb silently. Normalization degrades the page to an empty-but-valid state; the next natural navigation picks up the new bundle.

## Testing

- `apps/web/src/features/home/pages/HomePage.test.tsx` (`HomePage deploy-skew tolerance`) renders `HomePage` with `portfolios: undefined` and `benchmark: undefined` cast through `unknown as HomePageData`, and asserts `home-block-portfolios` is still in the document.

Tests deliberately cast through `unknown` so the type system cannot hide the very mismatch they exist to cover.

## Related

- [[concepts/chunk-reload-recovery]] — the module-level failure the same deploy skew causes, and its bounded reload path
- [[concepts/window-focus-refresh]] — `router.invalidate()` is one of the paths that re-runs a loader against a stale bundle
- [[entities/web-app]] — the homepage and its `PortfoliosBlock`
- [[entities/recipe-studio]] — the recipe studio and its loader-driven surfaces
- [[concepts/rendering-strategies]] — loader/hybrid-SSR data flow this guard sits inside
