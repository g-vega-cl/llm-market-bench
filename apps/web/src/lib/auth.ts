import { createServerClient } from '@supabase/ssr';
import { getCookies, setCookie } from '@tanstack/react-start/server';
import { assertValidAuthUrl, getAuthBrowserClient } from './auth-client';

export { assertValidAuthUrl, getAuthBrowserClient };

export function getAuthServerClient() {
    const authUrl = process.env.SUPABASE_AUTH_URL || process.env.SUPABASE_URL;
    const authAnonKey = process.env.SUPABASE_AUTH_ANON_KEY || process.env.SUPABASE_ANON_KEY;

    assertValidAuthUrl(authUrl, 'SUPABASE_AUTH_URL');
    if (!authAnonKey) {
        throw new Error('Missing Supabase Auth anon key (SUPABASE_AUTH_ANON_KEY)');
    }

    return createServerClient(authUrl, authAnonKey, {
        cookies: {
            getAll() {
                try {
                    return Object.entries(getCookies()).map(([name, value]) => ({
                        name,
                        value,
                    }));
                } catch {
                    return [];
                }
            },
            setAll(cookies: { name: string; value: string; options?: Record<string, unknown> }[]) {
                try {
                    for (const cookie of cookies) {
                        setCookie(cookie.name, cookie.value, cookie.options);
                    }
                } catch {
                    // Outside active HTTP request context
                }
            },
        },
    });
}
