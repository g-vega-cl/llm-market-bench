import type { AnyRoute } from '@tanstack/react-router';
import type { FileRoutesByTo } from '~/routeTree.gen';

export const PRELOAD_WARMUP_ROUTES = [
    '/',
    '/portfolios',
    '/lab',
    '/recipes-demo',
    '/recipes',
    '/profile',
    '/leaderboard',
    '/companies',
    '/how-it-works',
    '/audits',
    '/autoresearch',
    '/autoresearch-backtest',
    '/daily-predictions',
    '/daily-predictions-backtest',
    '/ai-predictions',
    '/market-overview',
    '/reasoning',
    '/memories',
    '/concepts',
    '/cause-and-effect',
    '/generated-newsletters',
    '/earnings-audit',
    '/barometer-audit',
    '/renko',
    '/retired-agents',
    '/chat',
    '/login',
] as const satisfies readonly (keyof FileRoutesByTo)[];

type DynamicWarmupRouteKey = Extract<
    keyof FileRoutesByTo,
    | '/portfolios/$portfolioId'
    | '/companies/$ticker'
    | '/recipes/backtest/$jobId'
    | '/memories/chain/$memoryId'
>;

export const DYNAMIC_WARMUP_SAMPLE_PATHS: Record<DynamicWarmupRouteKey, string> = {
    '/portfolios/$portfolioId': '/portfolios/_',
    '/companies/$ticker': '/companies/_',
    '/recipes/backtest/$jobId': '/recipes/backtest/_',
    '/memories/chain/$memoryId': '/memories/chain/_',
};

export interface WarmupRouterLike {
    getMatchedRoutes: (pathname: string) => [readonly AnyRoute[], ...unknown[]];
    loadRouteChunk: (route: AnyRoute) => Promise<void> | undefined;
}

function isDataSaverEnabled(): boolean {
    if (typeof navigator === 'undefined') return false;
    const nav = navigator as Navigator & { connection?: { saveData?: boolean } };
    return nav.connection?.saveData === true;
}

function yieldToIdleFrame(signal?: AbortSignal): Promise<void> {
    if (typeof window === 'undefined' || signal?.aborted) {
        return Promise.resolve();
    }
    const win = window as Window & {
        requestIdleCallback?: (cb: () => void, options?: { timeout: number }) => number;
        cancelIdleCallback?: (id: number) => void;
    };
    return new Promise((resolve) => {
        let settled = false;
        let usingIdle = false;
        let handle = 0;

        const finish = () => {
            if (settled) return;
            settled = true;
            signal?.removeEventListener('abort', onAbort);
            resolve();
        };

        const onAbort = () => {
            if (usingIdle && typeof win.cancelIdleCallback === 'function') {
                win.cancelIdleCallback(handle);
            } else {
                window.clearTimeout(handle);
            }
            finish();
        };

        signal?.addEventListener('abort', onAbort, { once: true });

        if (typeof win.requestIdleCallback === 'function') {
            usingIdle = true;
            handle = win.requestIdleCallback(finish, { timeout: 500 });
        } else {
            handle = window.setTimeout(finish, 0);
        }
    });
}

async function warmSingleRoute(
    router: WarmupRouterLike,
    route: AnyRoute | undefined,
    seenRouteIds: Set<string>,
    signal?: AbortSignal,
): Promise<boolean> {
    if (!route || signal?.aborted || seenRouteIds.has(route.id)) {
        return false;
    }
    if (route.options?.preload === false) {
        return false;
    }
    seenRouteIds.add(route.id);
    try {
        await router.loadRouteChunk(route);
        return true;
    } catch {
        // Non-blocking background chunk warmup (never invokes route loaders)
        return false;
    }
}

async function warmMatchedPath(
    router: WarmupRouterLike,
    path: string,
    seenRouteIds: Set<string>,
    signal?: AbortSignal,
): Promise<void> {
    try {
        const [matchedRoutes] = router.getMatchedRoutes(path);
        for (const route of matchedRoutes) {
            if (signal?.aborted) return;
            const warmed = await warmSingleRoute(router, route, seenRouteIds, signal);
            if (warmed && !signal?.aborted) {
                await yieldToIdleFrame(signal);
            }
        }
    } catch {
        // Ignore match errors on unregistered test routes
    }
}

/**
 * Downloads and compiles allowlisted route JS chunks during idle frames without invoking route
 * `loader` or `beforeLoad` handlers, preventing unrequested background fetches on navigation.
 */
export async function warmRouteChunks(
    router: WarmupRouterLike,
    signal?: AbortSignal,
): Promise<void> {
    if (isDataSaverEnabled()) return;

    const seenRouteIds = new Set<string>();
    const paths: readonly string[] = [
        ...PRELOAD_WARMUP_ROUTES,
        ...Object.values(DYNAMIC_WARMUP_SAMPLE_PATHS),
    ];

    for (const path of paths) {
        if (signal?.aborted) return;
        await warmMatchedPath(router, path, seenRouteIds, signal);
    }
}
