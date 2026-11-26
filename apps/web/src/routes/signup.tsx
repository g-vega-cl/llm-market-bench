import { createFileRoute, redirect } from '@tanstack/react-router';
import { sanitizePostAuthRedirect, sanitizeRedirectPath } from '~/shared/auth/redirect';

/**
 * Legacy signup entry point kept as a 307 redirect to `/login`, normalizing
 * `?next=` into `?redirect=`.
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
        throw redirect({
            to: '/login',
            search: {
                redirect: target,
                error: search.error,
            },
            replace: true,
        });
    },
});
