import { createServerClient } from '@supabase/ssr';
import { getCookies, setCookie } from '@tanstack/react-start/server';

export function getSupabaseServerClient() {
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;
    if (!supabaseUrl || !supabaseAnonKey) {
        throw new Error('Missing Supabase environment variables');
    }

    return createServerClient(supabaseUrl, supabaseAnonKey, {
        cookies: {
            getAll() {
                return Object.entries(getCookies()).map(([name, value]) => ({
                    name,
                    value,
                }));
            },
            setAll(cookies: { name: string; value: string; options?: Record<string, unknown> }[]) {
                cookies.forEach((cookie) => {
                    setCookie(cookie.name, cookie.value, cookie.options);
                });
            },
        },
    });
}
