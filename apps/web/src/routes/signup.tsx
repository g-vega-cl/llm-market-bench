import { usePostHog } from '@posthog/react';
import { useMutation } from '@tanstack/react-query';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { Auth } from '~/shared/auth';
import { sanitizeRedirectPath } from '~/shared/auth/redirect';

type SignupVariables = { email: string; password: string; redirectUrl?: string };
type AuthResult =
    | { error: true; message: string }
    | { user?: { id: string; email: string }; redirectUrl?: string }
    | undefined;

export const signupFn = createServerFn({ method: 'POST' })
    .validator((d: SignupVariables) => d)
    .handler(async ({ data }) => {
        const authClient = getAuthServerClient();
        const { data: authData, error } = await authClient.auth.signUp({
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
            user: authData.user
                ? {
                      id: authData.user.id,
                      email: authData.user.email ?? data.email,
                  }
                : undefined,
            redirectUrl: sanitizeRedirectPath(data.redirectUrl),
        };
    });

function SignupRouteComponent() {
    const { next } = Route.useSearch();
    return <SignupComp redirectTo={next} />;
}

export const Route = createFileRoute('/signup')({
    validateSearch: (search: Record<string, unknown>) => ({
        next: sanitizeRedirectPath(search.next),
    }),
    component: SignupRouteComponent,
});

export function SignupComp({ redirectTo }: { redirectTo?: string } = {}) {
    const router = useRouter();
    const posthog = usePostHog();
    const next = sanitizeRedirectPath(redirectTo);
    const signupMutation = useMutation<AuthResult, Error, SignupVariables>({
        mutationFn: (data: SignupVariables) => signupFn({ data }),
        onSuccess: async (data, variables) => {
            if (!data || !('error' in data && data.error)) {
                if (data && 'user' in data && data.user) {
                    posthog.identify(data.user.id, { email: data.user.email });
                }
                posthog.capture('user_signed_up', { email: variables.email });
                await router.invalidate();
                const redirectHref = sanitizeRedirectPath(
                    (data && 'redirectUrl' in data && data.redirectUrl) || next,
                );
                router.navigate({ href: redirectHref });
            }
        },
    });

    return (
        <Auth
            actionText="Sign Up"
            status={signupMutation.status}
            onSubmit={(e) => {
                const formData = new FormData(e.target as HTMLFormElement);

                signupMutation.mutate({
                    email: formData.get('email') as string,
                    password: formData.get('password') as string,
                    redirectUrl: next,
                });
            }}
            afterSubmit={
                signupMutation.data && 'error' in signupMutation.data ? (
                    <div className="text-red-400">{signupMutation.data.message}</div>
                ) : null
            }
        />
    );
}
