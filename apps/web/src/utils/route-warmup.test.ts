import {
    createMemoryHistory,
    createRootRoute,
    createRoute,
    createRouter,
} from '@tanstack/react-router';
import { describe, expect, it, vi } from 'vitest';
import {
    DYNAMIC_WARMUP_SAMPLE_PATHS,
    PRELOAD_WARMUP_ROUTES,
    warmRouteChunks,
} from './route-warmup';

describe('route-warmup', () => {
    it('includes /recipes-demo, /recipes, /profile, and dynamic routes while excluding /today and /logout', () => {
        expect(PRELOAD_WARMUP_ROUTES).toContain('/recipes-demo');
        expect(PRELOAD_WARMUP_ROUTES).toContain('/recipes');
        expect(PRELOAD_WARMUP_ROUTES).toContain('/profile');
        expect(Object.keys(DYNAMIC_WARMUP_SAMPLE_PATHS)).toContain('/portfolios/$portfolioId');
        expect(PRELOAD_WARMUP_ROUTES as readonly string[]).not.toContain('/today');
        expect(PRELOAD_WARMUP_ROUTES as readonly string[]).not.toContain('/logout');
    });

    it('warms allowlisted and dynamic route chunks without invoking loader or beforeLoad', async () => {
        const loaderSpy = vi.fn().mockResolvedValue({ ok: true });
        const beforeLoadSpy = vi.fn();
        const rootRoute = createRootRoute();

        const recipesDemoRoute = createRoute({
            getParentRoute: () => rootRoute,
            path: '/recipes-demo',
            beforeLoad: beforeLoadSpy,
            loader: loaderSpy,
        });

        const dynamicPortfolioRoute = createRoute({
            getParentRoute: () => rootRoute,
            path: '/portfolios/$portfolioId',
            beforeLoad: beforeLoadSpy,
            loader: loaderSpy,
        });

        const todayRedirectRoute = createRoute({
            getParentRoute: () => rootRoute,
            path: '/today',
        });

        const optedOutRoute = createRoute({
            getParentRoute: () => rootRoute,
            path: '/logout',
            preload: false,
        });

        const routeTree = rootRoute.addChildren([
            recipesDemoRoute,
            dynamicPortfolioRoute,
            todayRedirectRoute,
            optedOutRoute,
        ]);
        const router = createRouter({
            routeTree,
            history: createMemoryHistory({ initialEntries: ['/'] }),
        });

        const preloadSpy = vi.spyOn(router, 'preloadRoute');
        const loadRouteChunkSpy = vi.spyOn(router, 'loadRouteChunk').mockResolvedValue(undefined);

        await warmRouteChunks(router);

        const warmedIds = loadRouteChunkSpy.mock.calls.map(([route]) => route.id);
        expect(warmedIds).toContain('/recipes-demo');
        expect(warmedIds).toContain('/portfolios/$portfolioId');
        expect(warmedIds).not.toContain('/today');
        expect(warmedIds).not.toContain('/logout');
        expect(preloadSpy).not.toHaveBeenCalled();
        expect(loaderSpy).not.toHaveBeenCalled();
        expect(beforeLoadSpy).not.toHaveBeenCalled();
    });

    it('stops warming remaining routes when AbortSignal aborts before completion', async () => {
        const rootRoute = createRootRoute();
        const childA = createRoute({ getParentRoute: () => rootRoute, path: '/recipes-demo' });
        const childB = createRoute({ getParentRoute: () => rootRoute, path: '/recipes' });
        const router = createRouter({
            routeTree: rootRoute.addChildren([childA, childB]),
            history: createMemoryHistory({ initialEntries: ['/'] }),
        });

        const controller = new AbortController();
        const loadRouteChunkSpy = vi
            .spyOn(router, 'loadRouteChunk')
            .mockImplementation(async (route) => {
                if (route.id === '/recipes-demo') {
                    controller.abort();
                }
            });

        await warmRouteChunks(router, controller.signal);

        const warmedIds = loadRouteChunkSpy.mock.calls.map(([route]) => route.id);
        expect(warmedIds).toContain('/recipes-demo');
        expect(warmedIds).not.toContain('/recipes');
    });
});
