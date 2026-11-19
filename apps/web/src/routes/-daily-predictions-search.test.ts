import {
    createMemoryHistory,
    createRootRoute,
    createRoute,
    createRouter,
} from '@tanstack/react-router';
import { describe, expect, it } from 'vitest';
import { Route as DailyPredictionsRoute } from './daily-predictions/index';

/**
 * Asserts the exact invariant the router's SSR loader depends on.
 *
 * `loadServerRoute` (`@tanstack/router-core` `dist/esm/load-server.js`) rebuilds
 * the request URL with `buildLocation({ _includeValidateSearch: true })` and
 * throws a 307 whenever the rebuild differs from the requested `publicHref`. A
 * `validateSearch` that maps a URL param to `undefined` therefore rewrites the
 * URL on every SSR request, and a rewritten target that carries no query at all
 * is what produced the `/daily-predictions?ticker=SPY` redirect loop.
 *
 * The comparisons run through a real router (memory history + the route's own
 * validator + the same `buildLocation` call) rather than a hand-rolled copy of
 * the router's stringifier, so a change in search serialisation is caught too.
 */
type ValidateSearch = (search: Record<string, unknown>) => { ticker?: 'SPY' | 'TLT' | 'PICKS' };

const validateSearch = DailyPredictionsRoute.options.validateSearch as unknown as ValidateSearch;

function hrefsFor(entry: string): { requested: string; canonical: string } {
    const rootRoute = createRootRoute();
    const dailyPredictionsRoute = createRoute({
        getParentRoute: () => rootRoute,
        path: '/daily-predictions/',
        validateSearch,
    });
    const router = createRouter({
        routeTree: rootRoute.addChildren([dailyPredictionsRoute]),
        history: createMemoryHistory({ initialEntries: [entry] }),
    });

    router.updateLatestLocation();
    const requested = router.latestLocation;
    const canonical = router.buildLocation({
        to: requested.pathname,
        search: true,
        params: true,
        hash: true,
        state: true,
        _includeValidateSearch: true,
    } as never);

    return { requested: requested.publicHref, canonical: canonical.publicHref };
}

describe('/daily-predictions validateSearch canonicality', () => {
    it.each([
        '/daily-predictions',
        '/daily-predictions?ticker=SPY',
        '/daily-predictions?ticker=TLT',
        '/daily-predictions?ticker=PICKS',
        '/daily-predictions?ticker=SPY&utm_source=newsletter',
    ])('leaves %s untouched, so SSR issues no redirect', (entry) => {
        const { requested, canonical } = hrefsFor(entry);

        expect(canonical).toBe(requested);
    });

    it.each([
        ['/daily-predictions?ticker=spy', '/daily-predictions?ticker=SPY'],
        ['/daily-predictions?ticker=tlt', '/daily-predictions?ticker=TLT'],
        ['/daily-predictions?ticker=picks', '/daily-predictions?ticker=PICKS'],
        ['/daily-predictions?ticker=GOOG', '/daily-predictions?ticker=SPY'],
        ['/daily-predictions?ticker=', '/daily-predictions?ticker=SPY'],
    ])('normalises %s to %s in one hop that still carries a query', (entry, expected) => {
        const { requested, canonical } = hrefsFor(entry);

        expect(canonical).toBe(expected);
        // A query-less target is what the edge re-appended, so a normalising
        // redirect must always keep a parameter in the URL.
        expect(canonical).toContain('?ticker=');
        expect(canonical).not.toBe(requested);
    });
});
