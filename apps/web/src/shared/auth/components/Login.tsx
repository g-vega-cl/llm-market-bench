import { Button } from '@llm-market-bench/ui-design-system';
import { useMutation } from '@tanstack/react-query';
import { useRouter } from '@tanstack/react-router';
import { useAnalytics } from '~/lib/posthog-client';
import { loginFn } from '~/routes/_authed';
import { signupFn } from '~/routes/signup';
import { Auth } from './Auth';

type LoginVariables = { email: string; password: string };
type AuthResult = { error: true; message: string } | undefined;

export function Login() {
    const router = useRouter();
    const posthog = useAnalytics();

    const loginMutation = useMutation<AuthResult, Error, LoginVariables>({
        mutationFn: (variables) => loginFn({ data: variables }),
        onSuccess: async (data, variables) => {
            if (!data?.error) {
                posthog.identify(variables.email);
                posthog.capture('user_logged_in', { email: variables.email });
                await router.invalidate();
                router.navigate({ to: '/' });
                return;
            }
        },
    });

    const signupMutation = useMutation({
        mutationFn: (variables: LoginVariables) => signupFn({ data: variables }),
    });

    return (
        <Auth
            actionText="Login"
            status={loginMutation.status}
            onSubmit={(e) => {
                const formData = new FormData(e.target as HTMLFormElement);

                loginMutation.mutate({
                    email: formData.get('email') as string,
                    password: formData.get('password') as string,
                });
            }}
            afterSubmit={
                loginMutation.data ? (
                    <>
                        <div className="text-red-400">
                            {(loginMutation.data as AuthResult)?.message}
                        </div>
                        {loginMutation.data?.error &&
                        (loginMutation.data as AuthResult)?.message ===
                            'Invalid login credentials' ? (
                            <div>
                                <Button
                                    variant="ghost"
                                    colorScheme="info"
                                    className="text-blue-500"
                                    onClick={(e) => {
                                        const form = (e.target as HTMLButtonElement).form;
                                        if (!form) return;
                                        const formData = new FormData(form);

                                        signupMutation.mutate({
                                            email: formData.get('email') as string,
                                            password: formData.get('password') as string,
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
