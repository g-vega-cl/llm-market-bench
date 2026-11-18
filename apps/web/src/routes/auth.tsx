import { createFileRoute } from '@tanstack/react-router';
import { Login } from '~/shared/auth';
import { sanitizeRedirectPath } from '~/shared/auth/redirect';

/**
 * Auth entry point for gated routes.
 *
 * `/_authed` sends anonymous visitors here with `?redirect=<path they asked
 * for>`, so the card can show the right context (the Recipe Studio beta panel
 * for `/recipes`) and return them afterwards.
 */
export const Route = createFileRoute('/auth')({
    validateSearch: (search: Record<string, unknown>): { redirect?: string } => ({
        redirect:
            typeof search.redirect === 'string' ? sanitizeRedirectPath(search.redirect) : undefined,
    }),
    component: AuthRouteComponent,
});

function AuthRouteComponent() {
    const { redirect } = Route.useSearch();
    return <Login redirectPath={redirect} />;
}
