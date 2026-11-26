import { isRedirect } from '@tanstack/react-router';
import { describe, expect, it, vi } from 'vitest';
import { Route } from './llm-logs';

vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({
        auth: {
            getUser: vi.fn(),
        },
    }),
}));

type GuardContext = { user: { id: string; email: string } | null };

async function runGuard(context: GuardContext): Promise<unknown> {
    try {
        await (
            Route.options.beforeLoad as unknown as (args: {
                context: GuardContext;
                location: Record<string, unknown>;
            }) => Promise<void>
        )({
            context,
            location: {
                pathname: '/llm-logs',
                searchStr: '',
                search: {},
                href: '/llm-logs',
                hash: '',
                state: {},
            },
        });
        return null;
    } catch (err) {
        return err;
    }
}

describe('/llm-logs route guard', () => {
    it('redirects unauthenticated visitors to /login with /llm-logs return path', async () => {
        const thrown = await runGuard({ user: null });
        expect(isRedirect(thrown)).toBe(true);
        const redirectObj = thrown as unknown as {
            status: number;
            options: { to: string; search: { redirect: string } };
        };
        expect(redirectObj.status).toBe(307);
        expect(redirectObj.options.to).toBe('/login');
        expect(redirectObj.options.search).toEqual({ redirect: '/llm-logs' });
    });

    it('allows authenticated users through beforeLoad (component & server enforce email)', async () => {
        const thrown = await runGuard({ user: { id: 'u1', email: 'g.vega.cl@gmail.com' } });
        expect(thrown).toBeNull();
    });
});
