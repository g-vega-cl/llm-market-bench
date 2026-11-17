/**
 * Cache policy for the public read-only showcase (`/recipes-demo`).
 *
 * The page only changes when someone publishes a pin, so it is served from the
 * shared CDN cache for 72 hours instead of hitting the SSR function and reading
 * a ~1 MB `result_json` on every visit. Browsers are told to revalidate
 * (`max-age=0`), so a client never holds a three-day-old page.
 *
 * Deliberately simple: no purge API and no credentials. A re-deploy (or a manual
 * CDN cache clear) is the escape hatch when a publish must be visible at once.
 */

export const SHOWCASE_PATH = '/recipes-demo';
export const SHOWCASE_CACHE_MAX_AGE_SECONDS = 72 * 60 * 60;

const SHARED_CACHE_CONTROL = `public, max-age=0, s-maxage=${SHOWCASE_CACHE_MAX_AGE_SECONDS}, must-revalidate`;
const CDN_CACHE_CONTROL = `public, s-maxage=${SHOWCASE_CACHE_MAX_AGE_SECONDS}`;

/**
 * Apply the showcase cache policy to a document response.
 *
 * Fails closed on both axes: only a `200` gets cached, and the empty state
 * (`hasPin === false`) is `no-store` so a fresh publish is visible immediately
 * rather than sitting behind a 72-hour cache entry.
 */
export function withShowcaseCacheHeaders(
    pathname: string,
    response: Response,
    hasPin: boolean,
): Response {
    if (pathname !== SHOWCASE_PATH || response.status !== 200) return response;

    const headers = new Headers(response.headers);
    if (hasPin) {
        headers.set('cache-control', SHARED_CACHE_CONTROL);
        headers.set('netlify-cdn-cache-control', CDN_CACHE_CONTROL);
    } else {
        headers.set('cache-control', 'no-store');
        headers.delete('netlify-cdn-cache-control');
    }

    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
    });
}
