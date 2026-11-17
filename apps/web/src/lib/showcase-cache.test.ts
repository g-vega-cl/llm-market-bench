import { describe, expect, it } from 'vitest';
import {
    SHOWCASE_CACHE_MAX_AGE_SECONDS,
    SHOWCASE_PATH,
    withShowcaseCacheHeaders,
} from './showcase-cache';

function htmlResponse(status = 200, extraHeaders: Record<string, string> = {}): Response {
    return new Response('<html>demo</html>', {
        status,
        headers: { 'content-type': 'text/html; charset=utf-8', ...extraHeaders },
    });
}

describe('withShowcaseCacheHeaders', () => {
    it('marks a published showcase as shared-cacheable for 72h', () => {
        const res = withShowcaseCacheHeaders(SHOWCASE_PATH, htmlResponse(), true);

        expect(SHOWCASE_CACHE_MAX_AGE_SECONDS).toBe(72 * 60 * 60);
        expect(res.headers.get('cache-control')).toBe(
            'public, max-age=0, s-maxage=259200, must-revalidate',
        );
        expect(res.headers.get('netlify-cdn-cache-control')).toBe('public, s-maxage=259200');
        // Unrelated headers survive the rewrite.
        expect(res.headers.get('content-type')).toBe('text/html; charset=utf-8');
    });

    it('never caches the empty showcase state, so a fresh publish is visible immediately', () => {
        const res = withShowcaseCacheHeaders(SHOWCASE_PATH, htmlResponse(), false);

        expect(res.headers.get('cache-control')).toBe('no-store');
        expect(res.headers.get('netlify-cdn-cache-control')).toBeNull();
    });

    it('never caches a non-200 showcase response', () => {
        const res = withShowcaseCacheHeaders(SHOWCASE_PATH, htmlResponse(500), true);

        expect(res.headers.get('cache-control')).toBeNull();
        expect(res.headers.get('netlify-cdn-cache-control')).toBeNull();
    });

    it('leaves every other path untouched', () => {
        const original = htmlResponse();
        const res = withShowcaseCacheHeaders('/lab', original, true);

        expect(res).toBe(original);
        expect(res.headers.get('netlify-cdn-cache-control')).toBeNull();
    });
});
