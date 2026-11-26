import { createRouter, isRedirect } from '@tanstack/react-router';
import { describe, expect, it, vi } from 'vitest';
import { routeTree } from '~/routeTree.gen';
import { Route as AuthRoute } from './auth';
import { Route as AuthCallbackRoute } from './auth_.callback';
import { Route as LoginRoute } from './login';
import { Route as SignupRoute } from './signup';

const mockExchangeCodeForSession = vi.hoisted(() => vi.fn());
const mockGetAuthServerClient = vi.hoisted(() =>
    vi.fn(() => ({
        auth: {
            exchangeCodeForSession: mockExchangeCodeForSession,
        },
    })),
);

vi.mock('@tanstack/react-start', () => ({
    createServerFn: () => {
        const chain = {
            validator: () => chain,
            handler:
                (fn: (ctx: { data?: { code: string } }) => Promise<unknown>) =>
                (arg: { data?: { code: string } } = {}) =>
                    fn(arg),
        };
        return chain;
    },
}));

vi.mock('~/lib/auth', () => ({
    getAuthServerClient: mockGetAuthServerClient,
}));

type GuardContext = { user: { id: string; email: string } | null };

async function runBeforeLoad(
    route: { options: { beforeLoad?: unknown } },
    context: GuardContext,
    search: Record<string, unknown> = {},
): Promise<unknown> {
    try {
        await (
            route.options.beforeLoad as (args: {
                context: GuardContext;
                search: Record<string, unknown>;
            }) => Promise<void>
        )({
            context,
            search,
        });
        return null;
    } catch (err) {
        return err;
    }
}

describe('auth route guards & callback isolation', () => {
    it('does not nest /auth/callback under /auth in routeTree', () => {
        const router = createRouter({ routeTree });
        const callbackRoute = router.routesById['/auth_/callback'] as
            | { id?: string; parentRoute?: { id?: string } }
            | undefined;
        const authRoute = router.routesById['/auth'] as { children?: unknown } | undefined;

        expect(callbackRoute?.id).toBe('/auth_/callback');
        expect(callbackRoute?.parentRoute?.id).toBe('__root__');
        expect(authRoute?.children).toBeUndefined();
    });

    it('redirects anonymous /auth and /signup visitors to /login with unified ?redirect= and ?error=', async () => {
        const authThrown = await runBeforeLoad(
            AuthRoute,
            { user: null },
            { redirect: '/recipes', error: 'access_denied' },
        );
        expect(isRedirect(authThrown)).toBe(true);
        expect((authThrown as { options: Record<string, unknown> }).options).toMatchObject({
            to: '/login',
            search: { redirect: '/recipes', error: 'access_denied' },
            replace: true,
        });

        const signupThrown = await runBeforeLoad(SignupRoute, { user: null }, { next: '/chat' });
        expect(isRedirect(signupThrown)).toBe(true);
        expect((signupThrown as { options: Record<string, unknown> }).options).toMatchObject({
            to: '/login',
            search: { redirect: '/chat', error: undefined },
            replace: true,
        });
    });

    it('redirects signed-in visitors away from /login, /auth, and /signup without self-redirect loops', async () => {
        const user = { id: 'u1', email: 'u@example.com' };

        for (const [route, search] of [
            [LoginRoute, { redirect: '/login' }],
            [AuthRoute, { redirect: '/auth?redirect=/recipes' }],
            [SignupRoute, { next: '/signup' }],
        ] as const) {
            const thrown = await runBeforeLoad(route, { user }, search);
            expect(isRedirect(thrown)).toBe(true);
            expect((thrown as { options: { href: string } }).options.href).toBe('/');
        }

        const safeTarget = await runBeforeLoad(LoginRoute, { user }, { redirect: '/recipes' });
        expect(isRedirect(safeTarget)).toBe(true);
        expect((safeTarget as { options: { href: string } }).options.href).toBe('/recipes');
    });

    it('redirects OAuth callback errors and code-exchange exceptions back to /login with bounded error codes', async () => {
        const loader = AuthCallbackRoute.options.loader as unknown as (args: {
            deps: { code?: string; next?: string; error?: string };
        }) => Promise<unknown>;

        let thrown: unknown;
        try {
            await loader({ deps: { next: '/recipes', error: 'access_denied' } });
        } catch (err) {
            thrown = err;
        }
        expect(isRedirect(thrown)).toBe(true);
        expect(
            (thrown as { options: { to: string; search: Record<string, unknown> } }).options,
        ).toMatchObject({
            to: '/login',
            search: { redirect: '/recipes', error: 'access_denied' },
        });

        mockGetAuthServerClient.mockImplementationOnce(() => {
            throw new Error('Missing SUPABASE_AUTH_URL');
        });
        let exchangeThrown: unknown;
        try {
            await loader({ deps: { code: 'abc', next: '/recipes' } });
        } catch (err) {
            exchangeThrown = err;
        }
        expect(isRedirect(exchangeThrown)).toBe(true);
        expect(
            (exchangeThrown as { options: { to: string; search: Record<string, unknown> } })
                .options,
        ).toMatchObject({
            to: '/login',
            search: { redirect: '/recipes', error: 'exchange_failed' },
        });

        let emptyThrown: unknown;
        try {
            await loader({ deps: { next: '/recipes' } });
        } catch (err) {
            emptyThrown = err;
        }
        expect(isRedirect(emptyThrown)).toBe(true);
        expect(
            (emptyThrown as { options: { to: string; search: Record<string, unknown> } }).options,
        ).toMatchObject({
            to: '/login',
            search: { redirect: '/recipes' },
            replace: true,
        });
    });
});
