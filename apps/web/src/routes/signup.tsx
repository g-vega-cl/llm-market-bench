import { usePostHog } from '@posthog/react';
import { useMutation } from '@tanstack/react-query';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { useState } from 'react';
import { getAuthServerClient } from '~/lib/auth';
import { Auth } from '~/shared/auth';
import { sanitizeRedirectPath } from '~/shared/auth/redirect';

type SignupVariables = {
    email: string;
    password: string;
    redirectUrl?: string;
    captchaToken?: string;
};
type AuthResult =
    | { error: true; message: string }
    | { user?: { id: string; email: string }; redirectUrl?: string }
    | undefined;

export const signupFn = createServerFn({ method: 'POST' })
    .validator((d: SignupVariables) => d)
    .handler(async ({ data }) => {
        const authClient = getAuthServerClient();
        const captchaToken =
            typeof data.captchaToken === 'string' && data.captchaToken.trim()
                ? data.captchaToken.trim()
                : undefined;
        const { data: authData, error } = await authClient.auth.signUp({
            email: data.email,
            password: data.password,
            ...(captchaToken ? { options: { captchaToken } } : {}),
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
    const [captchaResetKey, setCaptchaResetKey] = useState(0);
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
                return;
            }
            setCaptchaResetKey((k) => k + 1);
        },
        onError: () => {
            setCaptchaResetKey((k) => k + 1);
        },
    });

    return (
        <Auth
            actionText="Sign Up"
            status={signupMutation.status}
            captchaResetKey={captchaResetKey}
            onSubmit={(e) => {
                const formData = new FormData(e.target as HTMLFormElement);
                const captchaToken = formData.get('captchaToken');

                signupMutation.mutate({
                    email: formData.get('email') as string,
                    password: formData.get('password') as string,
                    redirectUrl: next,
                    captchaToken: typeof captchaToken === 'string' ? captchaToken : undefined,
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
