import { describe, expect, it } from 'vitest';
import { buildAuthRedirectSearch, buildOAuthCallbackUrl, sanitizeRedirectPath } from './redirect';

describe('auth redirect helpers', () => {
    it('allows clean internal relative paths and rejects external or protocol-relative URLs', () => {
        expect(sanitizeRedirectPath('/recipes')).toBe('/recipes');
        expect(sanitizeRedirectPath('/recipes/backtest/job-123?tab=trace')).toBe(
            '/recipes/backtest/job-123?tab=trace',
        );
        expect(sanitizeRedirectPath('https://evil.com/phish')).toBe('/');
        expect(sanitizeRedirectPath('//evil.com')).toBe('/');
        expect(sanitizeRedirectPath('/\\evil.com')).toBe('/');
        expect(sanitizeRedirectPath('/\t/evil.com')).toBe('/');
        expect(sanitizeRedirectPath('/\n/evil.com')).toBe('/');
        expect(sanitizeRedirectPath('')).toBe('/');
        expect(sanitizeRedirectPath(undefined)).toBe('/');
    });

    it('attaches a safe next param to the OAuth callback URL when on a gated route', () => {
        expect(buildOAuthCallbackUrl('https://benchify.app', '/recipes')).toBe(
            'https://benchify.app/auth/callback?next=%2Frecipes',
        );
        expect(buildOAuthCallbackUrl('https://benchify.app', '/login')).toBe(
            'https://benchify.app/auth/callback',
        );
        expect(buildOAuthCallbackUrl('https://benchify.app', '/')).toBe(
            'https://benchify.app/auth/callback',
        );
    });

    it('carries the requested gated path to /auth as a sanitized redirect param', () => {
        expect(buildAuthRedirectSearch('/recipes')).toEqual({ redirect: '/recipes' });
        expect(buildAuthRedirectSearch('/recipes', '?recipeId=rec-1')).toEqual({
            redirect: '/recipes?recipeId=rec-1',
        });
        expect(buildAuthRedirectSearch('//evil.com')).toEqual({ redirect: '/' });
    });

    it('treats /auth itself as an auth path, not a return target', () => {
        expect(buildOAuthCallbackUrl('https://benchify.app', '/auth')).toBe(
            'https://benchify.app/auth/callback',
        );
    });
});
