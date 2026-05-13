import { createServerClient } from '@supabase/ssr';
import { getCookies, setCookie } from '@tanstack/react-start/server';

export function getSupabaseServerClient() {
    return createServerClient(process.env.SUPABASE_URL!, process.env.SUPABASE_ANON_KEY!, {
        cookies: {
            getAll() {
                return Object.entries(getCookies()).map(([name, value]) => ({
                    name,
                    value,
                }));
            },
            setAll(cookies: { name: string; value: string }[]) {
                cookies.forEach((cookie: { name: string; value: string }) => {
                    setCookie(cookie.name, cookie.value);
                });
            },
        },
    });
}
