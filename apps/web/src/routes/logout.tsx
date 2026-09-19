import { usePostHog } from '@posthog/react';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { useEffect } from 'react';
import { getSupabaseServerClient } from '~/lib/supabase';

export const logoutFn = createServerFn({ method: 'POST' }).handler(async () => {
    const supabase = getSupabaseServerClient();
    const { error } = await supabase.auth.signOut();

    if (error) {
        return {
            error: true,
            message: error.message,
        };
    }

    return { success: true };
});

export function LogoutComponent({
    logoutAction = () => logoutFn(),
}: {
    logoutAction?: () => Promise<unknown>;
} = {}) {
    const posthog = usePostHog();
    const router = useRouter();

    useEffect(() => {
        posthog?.reset();
        logoutAction().finally(async () => {
            await router.invalidate();
            router.navigate({ to: '/' });
        });
    }, [posthog, router, logoutAction]);

    return (
        <div className="flex items-center justify-center min-h-[50vh] text-zinc-400 text-sm font-mono">
            Logging out...
        </div>
    );
}

export const Route = createFileRoute('/logout')({
    preload: false,
    component: LogoutComponent,
});
