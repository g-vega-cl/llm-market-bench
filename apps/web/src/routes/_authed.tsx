import { createFileRoute, redirect } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { Login } from '~/shared/auth';
import { buildAuthRedirectSearch } from '~/shared/auth/redirect';

export const loginFn = createServerFn({ method: 'POST' })
    .validator((d: { email: string; password: string; captchaToken?: string }) => d)
    .handler(async ({ data }) => {
        const authClient = getAuthServerClient();
        const captchaToken =
            typeof data.captchaToken === 'string' && data.captchaToken.trim()
                ? data.captchaToken.trim()
                : undefined;
        const { data: authData, error } = await authClient.auth.signInWithPassword({
            email: data.email,
            password: data.password,
            ...(captchaToken ? { options: { captchaToken } } : {}),
        });

        if (error) {
            return {
                error: true,
                message: error.message,
            };
        }

        return {
            user: {
                id: authData.user.id,
                email: authData.user.email ?? data.email,
            },
        };
    });

export const Route = createFileRoute('/_authed')({
    beforeLoad: ({ context, location }) => {
        if (!context.user) {
            // Redirect rather than throw: a 307 to /auth lets SSR answer with a
            // real navigation (and a 200 auth card) instead of a 500 error page,
            // and carries the path the visitor asked for so the card can show
            // the right context — the Recipe Studio beta panel for /recipes.
            throw redirect({
                to: '/auth',
                search: buildAuthRedirectSearch(location.pathname, location.searchStr),
                replace: true,
            });
        }
    },
    errorComponent: ({ error }) => {
        if (error instanceof Error && error.message === 'Not authenticated') {
            return <Login />;
        }

        throw error;
    },
});
