import { usePostHog } from '@posthog/react';
import { useMutation } from '@tanstack/react-query';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { getSupabaseServerClient } from '~/lib/supabase';
import { Auth } from '~/shared/auth';

type SignupVariables = { email: string; password: string; redirectUrl?: string };
type AuthResult =
    | { error: true; message: string }
    | { user?: { id: string; email: string }; redirectUrl?: string }
    | undefined;

export const signupFn = createServerFn({ method: 'POST' })
    .inputValidator((d: SignupVariables) => d)
    .handler(async ({ data }) => {
        const supabase = getSupabaseServerClient();
        const { data: authData, error } = await supabase.auth.signUp({
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
            redirectUrl: data.redirectUrl || '/',
        };
    });

export const Route = createFileRoute('/signup')({
    component: SignupComp,
});

export function SignupComp() {
    const router = useRouter();
    const posthog = usePostHog();
    const signupMutation = useMutation<AuthResult, Error, SignupVariables>({
        mutationFn: (data: SignupVariables) => signupFn({ data }),
        onSuccess: async (data, variables) => {
            if (!data || !('error' in data && data.error)) {
                if (data && 'user' in data && data.user) {
                    posthog.identify(data.user.id, { email: data.user.email });
                }
                posthog.capture('user_signed_up', { email: variables.email });
                await router.invalidate();
                const redirectHref = (data && 'redirectUrl' in data && data.redirectUrl) || '/';
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
