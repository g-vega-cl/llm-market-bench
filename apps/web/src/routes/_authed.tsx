import { createFileRoute, redirect } from '@tanstack/react-router';
import { Auth } from '~/shared/auth';
import { buildAuthRedirectSearch } from '~/shared/auth/redirect';

export const Route = createFileRoute('/_authed')({
    beforeLoad: ({ context, location }) => {
        if (!context.user) {
            // Redirect rather than throw: a 307 to /login lets SSR answer with a
            // real navigation (and a 200 auth card) instead of a 500 error page,
            // and carries the path the visitor asked for so the card can show
            // the right context — the Recipe Studio beta panel for /recipes.
            throw redirect({
                to: '/login',
                search: buildAuthRedirectSearch(location.pathname, location.searchStr),
                replace: true,
            });
        }
    },
    errorComponent: ({ error }) => {
        if (error instanceof Error && error.message === 'Not authenticated') {
            return <Auth />;
        }

        throw error;
    },
});
