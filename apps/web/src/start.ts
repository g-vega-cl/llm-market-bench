import { createCsrfMiddleware, createMiddleware, createStart } from '@tanstack/react-start';
import { SHOWCASE_PATH, withShowcaseCacheHeaders } from './lib/showcase-cache';
import { getPostHogClient } from './utils/posthog-server';

const posthogExceptionAutocapture = createMiddleware().server(async ({ next }) => {
    getPostHogClient();
    return await next();
});

/**
 * Let the public showcase be served from the shared CDN cache instead of running
 * SSR (and a ~1 MB PostgREST read) for every visitor.
 *
 * The pin probe only runs when the cache misses, and it fails closed to
 * `no-store`, so the empty state is never frozen behind a 72-hour entry.
 */
const showcaseDocumentCache = createMiddleware().server(async ({ next, pathname }) => {
    const result = await next();
    if (pathname !== SHOWCASE_PATH) return result;

    let hasPin = false;
    try {
        // Imported lazily so the archive-DB and auth server modules never reach
        // the client bundle.
        const { hasPublishedShowcase } = await import('./features/recipes/api/recipes-quota-api');
        hasPin = await hasPublishedShowcase();
    } catch (error) {
        console.error('[recipes-demo] showcase cache probe failed; not caching', error);
    }

    return { ...result, response: withShowcaseCacheHeaders(pathname, result.response, hasPin) };
});

export const startInstance = createStart(() => ({
    requestMiddleware: [
        createCsrfMiddleware({ filter: ({ handlerType }) => handlerType === 'serverFn' }),
        posthogExceptionAutocapture,
        showcaseDocumentCache,
    ],
}));
