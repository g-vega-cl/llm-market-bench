import { createFileRoute, redirect } from '@tanstack/react-router';
import { seo } from '~/lib/seo';
import { Auth } from '~/shared/auth';
import { sanitizePostAuthRedirect, sanitizeRedirectPath } from '~/shared/auth/redirect';

/**
 * Dedicated `/signup` page so new visitors land on an explicit account-creation
 * view rather than being bounced straight to "Sign in to Benchify".
 */
export const Route = createFileRoute('/signup')({
    validateSearch: (
        search: Record<string, unknown>,
    ): { next?: string; redirect?: string; error?: string } => ({
        next: typeof search.next === 'string' ? sanitizeRedirectPath(search.next) : undefined,
        redirect:
            typeof search.redirect === 'string' ? sanitizeRedirectPath(search.redirect) : undefined,
        error: typeof search.error === 'string' && search.error ? search.error : undefined,
    }),
    beforeLoad: ({ context, search }) => {
        const target = search.redirect ?? search.next;
        if (context.user) {
            throw redirect({ href: sanitizePostAuthRedirect(target), replace: true });
        }
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Create account | Benchify',
                description:
                    'Create a free Benchify account with Google to build trading bots, run paper backtests, and track live results.',
            }),
        ],
    }),
    component: SignupRouteComponent,
});

export function SignupRouteComponent() {
    const { next, redirect: redirectParam, error } = Route.useSearch();
    const redirectPath = redirectParam ?? next;
    return <Auth mode="signup" redirectPath={redirectPath} errorCode={error} />;
}
