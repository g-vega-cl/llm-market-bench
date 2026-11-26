import { isRedirect } from '@tanstack/react-router';
import { describe, expect, it } from 'vitest';
import { Route } from './chat';

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

describe('/chat guard', () => {
    it('redirects an anonymous visitor to /login with the requested path', async () => {
        const thrown = await runGuard({ user: null }, '/chat', '?ticker=NVDA');

        expect(isRedirect(thrown)).toBe(true);
        const redirect = thrown as unknown as {
            status: number;
            options: { to: string; search: { redirect: string }; replace?: boolean };
        };
        expect(redirect.status).toBe(307);
        expect(redirect.options.to).toBe('/login');
        expect(redirect.options.search).toEqual({ redirect: '/chat?ticker=NVDA' });
        expect(redirect.options.replace).toBe(true);
    });

    it('lets an authenticated user through without redirecting', async () => {
        const thrown = await runGuard({ user: { id: 'u1', email: 'u@example.com' } }, '/chat');
        expect(thrown).toBeNull();
    });
});
