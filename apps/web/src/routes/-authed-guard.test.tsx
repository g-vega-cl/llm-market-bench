import { isRedirect } from '@tanstack/react-router';
import { describe, expect, it, vi } from 'vitest';
import { Route } from './_authed';

vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({
        auth: {
            getUser: vi.fn(),
        },
    }),
}));

type GuardContext = { user: { id: string; email: string } | null };

async function runGuard(context: GuardContext, pathname: string, searchStr = ''): Promise<unknown> {
    try {
        await (
            Route.options.beforeLoad as unknown as (args: {
                context: GuardContext;
                location: Record<string, unknown>;
            }) => Promise<void>
        )({
            context,
            location: {
                pathname,
                searchStr,
                search: {},
                href: `${pathname}${searchStr}`,
                hash: '',
                state: {},
            },
        });
        return null;
    } catch (err) {
        return err;
    }
}

describe('/_authed guard', () => {
    it('redirects an anonymous /recipes visitor to /login with the requested path', async () => {
        const thrown = await runGuard({ user: null }, '/recipes', '?recipeId=rec-1');

        expect(isRedirect(thrown)).toBe(true);
        const redirect = thrown as unknown as {
            status: number;
            options: { to: string; search: { redirect: string }; replace?: boolean };
        };
        expect(redirect.status).toBe(307);
        expect(redirect.options.to).toBe('/login');
        expect(redirect.options.search).toEqual({ redirect: '/recipes?recipeId=rec-1' });
        expect(redirect.options.replace).toBe(true);
    });

    it('sanitises the carried path so it cannot become an open redirect', async () => {
        const thrown = await runGuard({ user: null }, '//evil.com');

        expect(isRedirect(thrown)).toBe(true);
        expect(
            (thrown as unknown as { options: { search: { redirect: string } } }).options.search,
        ).toEqual({ redirect: '/' });
    });

    it('lets an authenticated user through without redirecting', async () => {
        const thrown = await runGuard({ user: { id: 'u1', email: 'u@example.com' } }, '/recipes');

        expect(thrown).toBeNull();
    });
});
