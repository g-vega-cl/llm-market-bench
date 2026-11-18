import { createFileRoute } from '@tanstack/react-router';
import { Login } from '~/shared/auth';
import { sanitizeRedirectPath } from '~/shared/auth/redirect';

export const Route = createFileRoute('/login')({
    validateSearch: (search: Record<string, unknown>): { redirect?: string } => ({
        redirect:
            typeof search.redirect === 'string' ? sanitizeRedirectPath(search.redirect) : undefined,
    }),
    component: LoginComp,
});

function LoginComp() {
    const { redirect } = Route.useSearch();
    return <Login redirectPath={redirect} />;
}
