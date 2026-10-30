import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { Login } from '~/shared/auth';

export const loginFn = createServerFn({ method: 'POST' })
    .inputValidator((d: { email: string; password: string }) => d)
    .handler(async ({ data }) => {
        const authClient = getAuthServerClient();
        const { data: authData, error } = await authClient.auth.signInWithPassword({
            email: data.email,
            password: data.password,
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
    beforeLoad: ({ context }) => {
        if (!context.user) {
            throw new Error('Not authenticated');
        }
    },
    errorComponent: ({ error }) => {
        if (error.message === 'Not authenticated') {
            return <Login />;
        }

        throw error;
    },
});
