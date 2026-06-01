import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { getSupabaseServerClient } from '~/lib/supabase';
import { Login } from '~/shared/auth';

export const loginFn = createServerFn({ method: 'POST' })
    .inputValidator((d: { email: string; password: string }) => d)
    .handler(async ({ data }) => {
        const supabase = getSupabaseServerClient();
        const { error } = await supabase.auth.signInWithPassword({
            email: data.email,
            password: data.password,
        });

        if (error) {
            return {
                error: true,
                message: error.message,
            };
        }
    });

/**
 * Server-side auth check for protected routes. Moved here (out of the root
 * route) so public pages like the homepage don't pay any Supabase auth cost
 * on first paint.
 */
const requireAuth = createServerFn({ method: 'GET' }).handler(async () => {
    const supabase = getSupabaseServerClient();
    const { data } = await supabase.auth.getUser();
    if (!data.user?.email) {
        throw new Error('Not authenticated');
    }
    return { email: data.user.email };
});

export const Route = createFileRoute('/_authed')({
    beforeLoad: async () => {
        // The homepage and other public routes opt out of this check by not
        // being under /_authed. Only protected routes pay the Supabase call.
        return await requireAuth();
    },
    errorComponent: ({ error }) => {
        if (error.message === 'Not authenticated') {
            return <Login />;
        }

        throw error;
    },
});
