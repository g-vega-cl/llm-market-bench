import { createBrowserClient } from '@supabase/ssr';

export interface PublicAuthConfig {
    url: string;
    anonKey: string;
}

const runtimeAuthConfig: { url?: string; anonKey?: string } = {};

/**
 * Hydrates public Supabase Auth credentials delivered by SSR root context so
 * browser Google OAuth still works when VITE_SUPABASE_AUTH_* was not baked at build time.
 */
export function setRuntimeAuthConfig(config: { url?: string; anonKey?: string } | null) {
    if (typeof window === 'undefined') return;
    runtimeAuthConfig.url = config?.url || undefined;
    runtimeAuthConfig.anonKey = config?.anonKey || undefined;
}

export function assertValidAuthUrl(
    url: string | undefined,
    envVarName: string,
): asserts url is string {
    if (!url) {
        throw new Error(`Missing Supabase Auth URL (${envVarName})`);
    }
    if (url.includes('benchify-archive-db')) {
        throw new Error(
            `Invalid Auth URL (${url}): points to the local PostgREST archive database, which does not run an Auth service. Set ${envVarName} to your Supabase Cloud project URL (e.g. https://<project-ref>.supabase.co).`,
        );
    }
}

export function getAuthBrowserClient() {
    const authUrl =
        import.meta.env.VITE_SUPABASE_AUTH_URL ||
        import.meta.env.VITE_SUPABASE_URL ||
        runtimeAuthConfig.url;
    const authAnonKey =
        import.meta.env.VITE_SUPABASE_AUTH_ANON_KEY ||
        import.meta.env.VITE_SUPABASE_ANON_KEY ||
        runtimeAuthConfig.anonKey;

    assertValidAuthUrl(authUrl, 'VITE_SUPABASE_AUTH_URL');
    if (!authAnonKey) {
        throw new Error('Missing Supabase Auth anon key (VITE_SUPABASE_AUTH_ANON_KEY)');
    }

    return createBrowserClient(authUrl, authAnonKey);
}
