import { createFileRoute, redirect } from '@tanstack/react-router';
import { sanitizePostAuthRedirect, sanitizeRedirectPath } from '~/shared/auth/redirect';

/**
 * Legacy auth entry point kept as a 307 redirect to `/login` so existing
 * `/auth?redirect=...` links and route guards keep working without duplicating
 * the sign-in page.
 */
export const Route = createFileRoute('/auth')({
    validateSearch: (search: Record<string, unknown>): { redirect?: string; error?: string } => ({
        redirect:
            typeof search.redirect === 'string' ? sanitizeRedirectPath(search.redirect) : undefined,
        error: typeof search.error === 'string' && search.error ? search.error : undefined,
    }),
    beforeLoad: ({ context, search }) => {
        if (context.user) {
            throw redirect({ href: sanitizePostAuthRedirect(search.redirect), replace: true });
        }
        throw redirect({
            to: '/login',
            search: {
                redirect: search.redirect,
                error: search.error,
            },
            replace: true,
        });
    },
});
