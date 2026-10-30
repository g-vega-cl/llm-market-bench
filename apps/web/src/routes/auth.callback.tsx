import { createFileRoute, redirect } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';

const exchangeCodeFn = createServerFn({ method: 'GET' })
    .inputValidator((d: { code: string }) => d)
    .handler(async ({ data }) => {
        const authClient = getAuthServerClient();
        const { error } = await authClient.auth.exchangeCodeForSession(data.code);
        if (error) {
            console.error('Error exchanging code for session:', error.message);
        }
    });

export const Route = createFileRoute('/auth/callback')({
    validateSearch: (search: Record<string, unknown>) => {
        return {
            code: search.code as string | undefined,
        };
    },
    loaderDeps: ({ search: { code } }) => ({ code }),
    loader: async ({ deps: { code } }) => {
        if (code) {
            await exchangeCodeFn({ data: { code } });
        }
        throw redirect({ to: '/' });
    },
});
