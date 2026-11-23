import { Button } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useMutation } from '@tanstack/react-query';
import { useRouter } from '@tanstack/react-router';
import { useState } from 'react';
import { loginFn } from '~/routes/_authed';
import { signupFn } from '~/routes/signup';
import { resolveCurrentReturnPath } from '../redirect';
import { Auth } from './Auth';

type LoginVariables = { email: string; password: string; captchaToken?: string };
type AuthResult =
    | { error: true; message: string }
    | { user?: { id: string; email: string }; redirectUrl?: string }
    | undefined;

export function Login({ redirectPath }: { redirectPath?: string } = {}) {
    const router = useRouter();
    const posthog = usePostHog();
    const [captchaResetKey, setCaptchaResetKey] = useState(0);
    // Set when the auth card is reached by a redirect from a gated route
    // (`/auth?redirect=/recipes`); otherwise fall back to the live location.
    const authReturnPath = redirectPath ?? resolveCurrentReturnPath();

    const navigateAfterAuth = async () => {
        await router.invalidate();
        if (authReturnPath === '/') {
            router.navigate({ to: '/' });
        } else {
            router.navigate({ href: authReturnPath });
        }
    };

    const loginMutation = useMutation<AuthResult, Error, LoginVariables>({
        mutationFn: (variables) => loginFn({ data: variables }),
        onSuccess: async (data, variables) => {
            if (!data || !('error' in data && data.error)) {
                if (data && 'user' in data && data.user) {
                    posthog.identify(data.user.id, { email: data.user.email });
                }
                posthog.capture('user_logged_in', { email: variables.email });
                await navigateAfterAuth();
                return;
            }
            setCaptchaResetKey((k) => k + 1);
        },
        onError: () => {
            setCaptchaResetKey((k) => k + 1);
        },
    });

    const signupMutation = useMutation<AuthResult, Error, LoginVariables>({
        mutationFn: (variables: LoginVariables) =>
            signupFn({ data: { ...variables, redirectUrl: authReturnPath } }),
        onSuccess: async (data, variables) => {
            if (!data || ('error' in data && data.error)) {
                setCaptchaResetKey((k) => k + 1);
                return;
            }
            if ('user' in data && data.user) {
                posthog.identify(data.user.id, { email: data.user.email });
            }
            posthog.capture('user_signed_up', { email: variables.email });
            await navigateAfterAuth();
        },
        onError: () => {
            setCaptchaResetKey((k) => k + 1);
        },
    });

    return (
        <Auth
            actionText="Login"
            redirectPath={authReturnPath}
            status={loginMutation.status}
            captchaResetKey={captchaResetKey}
            onSubmit={(e) => {
                const formData = new FormData(e.target as HTMLFormElement);
                const captchaToken = formData.get('captchaToken');

                loginMutation.mutate({
                    email: formData.get('email') as string,
                    password: formData.get('password') as string,
                    captchaToken: typeof captchaToken === 'string' ? captchaToken : undefined,
                });
            }}
            afterSubmit={
                loginMutation.data && 'error' in loginMutation.data ? (
                    <>
                        <div className="text-red-400">{loginMutation.data.message}</div>
                        {loginMutation.data.message === 'Invalid login credentials' ? (
                            <div>
                                <Button
                                    variant="outline"
                                    colorScheme="info"
                                    onClick={(e) => {
                                        const form = (e.target as HTMLButtonElement).form;
                                        if (!form) return;
                                        const formData = new FormData(form);
                                        const captchaToken = formData.get('captchaToken');

                                        signupMutation.mutate({
                                            email: formData.get('email') as string,
                                            password: formData.get('password') as string,
                                            captchaToken:
                                                typeof captchaToken === 'string'
                                                    ? captchaToken
                                                    : undefined,
                                        });
                                    }}
                                >
                                    Sign up instead?
                                </Button>
                            </div>
                        ) : null}
                    </>
                ) : null
            }
        />
    );
}
