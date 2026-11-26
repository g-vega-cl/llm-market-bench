import { createFileRoute, redirect } from '@tanstack/react-router';
import { Auth } from '~/shared/auth';
import { sanitizePostAuthRedirect, sanitizeRedirectPath } from '~/shared/auth/redirect';

export const Route = createFileRoute('/login')({
    validateSearch: (search: Record<string, unknown>): { redirect?: string; error?: string } => ({
        redirect:
            typeof search.redirect === 'string' ? sanitizeRedirectPath(search.redirect) : undefined,
        error: typeof search.error === 'string' && search.error ? search.error : undefined,
    }),
    beforeLoad: ({ context, search }) => {
        if (context.user) {
            throw redirect({ href: sanitizePostAuthRedirect(search.redirect), replace: true });
        }
    },
    component: LoginRouteComponent,
});

function LoginRouteComponent() {
    const { redirect: redirectPath, error } = Route.useSearch();
    return <Auth redirectPath={redirectPath} errorCode={error} />;
}
