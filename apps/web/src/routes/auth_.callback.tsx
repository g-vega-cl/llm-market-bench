import { createFileRoute, redirect } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { sanitizePostAuthRedirect } from '~/shared/auth/redirect';

export const exchangeCodeFn = createServerFn({ method: 'GET' })
    .validator((d: { code: string }) => d)
    .handler(async ({ data }): Promise<{ errorCode?: string }> => {
        try {
            const authClient = getAuthServerClient();
            const { error } = await authClient.auth.exchangeCodeForSession(data.code);
            if (error) {
                console.error('Error exchanging code for session:', error.message);
                return { errorCode: 'exchange_failed' };
            }
            return {};
        } catch (error) {
            console.error('Unexpected error exchanging code for session:', error);
            return { errorCode: 'exchange_failed' };
        }
    });

export const Route = createFileRoute('/auth_/callback')({
    preload: false,
    validateSearch: (search: Record<string, unknown>) => {
        return {
            code: typeof search.code === 'string' ? search.code : undefined,
            next: sanitizePostAuthRedirect(search.next),
            error: typeof search.error === 'string' ? search.error : undefined,
        };
    },
    loaderDeps: ({ search: { code, next, error } }) => ({
        code,
        next,
        error,
    }),
    loader: async ({ deps: { code, next, error } }) => {
        const safeNext = sanitizePostAuthRedirect(next);
        if (error) {
            throw redirect({
                to: '/login',
                search: {
                    redirect: safeNext !== '/' ? safeNext : undefined,
                    error: error === 'access_denied' ? 'access_denied' : 'oauth_failed',
                },
                replace: true,
            });
        }
        if (code) {
            const result = await exchangeCodeFn({ data: { code } });
            if (result?.errorCode) {
                throw redirect({
                    to: '/login',
                    search: {
                        redirect: safeNext !== '/' ? safeNext : undefined,
                        error: result.errorCode,
                    },
                    replace: true,
                });
            }
            throw redirect({ href: safeNext });
        }
        throw redirect({
            to: '/login',
            search: {
                redirect: safeNext !== '/' ? safeNext : undefined,
            },
            replace: true,
        });
    },
});
