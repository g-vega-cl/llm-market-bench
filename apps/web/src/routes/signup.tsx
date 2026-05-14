import { usePostHog } from '@posthog/react';
import { useMutation } from '@tanstack/react-query';
import { createFileRoute, redirect } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { getSupabaseServerClient } from '~/lib/supabase';
import { Auth } from '~/shared/auth';

export const signupFn = createServerFn({ method: 'POST' })
    .inputValidator((d: { email: string; password: string; redirectUrl?: string }) => d)
    .handler(async ({ data }) => {
        const supabase = getSupabaseServerClient();
        const { error } = await supabase.auth.signUp({
            email: data.email,
            password: data.password,
        });
        if (error) {
            return {
                error: true,
                message: error.message,
            };
        }

        // Redirect to the prev page stored in the "redirect" search param
        throw redirect({
            href: data.redirectUrl || '/',
        });
    });

export const Route = createFileRoute('/signup')({
    component: SignupComp,
});

function SignupComp() {
    const posthog = usePostHog();
    const signupMutation = useMutation({
        mutationFn: useServerFn(signupFn) as any,
        onSuccess: (data, variables) => {
            if (!(data as any)?.error) {
                posthog.identify((variables as any).email);
                posthog.capture('user_signed_up', { email: (variables as any).email });
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
                } as any);
            }}
            afterSubmit={
                signupMutation.data ? (
                    <div className="text-red-400">{(signupMutation.data as any).message}</div>
                ) : null
            }
        />
    );
}
